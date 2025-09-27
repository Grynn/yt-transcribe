#!/bin/sh

set -e -u -o pipefail

## Configuration
upgrade=""
working_dir="/tmp"
whisper_model="mlx-community/whisper-large-v3-turbo"
yt_dlp="yt-dlp"
mlx_whisper="mlx_whisper"
resume_mode=false

## State directory structure

# /tmp/{url_hash}/
# ├── info.json           # Video metadata
# ├── audio_filename.txt  # Path to audio file
# ├── {video_id}.opus     # Downloaded audio
# ├── {video_id}.txt      # Transcription
# ├── {video_id}.md       # Final summary
# ├── *.done              # Completion markers
# └── info.done, download.done, transcribe.done, summarize.done, notify.done

# Show usage
show_usage() {
    echo "Usage: $0 [-U] [-r] <URL>"
    echo "  -U: Upgrade tools to latest versions"
    echo "  -r: Resume from previous failed run"
    echo "  URL: YouTube or other supported URL"
    exit 1
}

while getopts "Ur" opt; do
    case $opt in
        U)
            upgrade="-U"
            yt_dlp="yt-dlp@latest"
            mlx_whisper="mlx_whisper@latest"
            ;;
        r)
            resume_mode=true
            ;;
        *)
            show_usage
            ;;
    esac
done
shift $((OPTIND -1))

if [ $# -eq 0 ]; then
    show_usage
fi

url="${1}"

# Create unique key for this URL
url_key=$(echo "${url}" | md5)
state_dir="/tmp/${url_key}"
mkdir -p "${state_dir}"

echo "Processing URL: ${url}"
echo "State directory: ${state_dir}"

# State management functions
mark_step_complete() {
    step_name="$1"
    touch "${state_dir}/${step_name}.done"
    echo "✓ Step completed: ${step_name}"
}

is_step_complete() {
    step_name="$1"
    [ -f "${state_dir}/${step_name}.done" ]
}

get_step_status() {
    if is_step_complete "$1"; then
        echo "✓ $1 (completed)"
    else
        echo "○ $1 (pending)"
    fi
}

# Show current status if resuming
if [ "$resume_mode" = true ]; then
    echo ""
    echo "Resume mode - Current status:"
    get_step_status "info"
    get_step_status "download"
    get_step_status "transcribe"
    get_step_status "summarize"
    get_step_status "notify"
    echo ""
fi

# Step 1: Get video info
if ! is_step_complete "info"; then
    echo "Getting video info..."
    if ! info_json=$(uvx ${yt_dlp} -j --no-warnings "${url}"); then
        echo "Error: Failed to get video info from ${url}"
        exit 1
    fi

    # Sanitize JSON by removing/escaping control characters
    sanitized_json=$(echo "${info_json}" | tr -d '\000-\037\177')

    # Validate JSON using sanitized version
    if ! echo "${sanitized_json}" | jq . >/dev/null 2>&1; then
        echo "Error: Invalid JSON received from yt-dlp"
        echo "Raw output:"
        echo "${info_json}" > "${state_dir}/yt-dlp-error.json"
        echo "Sanitized output:"
        echo "${sanitized_json}" > "${state_dir}/yt-dlp-sanitized.json"
        echo "See ${state_dir}/yt-dlp-error.json and ${state_dir}/yt-dlp-sanitized.json for details"
        exit 1
    fi

    # Use sanitized JSON for processing
    info_json="${sanitized_json}"

    echo "${info_json}" > "${state_dir}/info.json"
    echo "Video info saved to ${state_dir}/info.json"
    
    mark_step_complete "info"
else
    echo "Loading existing video info..."
    info_json=$(cat "${state_dir}/info.json")
fi

title=$(echo "${info_json}" | jq -r '.title')
webpage_url=$(echo "${info_json}" | jq -r '.webpage_url')
video_id=$(echo "${info_json}" | jq -r '.id')

if [ "${title}" = "null" ] || [ -z "${title}" ]; then
    echo "Error: Could not extract title from video info"
    exit 1
fi

echo "Title: ${title}"
echo "URL: ${webpage_url}"
echo "Video ID: ${video_id}"

# Step 2: Download audio
if ! is_step_complete "download"; then
    echo "Downloading audio..."
    audio_filename=$(uvx ${yt_dlp} -x "${url}" --output "${state_dir}/%(id)s.%(ext)s" --print 'after_move:filepath' --restrict-filenames)
    echo "Audio extracted to filename: ${audio_filename}"
    
    # Save audio filename for resume
    echo "${audio_filename}" > "${state_dir}/audio_filename.txt"
    mark_step_complete "download"
else
    echo "Using existing audio file..."
    audio_filename=$(cat "${state_dir}/audio_filename.txt")
    
    if [ ! -f "${audio_filename}" ]; then
        echo "Error: Audio file ${audio_filename} not found, removing download marker"
        rm -f "${state_dir}/download.done"
        echo "Re-run to download audio again"
        exit 1
    fi
    
    echo "Audio file: ${audio_filename}"
fi

# Step 3: Transcribe the audio
txt_filename="${state_dir}/${video_id}.txt"
if ! is_step_complete "transcribe"; then
    echo "Transcribing..."
    uvx ${mlx_whisper} --verbose False --model "${whisper_model}" "${audio_filename}" -o "${state_dir}"
    
    if [ ! -f "${txt_filename}" ]; then
        echo "Error: Transcription failed, ${txt_filename} not found"
        exit 1
    fi
    
    mark_step_complete "transcribe"
else
    echo "Using existing transcription..."
    
    if [ ! -f "${txt_filename}" ]; then
        echo "Error: Transcription file ${txt_filename} not found, removing transcribe marker"
        rm -f "${state_dir}/transcribe.done"
        echo "Re-run to transcribe again"
        exit 1
    fi
    
    echo "Transcription file: ${txt_filename}"
fi

# Step 4: Summarize the transcription
md_filename="${state_dir}/${video_id}.md"
if ! is_step_complete "summarize"; then
    echo "Summarizing with $(llm models default)...(change llm default model with 'llm models set default <model>')"
    summary_header="URL: ${webpage_url}\nTitle: ${title}\n\n"
    # PROMPT_PLACEHOLDER - This will be replaced during installation
    prompt="Give me the headlines and key takeaways as bullet points. Try to be concise, but also do not miss any key concepts that can help make investment decisions."
    
    if ! (echo -e "${summary_header}"; cat "${txt_filename}" | llm -s "${prompt}") > "${md_filename}"; then
        echo "Error: Summarization failed"
        exit 1
    fi
    
    mark_step_complete "summarize"
else
    echo "Using existing summary..."
    
    if [ ! -f "${md_filename}" ]; then
        echo "Error: Summary file ${md_filename} not found, removing summarize marker"
        rm -f "${state_dir}/summarize.done"
        echo "Re-run to summarize again"
        exit 1
    fi
    
    echo "Summary file: ${md_filename}"
fi

full_path=$(realpath "${md_filename}")
echo "Summary saved to ${full_path}"

# Step 5: Send notifications
if ! is_step_complete "notify"; then
    echo "Sending notifications..."
    
    # Terminal notification
    terminal-notifier -title "YT Transcribe" -message "Transcription complete" -sound Glass -open "file:///${full_path}"
    
    # Telegram notification
    cat "${full_path}" | telegram -M -
    
    mark_step_complete "notify"
    echo "All steps completed successfully!"
else
    echo "Notifications already sent"
    echo "All steps completed successfully!"
fi

echo ""
echo "Final output: ${full_path}"
echo "State directory: ${state_dir}"

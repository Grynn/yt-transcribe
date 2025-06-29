#!/bin/sh

set -e -u -o pipefail

## Configuration
upgrade=""
working_dir="/tmp"
whisper_model="mlx-community/whisper-large-v3-turbo"

while getopts "U" opt; do
    case $opt in
        U)
            upgrade="-U"
            ;;
        *)
            ;;
    esac
done
shift $((OPTIND -1))

url="${1}"

# Get video info
echo "Getting video info..."
info_json=$(uvx $upgrade yt-dlp -j "${url}")
title=$(echo "${info_json}" | jq -r '.title')
webpage_url=$(echo "${info_json}" | jq -r '.webpage_url')

# Download audio
# yt-dlp handles both YouTube and Twitter URLs.
echo "Downloading audio..."
audio_filename=$(uvx $upgrade yt-dlp -x "${url}" --output "/${working_dir}/%(id)s.%(ext)s" --print 'after_move:filepath' --restrict-filenames)
echo "Audio extracted to filename: ${audio_filename}"

# Transcribe the audio
txt_filename="${audio_filename%.*}.txt"
echo "Transcribing..."
uvx $upgrade mlx_whisper --verbose False --model "${whisper_model}" "${audio_filename}" -o /tmp
if [ ! -f "${txt_filename}" ]; then
    echo "Error: Transcription failed, ${txt_filename} not found"
    exit 1
fi

# Summarize the transcription
md_filename="${audio_filename%.*}.md"
echo "Summarizing with $(llm models default)...(change llm default model with 'llm models set default <model>')"
summary_header="URL: ${webpage_url}\nTitle: ${title}\n\n"
prompt="Give me the headlines and key takeaways as bullet points. Try to be concise, but also do not miss any key concepts that can help make investment decisions."
(echo -e "${summary_header}"; cat "${txt_filename}" | llm -s "${prompt}") > "${md_filename}"
full_path=$(realpath "${md_filename}")
echo "Summary saved to ${full_path}"
terminal-notifier -title "YT Transcribe" -message "Transcription complete" -sound Glass -open "file:///${full_path}"
cat "${full_path}" | telegram -M -

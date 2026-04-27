#!/usr/bin/env python3
"""Main CLI for yt-transcribe."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
import yt_dlp

from .config import (
    SUMMARIZATION_PROMPT,
    TELEGRAM_CHAR_LIMIT,
    WHISPER_MODEL,
    check_platform,
    get_codex_api_key,
    get_codex_base_url,
    get_codex_model,
    configure_provider,
    PROVIDER_CONFIGS,
)
from .email_sender import send_email
from .codex_summarizer import summarize_with_codex
from .telegram_sender import send_to_telegram
from .privatebin_uploader import upload_transcript


class StateManager:
    """Manages state and resumption for transcription workflow."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def mark_complete(self, step: str):
        """Mark a step as complete."""
        (self.state_dir / f"{step}.done").touch()
        click.echo(f"✓ Step completed: {step}")

    def is_complete(self, step: str) -> bool:
        """Check if a step is complete."""
        return (self.state_dir / f"{step}.done").exists()

    def get_status(self, step: str) -> str:
        """Get status string for a step."""
        if self.is_complete(step):
            return f"✓ {step} (completed)"
        return f"○ {step} (pending)"

    def show_status(self):
        """Display current workflow status."""
        click.echo("\nResume mode - Current status:")
        for step in ["info", "download", "transcribe", "summarize", "upload", "notify"]:
            click.echo(self.get_status(step))
        click.echo()

    def save_json(self, filename: str, data: dict):
        """Save JSON data to state directory."""
        path = self.state_dir / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_json(self, filename: str) -> dict:
        """Load JSON data from state directory."""
        path = self.state_dir / filename
        with open(path, "r") as f:
            return json.load(f)

    def save_text(self, filename: str, content: str):
        """Save text content to state directory."""
        path = self.state_dir / filename
        with open(path, "w") as f:
            f.write(content)

    def load_text(self, filename: str) -> str:
        """Load text content from state directory."""
        path = self.state_dir / filename
        with open(path, "r") as f:
            return f.read()

    def file_exists(self, filename: str) -> bool:
        """Check if file exists in state directory."""
        return (self.state_dir / filename).exists()


def get_state_dir(url: str) -> Path:
    """Get state directory for given URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return Path("/tmp") / url_hash


def _ytdlp_common_opts() -> dict:
    # Equivalent of:
    # --extractor-args "youtube:player_client=default,-android_sdkless"
    # --remote-components ejs:github
    # --cookies-from-browser chrome  (override via YTDLP_COOKIES_BROWSER env var)
    browser = os.environ.get("YTDLP_COOKIES_BROWSER", "chrome")
    opts: dict = {
        "extractor_args": {"youtube": {"player_client": ["default", "-android_sdkless"]}},
        "remote_components": ["ejs:github"],
    }
    if browser:
        opts["cookiesfrombrowser"] = (browser, None, None, None)
    return opts


_AUDIO_EXTENSIONS = {
    ".mp3",
    ".m4a",
    ".wav",
    ".flac",
    ".aac",
    ".ogg",
    ".opus",
    ".aiff",
    ".aif",
    ".wma",
    ".caf",
}


def _source_to_state_key(source: str, source_path: Optional[Path]) -> str:
    if not source_path:
        return source
    stat = source_path.stat()
    return f"file:{source_path}:{stat.st_size}:{stat.st_mtime_ns}"


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH. Install it with: brew install ffmpeg")


def _extract_audio_to_mp3(input_path: Path, output_path: Path) -> None:
    _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def get_local_file_info(source_path: Path, state: StateManager, source_key: str) -> dict:
    """Step 1 (local): Create minimal 'info' for a local file input."""
    if state.is_complete("info"):
        click.echo("Loading existing file info...")
        return state.load_json("info.json")

    title = source_path.stem
    video_id = f"local_{hashlib.md5(source_key.encode()).hexdigest()[:12]}"

    info = {
        "id": video_id,
        "title": title,
        "webpage_url": source_path.as_uri(),
        "original_url": str(source_path),
        "_type": "local_file",
        "ext": source_path.suffix.lstrip(".").lower(),
    }

    state.save_json("info.json", info)
    click.echo(f"File info saved to {state.state_dir}/info.json")
    state.mark_complete("info")
    return info


def get_video_info(url: str, state: StateManager, upgrade: bool = False) -> dict:
    """Step 1: Get video information."""
    if state.is_complete("info"):
        click.echo("Loading existing video info...")
        return state.load_json("info.json")

    click.echo("Getting video info...")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        **_ytdlp_common_opts(),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Save info
            state.save_json("info.json", info)
            click.echo(f"Video info saved to {state.state_dir}/info.json")

            state.mark_complete("info")
            return info

    except Exception as e:
        click.echo(f"Error: Failed to get video info from {url}", err=True)
        click.echo(f"Details: {e}", err=True)
        sys.exit(1)


def prepare_audio(
    source: str,
    state: StateManager,
    video_id: str,
    source_path: Optional[Path] = None,
    upgrade: bool = False,
) -> str:
    """Step 2: Prepare audio for transcription.

    - For URLs: downloads audio via yt-dlp.
    - For local files: uses the file directly if it's an audio format; otherwise extracts audio via ffmpeg.

    This step is still tracked via the existing `download.done` marker for backward compatibility.
    """
    if state.is_complete("download"):
        click.echo("Using existing audio file...")
        audio_filename = state.load_text("audio_filename.txt").strip()

        if not os.path.exists(audio_filename):
            click.echo(f"Error: Audio file {audio_filename} not found, removing download marker", err=True)
            os.remove(state.state_dir / "download.done")
            click.echo("Re-run to download audio again")
            sys.exit(1)

        click.echo(f"Audio file: {audio_filename}")
        return audio_filename

    if source_path is not None:
        click.echo(f"Using local file: {source_path}")
        ext = source_path.suffix.lower()

        if ext in _AUDIO_EXTENSIONS:
            audio_filename = str(source_path)
            click.echo("Input looks like an audio file; skipping extraction")
        else:
            click.echo("Extracting audio with ffmpeg...")
            extracted = state.state_dir / f"{video_id}.mp3"
            try:
                _extract_audio_to_mp3(source_path, extracted)
            except subprocess.CalledProcessError as e:
                click.echo("Error: ffmpeg failed to extract audio", err=True)
                click.echo(f"Details: {e}", err=True)
                sys.exit(1)
            audio_filename = str(extracted)
            click.echo(f"Audio extracted to: {audio_filename}")

        state.save_text("audio_filename.txt", audio_filename)
        state.mark_complete("download")
        return audio_filename

    click.echo("Downloading audio...")

    output_template = str(state.state_dir / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "opus",
        }],
        "outtmpl": output_template,
        "restrictfilenames": True,
        "quiet": False,
        **_ytdlp_common_opts(),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([source])

        # Find the downloaded file
        audio_files = list(state.state_dir.glob(f"{video_id}.*"))
        if not audio_files:
            click.echo("Error: Could not find downloaded audio file", err=True)
            sys.exit(1)

        audio_filename = str(audio_files[0])
        click.echo(f"Audio extracted to: {audio_filename}")

        # Save filename for resume
        state.save_text("audio_filename.txt", audio_filename)
        state.mark_complete("download")

        return audio_filename

    except Exception as e:
        click.echo(f"Error: Failed to download audio", err=True)
        click.echo(f"Details: {e}", err=True)
        sys.exit(1)


def transcribe_audio(audio_filename: str, state: StateManager, video_id: str, upgrade: bool = False) -> str:
    """Step 3: Transcribe audio using mlx-whisper."""
    txt_filename = str(state.state_dir / f"{video_id}.txt")

    if state.is_complete("transcribe"):
        click.echo("Using existing transcription...")

        if not os.path.exists(txt_filename):
            click.echo(f"Error: Transcription file {txt_filename} not found, removing transcribe marker", err=True)
            os.remove(state.state_dir / "transcribe.done")
            click.echo("Re-run to transcribe again")
            sys.exit(1)

        click.echo(f"Transcription file: {txt_filename}")
        with open(txt_filename, "r") as f:
            return f.read()

    click.echo("Transcribing...")

    # Use mlx-whisper via uvx
    package = "mlx_whisper@latest" if upgrade else "mlx_whisper"
    cmd = [
        "uvx",
        package,
        "--verbose", "False",
        "--model", WHISPER_MODEL,
        audio_filename,
        "-o", str(state.state_dir)
    ]

    try:
        subprocess.run(cmd, check=True)

        if not os.path.exists(txt_filename):
            click.echo(f"Error: Transcription failed, {txt_filename} not found", err=True)
            sys.exit(1)

        state.mark_complete("transcribe")

        with open(txt_filename, "r") as f:
            return f.read()

    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Transcription failed", err=True)
        click.echo(f"Details: {e}", err=True)
        sys.exit(1)


def summarize_transcription(
    transcription: str,
    title: str,
    webpage_url: str,
    state: StateManager,
    video_id: str
) -> tuple[Optional[str], Optional[dict]]:
    """Step 4: Summarize transcription using Codex CLI.

    Returns:
        Tuple of (summary_content, error_details).
        If successful: (summary, None)
        If failed: (None, error_details_dict)
    """
    md_filename = str(state.state_dir / f"{video_id}.md")

    if state.is_complete("summarize"):
        click.echo("Using existing summary...")

        if not os.path.exists(md_filename):
            click.echo(f"Error: Summary file {md_filename} not found, removing summarize marker", err=True)
            os.remove(state.state_dir / "summarize.done")
            click.echo("Re-run to summarize again")
            sys.exit(1)

        click.echo(f"Summary file: {md_filename}")
        with open(md_filename, "r") as f:
            return f.read(), None

    click.echo("Summarizing with Codex CLI...")

    # Create summary header
    summary_header = f"URL: {webpage_url}\nTitle: {title}\n\n"

    # Get summary from Codex with config-provided credentials
    model = get_codex_model()
    api_key = get_codex_api_key()
    base_url = get_codex_base_url()

    if base_url:
        click.echo(f"Using custom API endpoint: {base_url}")
    if model:
        click.echo(f"Using model: {model}")

    try:
        summary_content = summarize_with_codex(
            transcription,
            SUMMARIZATION_PROMPT,
            state.state_dir,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

        # Combine header and summary
        full_summary = summary_header + summary_content

        # Save to file
        with open(md_filename, "w") as f:
            f.write(full_summary)

        state.mark_complete("summarize")

        return full_summary, None

    except Exception as e:
        # Capture rich error details
        import traceback
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "model": model,
            "base_url": base_url,
            "has_api_key": bool(api_key),
        }

        click.echo(f"Warning: Summarization failed: {e}", err=True)
        click.echo("Will continue with PrivateBin upload and email with error details.", err=True)

        return None, error_details


def upload_full_transcript(
    transcription: str,
    title: str,
    webpage_url: str,
    state: StateManager
) -> str:
    """Step 5: Upload full transcript to PrivateBin."""
    if state.is_complete("upload"):
        click.echo("Using existing PrivateBin URL...")
        return state.load_text("privatebin_url.txt").strip()

    click.echo("Uploading full transcript to PrivateBin...")

    try:
        privatebin_url = upload_transcript(transcription, title, webpage_url)
        click.echo(f"Full transcript uploaded: {privatebin_url}")

        # Save URL for resume
        state.save_text("privatebin_url.txt", privatebin_url)
        state.mark_complete("upload")

        return privatebin_url
    except Exception as e:
        click.echo(f"Warning: PrivateBin upload failed: {e}", err=True)
        return None


def format_error_summary(error_details: dict, title: str, privatebin_url: Optional[str] = None, webpage_url: Optional[str] = None) -> str:
    """Format error details into a rich markdown summary for email/notifications."""
    lines = [
        f"# ⚠️ Summarization Failed\n",
        f"**Video:** {title}\n",
    ]

    if webpage_url:
        lines.append(f"**Source:** {webpage_url}\n")

    if privatebin_url:
        lines.append(f"**Full Transcript:** {privatebin_url}\n")

    lines.extend([
        "\n---\n",
        "## Error Details\n",
        f"**Error Type:** `{error_details.get('error_type', 'Unknown')}`\n",
        f"**Message:** {error_details.get('error_message', 'No message')}\n",
    ])

    # Add configuration details
    lines.append("\n### Configuration\n")
    if error_details.get('model'):
        lines.append(f"- **Model:** `{error_details['model']}`\n")
    if error_details.get('base_url'):
        lines.append(f"- **Base URL:** `{error_details['base_url']}`\n")
    lines.append(f"- **API Key Configured:** {'✓ Yes' if error_details.get('has_api_key') else '✗ No'}\n")

    # Add traceback if available
    if error_details.get('traceback'):
        lines.extend([
            "\n### Full Traceback\n",
            "```\n",
            error_details['traceback'],
            "```\n",
        ])

    # Add helpful next steps
    lines.extend([
        "\n### Next Steps\n",
        "1. Check that your API key is valid and has sufficient credits\n",
        "2. Verify the API endpoint is accessible\n",
        "3. Try again with the `-r` flag to resume from this point\n",
        "4. The full transcript is available above via PrivateBin\n",
    ])

    return "".join(lines)


def send_notifications(
    summary: Optional[str],
    md_filename: str,
    state: StateManager,
    title: str,
    privatebin_url: Optional[str] = None,
    webpage_url: Optional[str] = None,
    error_details: Optional[dict] = None
):
    """Step 6: Send notifications via email and Telegram.

    Args:
        summary: The summary content (None if summarization failed).
        error_details: Error details dict if summarization failed.
    """
    if state.is_complete("notify"):
        click.echo("Notifications already sent")
        return

    click.echo("Sending notifications...")

    # Determine notification content
    if error_details:
        # Summarization failed - use error summary
        notification_summary = format_error_summary(error_details, title, privatebin_url, webpage_url)
        # Save error summary to file as well
        error_md_filename = md_filename.replace('.md', '_error.md')
        with open(error_md_filename, "w") as f:
            f.write(notification_summary)
        click.echo(f"Error summary saved to {error_md_filename}")
        md_filename = error_md_filename  # Update for Telegram
    else:
        # Normal summary
        notification_summary = summary
        if privatebin_url:
            notification_summary += f"\n\n---\n\n**Full Transcript:** {privatebin_url}"
        if webpage_url:
            notification_summary += f"\n**Source:** {webpage_url}"

    # Send email
    try:
        send_email(notification_summary, title)
        click.echo("✓ Email sent")
    except Exception as e:
        click.echo(f"Warning: Email failed: {e}", err=True)

    # Send to Telegram (text or PDF based on length)
    try:
        send_to_telegram(notification_summary, md_filename, title)
        click.echo("✓ Telegram sent")
    except Exception as e:
        click.echo(f"Warning: Telegram failed: {e}", err=True)

    # macOS terminal notification
    try:
        subprocess.run([
            "terminal-notifier",
            "-title", "YT Transcribe",
            "-message", "Transcription complete" if not error_details else "Summarization failed",
            "-sound", "Glass",
            "-open", f"file:///{md_filename}"
        ], check=False)
    except FileNotFoundError:
        pass  # terminal-notifier not installed

    state.mark_complete("notify")


@click.command()
@click.argument("source")
@click.option("-U", "--upgrade", is_flag=True, help="Upgrade tools to latest versions")
@click.option("-r", "--resume", is_flag=True, help="Resume from previous failed run")
@click.option(
    "-t",
    "--transcribe",
    "transcribe_only",
    is_flag=True,
    help="Transcript-only mode: skip LLM summarization, still upload and email transcript",
)
@click.option(
    "--model",
    type=click.Choice(sorted(PROVIDER_CONFIGS.keys()), case_sensitive=False),
    help="AI model provider to use for summarization (glm, deepseek, grok, openai, etc.)",
)
def cli(source: str, upgrade: bool, resume: bool, transcribe_only: bool, model: Optional[str]):
    """Transcribe and summarize video/audio content from URLs or local files.

    Optimized for Apple Silicon Macs using MLX-accelerated Whisper.
    """
    # Check platform requirements
    try:
        check_platform()
    except RuntimeError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    # Configure provider if specified
    if model:
        try:
            provider_config = configure_provider(model)
            click.echo(f"Using provider: {model}")
            click.echo(f"  Model: {provider_config['model']}")
            if provider_config['base_url']:
                click.echo(f"  Base URL: {provider_config['base_url']}")
        except ValueError as e:
            click.echo(str(e), err=True)
            sys.exit(1)

    source_path: Optional[Path] = None
    expanded = Path(source).expanduser()
    if expanded.exists() and expanded.is_file():
        source_path = expanded.resolve()

    # Setup state management
    source_key = _source_to_state_key(source, source_path)
    state_dir = get_state_dir(source_key)
    state = StateManager(state_dir)

    if source_path:
        click.echo(f"Processing file: {source_path}")
    else:
        click.echo(f"Processing URL: {source}")
    click.echo(f"State directory: {state_dir}")

    # Show status if resuming
    if resume:
        state.show_status()

    # Step 1: Get video info
    if source_path:
        info = get_local_file_info(source_path, state, source_key)
    else:
        info = get_video_info(source, state, upgrade)

    title = info.get("title")
    webpage_url = info.get("webpage_url", source)
    video_id = info.get("id")

    if not title:
        click.echo("Error: Could not extract title from video info", err=True)
        sys.exit(1)
    if not video_id:
        click.echo("Error: Could not extract ID from video info", err=True)
        sys.exit(1)

    click.echo(f"Title: {title}")
    click.echo(f"URL: {webpage_url}")
    click.echo(f"Video ID: {video_id}")

    # Step 2: Prepare audio (download for URL, extract for local file if needed)
    audio_filename = prepare_audio(source, state, video_id, source_path=source_path, upgrade=upgrade)

    # Step 3: Transcribe
    transcription = transcribe_audio(audio_filename, state, video_id, upgrade)

    md_filename = str(state.state_dir / f"{video_id}.md")
    full_path = os.path.realpath(md_filename)

    if transcribe_only:
        # Step 4 (skipped): Use transcript itself as the notification body.
        click.echo("Transcript-only mode: skipping summarization")
        summary = f"# Transcript: {title}\n\nURL: {webpage_url}\n\n---\n\n{transcription}"
        with open(md_filename, "w") as f:
            f.write(summary)
        error_details = None
        click.echo(f"Transcript saved to {full_path}")
    else:
        # Step 4: Summarize (may fail gracefully)
        summary, error_details = summarize_transcription(transcription, title, webpage_url, state, video_id)

        if summary:
            click.echo(f"Summary saved to {full_path}")
        else:
            click.echo(f"⚠️ Summary generation failed (details will be in email)")

    # Step 5: Upload full transcript to PrivateBin (always runs, even if summary failed)
    privatebin_url = upload_full_transcript(transcription, title, webpage_url, state)

    # Step 6: Send notifications (always runs, includes error details if summary failed)
    send_notifications(summary, full_path, state, title, privatebin_url, webpage_url, error_details)

    click.echo("\nAll steps completed successfully!")
    click.echo(f"\nFinal output: {full_path}")
    if privatebin_url:
        click.echo(f"Full transcript: {privatebin_url}")
    click.echo(f"State directory: {state_dir}")


if __name__ == "__main__":
    cli()

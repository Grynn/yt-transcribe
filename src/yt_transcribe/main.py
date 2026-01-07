#!/usr/bin/env python3
"""Main CLI for yt-transcribe."""

import hashlib
import json
import os
import re
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


def download_audio(url: str, state: StateManager, video_id: str, upgrade: bool = False) -> str:
    """Step 2: Download audio from video."""
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
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

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
) -> str:
    """Step 4: Summarize transcription using Codex CLI."""
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
            return f.read()

    click.echo("Summarizing with Codex CLI...")

    # Create summary header
    summary_header = f"URL: {webpage_url}\nTitle: {title}\n\n"

    # Get summary from Codex
    summary_content = summarize_with_codex(transcription, SUMMARIZATION_PROMPT, state.state_dir)

    # Combine header and summary
    full_summary = summary_header + summary_content

    # Save to file
    with open(md_filename, "w") as f:
        f.write(full_summary)

    state.mark_complete("summarize")

    return full_summary


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


def send_notifications(
    summary: str,
    md_filename: str,
    state: StateManager,
    title: str,
    privatebin_url: Optional[str] = None,
    webpage_url: Optional[str] = None
):
    """Step 6: Send notifications via email and Telegram."""
    if state.is_complete("notify"):
        click.echo("Notifications already sent")
        return

    click.echo("Sending notifications...")

    # Add PrivateBin link to summary if available
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
            "-message", "Transcription complete",
            "-sound", "Glass",
            "-open", f"file:///{md_filename}"
        ], check=False)
    except FileNotFoundError:
        pass  # terminal-notifier not installed

    state.mark_complete("notify")


@click.command()
@click.argument("url")
@click.option("-U", "--upgrade", is_flag=True, help="Upgrade tools to latest versions")
@click.option("-r", "--resume", is_flag=True, help="Resume from previous failed run")
def cli(url: str, upgrade: bool, resume: bool):
    """Transcribe and summarize video/audio content from YouTube and other sources.

    Optimized for Apple Silicon Macs using MLX-accelerated Whisper.
    """
    # Check platform requirements
    try:
        check_platform()
    except RuntimeError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    # Setup state management
    state_dir = get_state_dir(url)
    state = StateManager(state_dir)

    click.echo(f"Processing URL: {url}")
    click.echo(f"State directory: {state_dir}")

    # Show status if resuming
    if resume:
        state.show_status()

    # Step 1: Get video info
    info = get_video_info(url, state, upgrade)

    title = info.get("title")
    webpage_url = info.get("webpage_url", url)
    video_id = info.get("id")

    if not title:
        click.echo("Error: Could not extract title from video info", err=True)
        sys.exit(1)

    click.echo(f"Title: {title}")
    click.echo(f"URL: {webpage_url}")
    click.echo(f"Video ID: {video_id}")

    # Step 2: Download audio
    audio_filename = download_audio(url, state, video_id, upgrade)

    # Step 3: Transcribe
    transcription = transcribe_audio(audio_filename, state, video_id, upgrade)

    # Step 4: Summarize
    summary = summarize_transcription(transcription, title, webpage_url, state, video_id)

    md_filename = str(state.state_dir / f"{video_id}.md")
    full_path = os.path.realpath(md_filename)
    click.echo(f"Summary saved to {full_path}")

    # Step 5: Upload full transcript to PrivateBin
    privatebin_url = upload_full_transcript(transcription, title, webpage_url, state)

    # Step 6: Send notifications
    send_notifications(summary, full_path, state, title, privatebin_url, webpage_url)

    click.echo("\nAll steps completed successfully!")
    click.echo(f"\nFinal output: {full_path}")
    if privatebin_url:
        click.echo(f"Full transcript: {privatebin_url}")
    click.echo(f"State directory: {state_dir}")


if __name__ == "__main__":
    cli()

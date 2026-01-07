"""Summarization using the Codex CLI."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

CODEX_CMD = ["bunx", "@openai/codex@latest"]
CODEX_AUTH_FILES = ("auth.json", "config.toml", "config.json")


def summarize_with_codex(
    transcription: str,
    prompt: str,
    state_dir: Path,
    model: Optional[str] = None,
) -> str:
    """Summarize transcription using the Codex CLI.

    Args:
        transcription: The text to summarize.
        prompt: The summarization prompt.
        state_dir: Directory for Codex output artifacts.
        model: Optional model name override (CODEX_MODEL env var if unset, defaults to gpt-5.2-codex).

    Returns:
        The summary text.
    """
    _ensure_codex_ready()

    if model is None:
        model = os.getenv("CODEX_MODEL", "gpt-5.2-codex")

    output_path = state_dir / "codex_summary.txt"
    if output_path.exists():
        output_path.unlink()
    full_prompt = _build_prompt(transcription, prompt)

    cmd = CODEX_CMD + [
        "exec",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--output-last-message",
        str(output_path),
    ]

    if model:
        cmd.extend(["-m", model])

    cmd.append("-")

    result = subprocess.run(
        cmd,
        input=full_prompt,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or "No error output captured."
        raise RuntimeError(f"Codex CLI summarization failed: {details}")

    if not output_path.exists():
        raise RuntimeError("Codex CLI did not write a summary output file.")

    summary = output_path.read_text().strip()
    if not summary:
        raise RuntimeError("Codex CLI returned an empty summary.")

    return summary


def _build_prompt(transcription: str, prompt: str) -> str:
    """Build the Codex prompt for summarization."""
    return (
        "You are a financial analyst helping investors extract actionable insights from content.\n"
        "Follow the format exactly and keep the response concise.\n"
        f"{prompt}\n\n"
        "Transcript:\n"
        f"{transcription}\n\n"
        "Return only the summary in markdown. Do not include the transcript, code fences, or extra commentary."
    )


def _ensure_codex_ready() -> None:
    """Fail fast if Codex CLI or credentials are missing."""
    if shutil.which("bunx") is None:
        raise RuntimeError(
            "bunx not found. Install Bun or ensure bunx is on PATH before running."
        )

    if os.getenv("OPENAI_API_KEY"):
        return

    codex_dir = Path.home() / ".codex"
    for filename in CODEX_AUTH_FILES:
        if (codex_dir / filename).exists():
            return

    raise RuntimeError(
        "Codex CLI credentials not found. Run `bunx @openai/codex@latest login` "
        "or set OPENAI_API_KEY."
    )

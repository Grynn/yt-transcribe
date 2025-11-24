"""Configuration and constants for yt-transcribe."""

import os
import platform

# Summarization prompt for investment insights
SUMMARIZATION_PROMPT = """* **Core insights:** Bullet point the key ideas, focusing on what's actionable for investment decisions (market signals, timing, risks, opportunities)
* **Non-consensus views:** What contrarian, surprising, or non-obvious points were made? Include specific quotes if striking
* **Alpha signals:** Any mentions of emerging trends, inefficiencies, or insights that aren't yet priced in by markets?
"""

# Whisper model for transcription
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"

# Telegram character limit
TELEGRAM_CHAR_LIMIT = 4096

# Check if running on Apple Silicon
def is_apple_silicon() -> bool:
    """Check if running on Apple Silicon Mac."""
    return platform.system() == "Darwin" and platform.machine() == "arm64"

def check_platform():
    """Verify platform requirements."""
    if not is_apple_silicon():
        raise RuntimeError(
            "yt-transcribe requires Apple Silicon (M-series) Mac.\n"
            f"Detected: {platform.system()} {platform.machine()}"
        )

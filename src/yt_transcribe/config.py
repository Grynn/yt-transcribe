"""Configuration and constants for yt-transcribe."""

import os
import platform
import sys
from pathlib import Path
from typing import Optional

# Use tomllib (Python 3.11+) or tomli (Python 3.10)
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def get_config_path() -> Path:
    """Get config file path using XDG_CONFIG_HOME or default."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        config_dir = Path(xdg_config) / "yt-transcribe"
    else:
        config_dir = Path.home() / ".config" / "yt-transcribe"
    return config_dir / "config.toml"


def load_config() -> dict:
    """Load configuration from config file."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    return {}


# Load config at module import
_config = load_config()


def get_telegram_token() -> Optional[str]:
    """Get Telegram bot token from config or environment."""
    # Environment variable takes precedence
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env_token:
        return env_token
    return _config.get("telegram", {}).get("token")


def get_telegram_chat_id() -> Optional[str]:
    """Get Telegram chat ID from config or environment."""
    env_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if env_chat_id:
        return env_chat_id
    return _config.get("telegram", {}).get("chat_id")


def get_email_recipient() -> Optional[str]:
    """Get email recipient from config or environment."""
    env_recipient = os.environ.get("EMAIL_RECIPIENT")
    if env_recipient:
        return env_recipient
    return _config.get("email", {}).get("recipient")


def get_email_sender() -> Optional[str]:
    """Get email sender from config or environment."""
    env_sender = os.environ.get("EMAIL_SENDER")
    if env_sender:
        return env_sender
    return _config.get("email", {}).get("sender")

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

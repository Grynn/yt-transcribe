"""Configuration and constants for yt-transcribe."""

import os
import platform
import sys
from pathlib import Path
from typing import Optional, Dict

# Use tomllib (Python 3.11+) or tomli (Python 3.10)
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# Provider configurations for different AI models
PROVIDER_CONFIGS: Dict[str, Dict[str, str]] = {
    "glm": {
        "base_url": "https://api.z.ai/api/coding/paas/v4",
        "model": "glm-4.7",
        "api_key_env": "GLM_API_KEY",
    },
    "glm-flash": {
        "base_url": "https://api.z.ai/api/coding/paas/v4",
        "model": "glm-4.7-flash",
        "api_key_env": "GLM_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "deepseek-r1": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-r1",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "grok": {
        "base_url": "https://api.x.ai/v1",
        "model": "grok-2-1212",
        "api_key_env": "XAI_API_KEY",
    },
    "openai": {
        "base_url": "",  # Use default OpenAI endpoint
        "model": "gpt-5.2-codex",
        "api_key_env": "OPENAI_API_KEY",
    },
}


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


def get_codex_api_key() -> Optional[str]:
    """Get Codex API key from config or environment."""
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        return env_key
    return _config.get("codex", {}).get("api_key")


def get_codex_base_url() -> Optional[str]:
    """Get Codex base URL from config or environment for custom providers (e.g., z.ai GLM-4.7)."""
    env_url = os.environ.get("OPENAI_BASE_URL")
    if env_url:
        return env_url
    return _config.get("codex", {}).get("base_url")


def get_codex_model() -> str:
    """Get Codex model from config or environment."""
    env_model = os.environ.get("CODEX_MODEL")
    if env_model:
        return env_model
    return _config.get("codex", {}).get("model", "gpt-5.2-codex")


def configure_provider(provider: str) -> Dict[str, str]:
    """Configure environment variables for a specific provider.

    Args:
        provider: Provider name (glm, deepseek, grok, openai, etc.)

    Returns:
        Dictionary with the configured base_url, model, and api_key_env.

    Raises:
        ValueError: If provider is not supported.
    """
    provider = provider.lower()

    if provider not in PROVIDER_CONFIGS:
        available = ", ".join(sorted(PROVIDER_CONFIGS.keys()))
        raise ValueError(
            f"Unsupported provider '{provider}'. Available providers: {available}"
        )

    config = PROVIDER_CONFIGS[provider]

    # Get API key from provider-specific env var or fallback to OPENAI_API_KEY
    api_key = os.environ.get(config["api_key_env"]) or os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            f"API key not found for provider '{provider}'. "
            f"Set {config['api_key_env']} or OPENAI_API_KEY environment variable."
        )

    # Set environment variables for this process and subprocesses
    os.environ["OPENAI_API_KEY"] = api_key

    if config["base_url"]:
        os.environ["OPENAI_BASE_URL"] = config["base_url"]
        # Also remove any existing base URL to avoid conflicts
        if "OPENAI_BASE_URL" in os.environ and not config["base_url"]:
            del os.environ["OPENAI_BASE_URL"]

    os.environ["CODEX_MODEL"] = config["model"]

    return {
        "base_url": config["base_url"],
        "model": config["model"],
        "api_key_env": config["api_key_env"],
    }


def get_prompt_path() -> Path:
    """Get prompt file path in config directory."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        config_dir = Path(xdg_config) / "yt-transcribe"
    else:
        config_dir = Path.home() / ".config" / "yt-transcribe"
    return config_dir / "prompt.md"


def get_default_prompt() -> str:
    """Return the default summarization prompt."""
    return """* **Core insights:** Bullet point the key ideas, focusing on what's actionable for investment decisions (market signals, timing, risks, opportunities)
* **Non-consensus views:** What contrarian, surprising, or non-obvious points were made? Include specific quotes if striking
* **Alpha signals:** Any mentions of emerging trends, inefficiencies, or insights that aren't yet priced in by markets?
* If source is not in English, translate to English.
"""


def deploy_default_prompt() -> Path:
    """Deploy default prompt.md to config directory if not present."""
    prompt_path = get_prompt_path()
    if not prompt_path.exists():
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(get_default_prompt())
    return prompt_path


def get_summarization_prompt() -> str:
    """Get summarization prompt from config directory, deploying default if needed."""
    prompt_path = deploy_default_prompt()
    return prompt_path.read_text()


# Summarization prompt - loaded from config directory
SUMMARIZATION_PROMPT = get_summarization_prompt()

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

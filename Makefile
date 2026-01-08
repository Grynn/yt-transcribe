.PHONY: help install clean dev test

INSTALL_DIR = $(shell brew --prefix)/bin
SCRIPT_NAME = yt-transcribe

help:
	@echo "yt-transcribe - YouTube video transcription and summarization"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  help     Show this help message"
	@echo "  install  Install yt-transcribe via uv tool"
	@echo "  dev      Install in development mode"
	@echo "  test     Run tests"
	@echo "  clean    Uninstall and remove build artifacts"
	@echo ""
	@echo "Configuration: ~/.config/yt-transcribe/"
	@echo "  config.toml  - Telegram/email settings"
	@echo "  prompt.md    - Summarization prompt"

install:
	@echo "Building and installing $(SCRIPT_NAME)..."
	@uv tool install --force .
	@echo "Installation complete. $(SCRIPT_NAME) is now available in your PATH."
	@echo ""
	@echo "Configure via ~/.config/yt-transcribe/config.toml:"
	@echo "  [telegram]"
	@echo "  token = \"your-bot-token\""
	@echo "  chat_id = \"your-chat-id\""
	@echo ""
	@echo "  [email]"
	@echo "  recipient = \"you@example.com\""
	@echo ""
	@echo "Customize the summarization prompt:"
	@echo "  ~/.config/yt-transcribe/prompt.md"

dev:
	@echo "Installing in development mode..."
	@uv pip install -e .

clean:
	@uv tool uninstall $(SCRIPT_NAME) 2>/dev/null || true
	@rm -rf dist/ build/ *.egg-info
	@echo "Cleaned up build artifacts and uninstalled $(SCRIPT_NAME)"

test:
	@echo "Running tests..."
	@uv run pytest tests/ -v

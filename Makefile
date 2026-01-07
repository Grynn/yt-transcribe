.PHONY: install clean dev test

INSTALL_DIR = $(shell brew --prefix)/bin
SCRIPT_NAME = yt-transcribe

install:
	@echo "Building and installing $(SCRIPT_NAME)..."
	@uv build
	@uv tool install --force .
	@echo "Installation complete. $(SCRIPT_NAME) is now available in your PATH."
	@echo ""
	@echo "Configure with environment variables:"
	@echo "  OPENAI_API_KEY - For Codex CLI authentication"
	@echo "  CODEX_MODEL - Optional Codex model override (default: gpt-5.2-codex)"
	@echo "  EMAIL_RECIPIENT - Email address for notifications"
	@echo "  EMAIL_SENDER - Sender email address"
	@echo "  TELEGRAM_BOT_TOKEN - Telegram bot token"
	@echo "  TELEGRAM_CHAT_ID - Telegram chat ID"

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

.PHONY: help install clean dev test version

INSTALL_DIR = $(shell brew --prefix)/bin
SCRIPT_NAME = yt-transcribe

help:
	@echo "yt-transcribe - YouTube video transcription and summarization"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  help     Show this help message"
	@echo "  version  Bump patch version (default) + commit + tag"
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
	@uv tool install --force -U .
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

# Usage:
#   make version           # bumps patch
#   make version BUMP=minor
#   make version BUMP=major
BUMP ?= patch
version:
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: git worktree is dirty; commit/stash changes first." >&2; \
		git --no-pager status --porcelain >&2; \
		exit 1; \
	fi
	@echo "Bumping version ($(BUMP))..."
	@uv version --bump $(BUMP)
	@VERSION=$$(uv version --short); \
	if git show-ref --tags --verify --quiet "refs/tags/v$$VERSION"; then \
		echo "Error: tag v$$VERSION already exists" >&2; \
		git checkout -- pyproject.toml uv.lock >/dev/null 2>&1 || true; \
		exit 1; \
	fi; \
	echo "New version: $$VERSION"; \
	git add pyproject.toml uv.lock; \
	git commit -m "chore: bump version to $$VERSION"; \
	git tag -a "v$$VERSION" -m "v$$VERSION"; \
	echo "Created tag v$$VERSION"; \
	echo "Push with: git push --follow-tags"

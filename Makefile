.PHONY: install clean

INSTALL_DIR = $(shell brew --prefix)/bin
SCRIPT_NAME = yt-transcribe

install: quick.sh prompt.md
	@echo "Installing $(SCRIPT_NAME) to $(INSTALL_DIR)..."
	@# Read prompt from prompt.md and escape it for sed
	@prompt=$$(cat prompt.md | sed 's/"/\\"/g' | tr '\n' ' ' | sed 's/  */ /g'); \
	sed "s|# PROMPT_PLACEHOLDER - This will be replaced during installation|# Prompt inlined from prompt.md during installation|; \
	     s|prompt=\".*\"|prompt=\"$$prompt\"|" quick.sh > /tmp/$(SCRIPT_NAME)
	@install -m 755 /tmp/$(SCRIPT_NAME) $(INSTALL_DIR)/$(SCRIPT_NAME)
	@rm /tmp/$(SCRIPT_NAME)
	@echo "Installation complete. $(SCRIPT_NAME) is now available in your PATH."

clean:
	@rm -f $(INSTALL_DIR)/$(SCRIPT_NAME)
	@echo "Removed $(SCRIPT_NAME) from $(INSTALL_DIR)"

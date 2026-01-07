# Security Policy

## Sensitive Data

This project does NOT include any credentials, API keys, or personal information in the repository.

### Configuration Files

User credentials should be stored in:
- `~/.config/yt-transcribe/config.toml` (NOT tracked by git)
- Environment variables

**Never commit:**
- `config.toml` with real credentials
- `.env` files
- API keys or tokens
- Personal email addresses or chat IDs

### Example Configuration

See `config.toml.example` for a template with placeholder values.

## Reporting a Vulnerability

If you discover a security vulnerability, please email the maintainer privately rather than opening a public issue.

## Best Practices

1. **API Keys**: Use `bunx @openai/codex@latest login` to store credentials securely
2. **Telegram**: Never share your bot token publicly
3. **Config Files**: Keep `~/.config/yt-transcribe/config.toml` readable only by your user:
   ```bash
   chmod 600 ~/.config/yt-transcribe/config.toml
   ```

## Third-Party Services

This tool may send data to:
- OpenAI (via Codex CLI) - for summarization
- PrivateBin servers - for transcript hosting
- Your configured email/Telegram endpoints

Review the privacy policies of these services before use.

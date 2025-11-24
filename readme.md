# yt-transcribe

Transcribe and summarize video/audio content from YouTube, Twitter, and other sources with AI-powered analysis. Optimized for Apple Silicon Macs using MLX-accelerated Whisper.

## Features

- 🎥 **Multi-source support**: YouTube, Twitter, and any platform supported by yt-dlp
- 🎯 **Investment-focused summaries**: Specialized prompts for actionable insights
- 🔄 **Resumable workflow**: Interrupted jobs can continue from last checkpoint
- 📧 **Email notifications**: Markdown summaries converted to beautiful HTML
- 📱 **Telegram integration**: Auto-converts long summaries to PDF
- 🚀 **MLX-accelerated**: Optimized for M-series chip performance
- 🤖 **Multi-LLM support**: Works with GPT-4, Claude, Gemini, and more via LiteLLM

## Requirements

- **macOS** with **Apple Silicon (M1/M2/M3/M4)**
- **Python 3.10+**
- **uv** (Python package installer)
- **ffmpeg** (for audio processing)
- **Homebrew** (for installation)

## Installation

### 1. Install system dependencies

```bash
brew install ffmpeg
```

### 2. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install yt-transcribe

```bash
make install
```

This will build the package and install the `yt-transcribe` command to your PATH.

## Configuration

Configure via environment variables (add to `~/.zshrc` or `~/.bashrc`):

### LLM Configuration (required)

```bash
# Choose your LLM provider:

# OpenAI (GPT-4)
export LITELLM_MODEL="gpt-4o"
export OPENAI_API_KEY="sk-..."

# Anthropic (Claude)
export LITELLM_MODEL="claude-3-5-sonnet-20241022"
export ANTHROPIC_API_KEY="sk-ant-..."

# Google (Gemini)
export LITELLM_MODEL="gemini/gemini-pro"
export GEMINI_API_KEY="..."
```

### Email Configuration (optional)

```bash
export EMAIL_RECIPIENT="your.email@example.com"
export EMAIL_SENDER="transcribe@$(hostname)"
```

If not set, emails will be sent to `$USER@localhost`.

### Telegram Configuration (optional)

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHAT_ID="123456789"
```

To get these values:
1. Create a bot via [@BotFather](https://t.me/botfather) on Telegram
2. Get your chat ID by messaging [@userinfobot](https://t.me/userinfobot)

## Usage

### Basic usage

```bash
yt-transcribe <URL>
```

### With resume support

```bash
yt-transcribe -r <URL>
```

Resume from previous failed run (uses cached results for completed steps).

### With package upgrades

```bash
yt-transcribe -U <URL>
```

Upgrades MLX Whisper and yt-dlp to latest versions before processing.

## Examples

### Transcribe a YouTube video

```bash
yt-transcribe https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Transcribe a Twitter video

```bash
yt-transcribe https://twitter.com/user/status/123456789
```

### Resume interrupted job

```bash
# First attempt (interrupted)
yt-transcribe https://www.youtube.com/watch?v=...

# Resume from last checkpoint
yt-transcribe -r https://www.youtube.com/watch?v=...
```

## Output

The tool generates several files in `/tmp/{url_hash}/`:

- `info.json` - Video metadata
- `{video_id}.opus` - Extracted audio
- `{video_id}.txt` - Raw transcription
- `{video_id}.md` - **Final summary** (this is sent via email/Telegram)

The markdown summary includes:
- Original URL and title
- Core insights for investment decisions
- Non-consensus/contrarian views
- Alpha signals (emerging trends, inefficiencies)

## Notification Behavior

### Email
- Always sent as HTML-formatted email
- Responsive design for mobile
- Plain text fallback included

### Telegram
- **Short summaries** (< 4096 chars): Sent as formatted text message
- **Long summaries** (≥ 4096 chars): Converted to PDF and sent as document

### macOS Terminal
- Desktop notification with link to summary file

## Workflow Steps

The tool follows a resumable 5-step workflow:

1. **Get Info** - Fetch video metadata
2. **Download** - Extract audio from video
3. **Transcribe** - Convert speech to text (MLX Whisper)
4. **Summarize** - Generate insights (LiteLLM)
5. **Notify** - Send via email + Telegram

Each step creates a `.done` marker file. If interrupted, use `-r` to resume.

## Development

### Install in development mode

```bash
make dev
```

### Run tests

```bash
make test
```

### Uninstall

```bash
make clean
```

## Architecture

See [agents.md](agents.md) for detailed development notes on the agentic architecture, design decisions, and implementation patterns.

## Troubleshooting

### "yt-transcribe requires Apple Silicon"

This tool is optimized for M-series Macs. MLX Whisper requires Apple Silicon to run efficiently.

### "LITELLM_MODEL environment variable not set"

Configure your LLM provider as shown in the Configuration section above.

### "TELEGRAM_BOT_TOKEN environment variable not set"

Either configure Telegram credentials or the tool will warn but continue (email still works).

### Transcription is slow

Make sure you're using an Apple Silicon Mac. MLX is significantly faster on M-series chips than Intel Macs.

## TODO

- [ ] Add support for local audio/video files
- [ ] Support for batch processing multiple URLs
- [ ] Web interface for easier configuration
- [ ] Docker support for non-macOS platforms

## License

MIT

## Credits

Built with:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video downloading
- [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) - Speech recognition
- [LiteLLM](https://github.com/BerriAI/litellm) - Unified LLM interface
- [ReportLab](https://www.reportlab.com/) - PDF generation

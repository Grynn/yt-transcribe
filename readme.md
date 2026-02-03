# yt-transcribe

Transcribe and summarize video/audio content from YouTube, Twitter, and other sources with AI-powered analysis. Optimized for Apple Silicon Macs using MLX-accelerated Whisper. When done, send summary by email/telegram.

Use case: (purely for myself): Come across an interesting but long YouTube or X video, send to this cli tool and get an email with summary and link.
YouTube transcripts are half-assed at best and X does not have any. So use whisper (local) to transcribe speech.

Does not yet do diarization.

## Features

- 🎥 **Multi-source support**: YouTube, Twitter, and any platform supported by yt-dlp
- 🎯 **Investment-focused summaries**: Specialized prompts for actionable insights
- 🔄 **Resumable workflow**: Interrupted jobs can continue from last checkpoint
- 📧 **Email notifications**: Markdown summaries converted to beautiful HTML
- 📱 **Telegram integration**: Auto-converts long summaries to PDF
- 🚀 **MLX-accelerated**: Optimized for M-series chip performance
- 🤖 **Codex CLI summaries**: Uses Codex to produce investment-focused insights
- 🔗 **Full transcript sharing**: Uploads formatted transcripts to PrivateBin with secure links

## Requirements

- **macOS** with **Apple Silicon (M1/M2/M3/M4)**
- **Python 3.10+**
- **uv** (Python package installer)
- **ffmpeg** (for audio processing)
- **Homebrew** (for installation)
- **Bun** (for Codex CLI via bunx)

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
uv tool install git+https://github.com/grynn/yt-transcribe
```

Or clone and install locally:

```bash
git clone https://github.com/grynn/yt-transcribe
cd yt-transcribe
make install
```

This will install the `yt-transcribe` command to your PATH.

## Configuration

### Option 1: Config File (Recommended)

Create a config file at `~/.config/yt-transcribe/config.toml`:

```bash
# Copy the example config
cp config.toml.example ~/.config/yt-transcribe/config.toml

# Edit with your values
nano ~/.config/yt-transcribe/config.toml
```

See `config.toml.example` for the template.

### Option 2: Environment Variables

Alternatively, configure via environment variables (add to `~/.zshrc` or `~/.bashrc`):

### Codex Configuration (required)

**Option 1: Use --model flag (Recommended for quick switching)**

```bash
# Set the appropriate API key for your provider
export GLM_API_KEY="your_glm_key"        # For glm/glm-flash
export DEEPSEEK_API_KEY="your_deepseek_key"  # For deepseek/deepseek-r1
export XAI_API_KEY="your_xai_key"         # For grok
export OPENAI_API_KEY="your_openai_key"   # For openai (default)

# Then use the --model flag
yt-transcribe --model glm <URL>
```

**Option 2: Authenticate with OpenAI Codex (for default usage)**

```bash
bunx @openai/codex@latest login
```

**Option 3: Set OPENAI_API_KEY directly**

```bash
export OPENAI_API_KEY="sk-..."
export CODEX_MODEL="gpt-5.2-codex"
```

#### Using GLM-4.7 (z.ai Coding Plan)

To use z.ai's GLM-4.7 model instead of OpenAI's Codex:

**Option 1: Via config file (Recommended)**

Add to `~/.config/yt-transcribe/config.toml`:

```toml
[codex]
model = "glm-4.7"
api_key = "your_zai_api_key"
base_url = "https://api.z.ai/api/coding/paas/v4"
```

**Option 2: Via environment variables**

```bash
export OPENAI_API_KEY="your_zai_api_key"
export OPENAI_BASE_URL="https://api.z.ai/api/coding/paas/v4"
export CODEX_MODEL="glm-4.7"
```

**Available GLM models:**
- `glm-4.7` - Full GLM-4.7 model (requires coding plan subscription)
- `glm-4.7-flash` - Free tier (lower quality but no subscription needed)
- `glm-4.5-air` - Lighter/faster variant

Get your API key from [z.ai](https://docs.z.ai/guides/overview/quick-start).

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

### PrivateBin Configuration (optional)

```bash
export PRIVATEBIN_SERVER="https://privatebin.net"  # Default if not set
```

Transcripts are uploaded to PrivateBin for easy sharing. The default server is `privatebin.net`, but you can specify any PrivateBin instance.

## Usage

### Basic usage

```bash
yt-transcribe <URL-or-file>
```

If you pass a local video file (e.g., `.mp4`, `.mov`), yt-transcribe will skip yt-dlp and use `ffmpeg` to extract audio to an `.mp3` for transcription.

### With resume support

```bash
yt-transcribe -r <URL-or-file>
```

Resume from previous failed run (uses cached results for completed steps).

### With package upgrades

```bash
yt-transcribe -U <URL-or-file>
```

Upgrades MLX Whisper and yt-dlp to latest versions before processing.

### With custom AI model provider

```bash
# Use GLM-4.7 (requires GLM_API_KEY)
yt-transcribe --model glm <URL>

# Use DeepSeek (requires DEEPSEEK_API_KEY)
yt-transcribe --model deepseek <URL>

# Use Grok (requires XAI_API_KEY)
yt-transcribe --model grok <URL>

# Use GLM-4.7 Flash free tier (requires GLM_API_KEY)
yt-transcribe --model glm-flash <URL>

# Use DeepSeek R1 reasoning model (requires DEEPSEEK_API_KEY)
yt-transcribe --model deepseek-r1 <URL>
```

The `--model` option automatically configures the appropriate API endpoint and model for the selected provider. Environment variables are set only for the current process and won't affect your shell.

**Available providers:**
- `glm` - z.ai GLM-4.7 (coding plan, $3/mo)
- `glm-flash` - z.ai GLM-4.7 Flash (free tier)
- `deepseek` - DeepSeek V3.2 chat
- `deepseek-r1` - DeepSeek R1 reasoning
- `grok` - xAI Grok-2
- `openai` - OpenAI GPT-5.2 Codex (default)

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

### Transcribe a local file

```bash
yt-transcribe ~/Downloads/my-video.mp4
```

## Output

The tool generates several files in `/tmp/{source_hash}/`:

- `info.json` - Video metadata
- `{video_id}.*` - Prepared audio (downloaded or extracted)
- `{video_id}.txt` - Raw transcription
- `{video_id}.md` - **Final summary** (this is sent via email/Telegram)
- `privatebin_url.txt` - Link to full transcript on PrivateBin

The markdown summary includes:
- Original URL and title
- Core insights for investment decisions
- Non-consensus/contrarian views
- Alpha signals (emerging trends, inefficiencies)

The full transcript is uploaded to PrivateBin and the link is included in notifications.

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
4. **Summarize** - Generate insights (Codex CLI)
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

### "Codex CLI credentials not found"

Run `bunx @openai/codex@latest login` or set `OPENAI_API_KEY` as shown above.

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
- Codex CLI - Summarization
- [ReportLab](https://www.reportlab.com/) - PDF generation

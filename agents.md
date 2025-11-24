# Development Notes: Agentic Architecture

## Overview

This project evolved from a bash script to a Python application with a focus on modularity, resumability, and multi-channel notifications. The architecture follows an agentic workflow pattern where each step is independent and can be resumed on failure.

## Architecture Philosophy

### State-Based Workflow

The system implements a **state machine pattern** with persistent checkpoints:

```
[Get Info] → [Download] → [Transcribe] → [Summarize] → [Notify]
     ✓            ✓            ✓             ✓            ✓
```

Each step:
1. Checks if already completed (`.done` marker)
2. Loads existing results if resuming
3. Executes the operation
4. Saves results to state directory
5. Marks completion with a `.done` file

This approach provides:
- **Fault tolerance**: Interrupted workflows can resume
- **Idempotency**: Re-running is safe and efficient
- **Transparency**: State directory shows exactly what's been done
- **Debugging**: Each intermediate result is preserved

### State Directory Structure

```
/tmp/{url_md5_hash}/
├── info.json              # Video metadata from yt-dlp
├── audio_filename.txt     # Path to extracted audio
├── {video_id}.opus        # Downloaded audio file
├── {video_id}.txt         # Raw transcription
├── {video_id}.md          # Final markdown summary
├── info.done              # Completion markers
├── download.done
├── transcribe.done
├── summarize.done
└── notify.done
```

## Component Design

### 1. Main Orchestrator (`main.py`)

The `cli()` function acts as the **orchestration agent**:
- Validates platform requirements (Apple Silicon check)
- Manages workflow state
- Coordinates between specialized agents
- Handles error recovery

**Design decision**: Using Click for CLI to maintain UNIX philosophy (simple, composable, flags-based).

### 2. LLM Summarization (`llm_summarizer.py`)

**Choice: LiteLLM**

We chose LiteLLM over alternatives (LangChain, direct APIs) because:
- **Unified interface** across providers (OpenAI, Anthropic, Google, Azure)
- **Minimal dependencies** - lightweight, no bloat
- **Environment-based config** - matches UNIX tool philosophy
- **Model agnostic** - switch providers without code changes

**Configuration pattern**:
```bash
# OpenAI
export LITELLM_MODEL="gpt-4o"
export OPENAI_API_KEY="sk-..."

# Anthropic Claude
export LITELLM_MODEL="claude-3-5-sonnet-20241022"
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
export LITELLM_MODEL="gemini/gemini-pro"
export GEMINI_API_KEY="..."
```

**Prompt Engineering**:
The system uses a focused investment analysis prompt:
- Core insights for actionable decisions
- Non-consensus/contrarian views
- Alpha signals (emerging trends, inefficiencies)

This creates a specialized agent persona without complex role systems.

### 3. Transcription Strategy

**Hybrid approach: Python orchestration + MLX binary**

```python
subprocess.run(["uvx", "mlx_whisper", ...])
```

**Why not pure Python**:
- MLX Whisper is optimized at the binary level for Apple Silicon
- Metal Performance Shaders integration requires native code
- Python wrapper would add overhead without benefit
- Direct subprocess call maintains performance

**Model choice**: `mlx-community/whisper-large-v3-turbo`
- Best balance of speed/accuracy for M-series chips
- Optimized quantization for on-device inference

### 4. Multi-Channel Notifications

**Design: Parallel delivery to email + Telegram**

#### Email Agent (`email_sender.py`)
- Converts markdown → HTML with inline CSS
- Uses macOS sendmail (UNIX philosophy: use system tools)
- MIME multipart: plain text + HTML alternatives
- Responsive design for mobile email clients

**Why sendmail over SMTP libraries**:
- Already configured on macOS
- No external dependencies
- Respects system mail routing rules
- Works with corporate mail systems

#### Telegram Agent (`telegram_sender.py`)
- Adaptive content delivery based on length
- **Text mode** (< 4096 chars): Direct markdown message
- **PDF mode** (≥ 4096 chars): Convert to PDF, send as document

**PDF generation strategy**:
- WeasyPrint for HTML → PDF conversion
- Styled for readability (proper margins, fonts, page breaks)
- Temporary file pattern (no disk pollution)

**Why not split long messages**:
- Context continuity (don't break mid-thought)
- PDF is searchable and shareable
- Better user experience for long-form content

## Agentic Patterns Used

### 1. **Agent Specialization**
Each module has a single responsibility:
- `llm_summarizer.py` - Text understanding & synthesis
- `email_sender.py` - Email formatting & delivery
- `telegram_sender.py` - Chat messaging & file delivery

### 2. **Agent Coordination**
The main orchestrator doesn't know implementation details:
```python
send_email(summary, title)        # Handles MD→HTML internally
send_to_telegram(summary, ...)    # Handles text/PDF decision internally
```

### 3. **Agent Resilience**
Try/except blocks allow partial success:
```python
try:
    send_email(...)
    click.echo("✓ Email sent")
except Exception as e:
    click.echo(f"Warning: Email failed: {e}")  # Continue workflow
```

### 4. **Agent Configuration**
Environment variables enable runtime agent behavior changes:
- Which LLM model to use
- Email recipients
- Telegram credentials

## Development Trade-offs

### What We Kept from Bash
- State management with `.done` files
- MD5-based state directories in `/tmp`
- Step-by-step workflow model
- Resume flag behavior

### What We Improved
- **Type safety**: Python types vs bash strings
- **Error handling**: Structured exceptions vs exit codes
- **Modularity**: Importable functions vs shell functions
- **Testing**: Unit testable vs shell script testing
- **Dependencies**: Declarative (pyproject.toml) vs comments

### What We Added
- Email delivery with HTML formatting
- PDF generation for long content
- Platform validation (Apple Silicon)
- Multi-provider LLM support via LiteLLM

## Future Agentic Enhancements

### Potential Agent Additions
1. **Content routing agent**: Decide which notification channels based on content type/length
2. **Translation agent**: Detect language, translate to preferred language
3. **Fact-checking agent**: Verify claims against knowledge bases
4. **Scheduling agent**: Queue processing for rate-limited APIs

### Multi-Agent Collaboration
Could implement **agent conversation patterns**:
```
Transcription → Summary → Critic → Revision → Final
```

Where:
- Summarizer creates initial summary
- Critic agent reviews for accuracy/completeness
- Revision agent improves based on feedback

### Observability
Add agent tracing:
```python
@trace_agent
def summarize_with_litellm(...):
    # Automatic logging of inputs/outputs/timing
```

## Performance Characteristics

### Bottlenecks
1. **Download**: Network bandwidth limited
2. **Transcription**: CPU/GPU bound (MLX accelerated)
3. **Summarization**: API latency (network call to LLM)
4. **PDF generation**: CPU bound (HTML rendering)

### Optimization Opportunities
- Parallel notification sending (already async-capable)
- Streaming transcription (process chunks as they arrive)
- Cached summaries (hash content, reuse if seen before)

## Platform-Specific Decisions

### Why Apple Silicon Only?
- MLX framework requires M-series chips
- Whisper performance degrades significantly on x86 (even with AVX512)
- Metal Performance Shaders are macOS-specific
- Target audience: developers with modern Macs

### Migration Path for Other Platforms
To support Linux/Windows, would need:
- Replace MLX Whisper with OpenAI Whisper or faster-whisper
- Add CUDA support detection
- Use different audio backend (MLX uses Metal)

## Configuration Best Practices

### Environment Setup Example
```bash
# ~/.zshrc or ~/.bashrc

# LLM Configuration
export LITELLM_MODEL="claude-3-5-sonnet-20241022"
export ANTHROPIC_API_KEY="sk-ant-..."

# Email Configuration
export EMAIL_RECIPIENT="me@example.com"
export EMAIL_SENDER="transcribe@$(hostname)"

# Telegram Configuration
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHAT_ID="123456789"
```

### Security Notes
- Never commit API keys to git
- Use environment variables or secret management
- sendmail respects system security policies
- Telegram bot tokens should be treated as passwords

## Testing Strategy

### Unit Tests
Each agent module should be independently testable:
```python
def test_markdown_to_html():
    md = "# Test\n- Item 1"
    html = markdown_to_html(md)
    assert "<h1>Test</h1>" in html
```

### Integration Tests
Test workflow steps with mocked dependencies:
```python
@patch('subprocess.run')
def test_transcribe_audio(mock_run):
    # Test transcription step
```

### End-to-End Tests
Use test fixtures:
- Sample video URL
- Pre-downloaded audio
- Known transcription output
- Expected summary format

## Lessons Learned

### From Bash to Python
1. **State management is critical** - Don't assume operations complete
2. **Resumability saves time** - Long-running processes will fail
3. **Environment variables > config files** - For deployment flexibility
4. **Single responsibility** - Each module does one thing well
5. **Graceful degradation** - Email fails? Telegram should still work

### Agentic Design Benefits
- **Composability**: Easy to add new notification channels
- **Testability**: Mock individual agents in isolation
- **Flexibility**: Swap LLM providers without refactoring
- **Maintainability**: Clear separation of concerns

## Conclusion

This architecture demonstrates that **agentic patterns** don't require complex frameworks. Key principles:

1. **State persistence** enables fault tolerance
2. **Agent specialization** improves maintainability
3. **Environment configuration** provides flexibility
4. **Graceful failure** ensures partial success
5. **Platform optimization** leverages hardware capabilities

The result is a robust, resumable pipeline for video transcription and summarization, optimized for Apple Silicon Macs and delivering results via multiple channels.

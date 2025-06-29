Quick utils to transcribe Youtube, Twitter and other audio/video sources to text and summarize the results using an AI model.
Defaults to using the `llm` cli's default model.
Need to make better prompts also.

## TODO

- [ ] Add support for other audio/video sources (if URL is a local file ./audiofile or ./videofile) then use ffmpeg to create aac/opus/mp3 (if needed) and then transcribe
  - [ ] (maybe mlx_whisper already does this?)
- [ ] Completion notification via Telegram


## Installation

```bash
brew install yt-dlp
brew install ffmpeg
brew install jq
brew install telegram-cli
brew install terminal-notifier
pip install llm
pip install llm-gpt4all
pip install llm-mistral
pip install llm-claude3
pip install llm-gemini
pip install uvx
pip install mlx-whisper
```

## Usage

```bash
./quick.sh <url>
```

Supported URLs include YouTube, Twitter, and other sources supported by `yt-dlp`.

## Example

```bash
./quick.sh https://www.youtube.com/watch?v=...
./quick.sh https://twitter.com/user/status/...
```

This will download the audio from the URL, transcribe it using whisper, and then summarize it using the default llm model.
The summary will include the original URL and title, and will be saved to a file in the `/tmp` directory.
A notification will be sent to the terminal, and the summary will be sent to Telegram.

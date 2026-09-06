---
name: openai-whisper
description: Local speech-to-text with the Whisper CLI (no API key). Triggers: "transcribe audio", "speech to text", "transcribe recording".
homepage: https://openai.com/research/whisper
metadata:
  bins: ["whisper"]
  install: [{"id": "brew", "kind": "brew", "formula": "openai-whisper", "label": "Install OpenAI Whisper (brew)"}]
---

# openai-whisper — Local Speech-to-Text

Local speech-to-text using OpenAI's Whisper model. No API key required — runs entirely locally.

## Installation

```bash
brew install openai-whisper
```

## Usage

```bash
# Basic transcription
whisper audio.mp3

# Specify language
whisper audio.mp3 --language English

# Output to specific format
whisper audio.mp3 --output-format json

# Model size (default is medium)
whisper audio.mp3 --model small  # fast, less accurate
whisper audio.mp3 --model large  # slow, most accurate
```

## Supported Formats

MP3, WAV, M4A, FLAC, OGG — any audio format FFmpeg can read.

## Error Handling

- **File not found**: Verify the file path exists
- **Unsupported format**: Convert to a supported format with FFmpeg first
- **Model download**: First run downloads the model automatically

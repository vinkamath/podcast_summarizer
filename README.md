# Podcast Summarization Tool

A powerful CLI tool that downloads podcasts from YouTube and other platforms, transcribes them using OpenAI's Whisper, and generates intelligent summaries using Google's Gemini Flash 2.5 API.

## Features

- 🎵 **Download podcasts** from YouTube and other platforms using yt-dlp
- 🎤 **Transcribe audio** with OpenAI Whisper (multiple model sizes available)
- 🤖 **Generate summaries** with Google Gemini Flash 2.5 (brief, comprehensive, or bullet points)
- ⚡ **Chunked processing** for long episodes with automatic time-based segmentation
- 📄 **Multiple output formats** (JSON, Markdown, Plain text, SRT subtitles)
- 🏷️ **Key topic extraction** from transcribed content
- 🛠️ **Flexible CLI** with individual command support for each step

## Installation

### Prerequisites

1. **Python 3.9 or higher**
2. **FFmpeg** (required for audio processing)
   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt install ffmpeg

   # Windows
   # Download from https://ffmpeg.org/
   ```

3. **Google Gemini API Key**
   - Visit [Google AI Studio](https://ai.google.dev/)
   - Create an account and generate an API key
   - Set the environment variable:
     ```bash
     export GEMINI_API_KEY='your-api-key-here'
     ```

### Install the Package

```bash
# Clone the repository
git clone https://github.com/yourusername/podcast-summarize.git
cd podcast-summarize

# Install in development mode
pip install -e .
```

## Quick Start

### Complete Workflow

Process a podcast from Spotify URL to summary in one command:

```bash
podcast-summarize process "https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk"
```

This will:
1. Download the podcast audio
2. Transcribe it using Whisper
3. Generate a comprehensive summary
4. Save results in multiple formats

### Individual Commands

#### Get Episode Information
```bash
podcast-summarize info "https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk"
```

#### Transcribe Audio File
```bash
podcast-summarize transcribe audio.mp3 --model base --format json
```

#### Summarize Text File
```bash
podcast-summarize summarize transcript.txt --type bullet_points --topics 5
```

#### Check Available Models
```bash
podcast-summarize models
```

#### Setup Help
```bash
podcast-summarize setup
```

## Command Reference

### `process` - Complete Workflow

Process a podcast from Spotify URL to summary.

```bash
podcast-summarize process [OPTIONS] SPOTIFY_URL
```

**Options:**
- `--output-dir, -o`: Output directory for files
- `--whisper-model, -m`: Whisper model (`tiny`, `base`, `small`, `medium`, `large`, `turbo`)
- `--summary-type, -s`: Summary type (`brief`, `comprehensive`, `bullet_points`)
- `--language, -l`: Language code for transcription
- `--keep-audio`: Keep downloaded audio file
- `--keep-transcript`: Keep transcription file
- `--chunk-duration`: Duration of chunks in seconds (default: 300)

**Example:**
```bash
podcast-summarize process \
  "https://open.spotify.com/episode/..." \
  --output-dir ./results \
  --whisper-model small \
  --summary-type bullet_points \
  --language en \
  --keep-audio \
  --chunk-duration 600
```

### `transcribe` - Audio Transcription

Transcribe an audio file using Whisper.

```bash
podcast-summarize transcribe [OPTIONS] AUDIO_FILE
```

**Options:**
- `--output, -o`: Output file path
- `--model, -m`: Whisper model
- `--language, -l`: Language code
- `--format, -f`: Output format (`json`, `txt`, `srt`)
- `--timestamps`: Include timestamps (default: true)

**Example:**
```bash
podcast-summarize transcribe episode.mp3 \
  --model medium \
  --language en \
  --format srt \
  --output transcript.srt
```

### `summarize` - Text Summarization

Summarize a text file using Gemini Flash 2.5.

```bash
podcast-summarize summarize [OPTIONS] TEXT_FILE
```

**Options:**
- `--output, -o`: Output file path
- `--type, -t`: Summary type (`brief`, `comprehensive`, `bullet_points`)
- `--format, -f`: Output format (`json`, `txt`, `md`)
- `--topics`: Extract N key topics

**Example:**
```bash
podcast-summarize summarize transcript.txt \
  --type comprehensive \
  --format md \
  --topics 3 \
  --output summary.md
```

### `info` - Episode Information

Get information about a Spotify podcast episode.

```bash
podcast-summarize info "https://open.spotify.com/episode/..."
```

## Whisper Models

| Model    | Size  | Speed         | Languages     | Use Case                    |
|----------|-------|---------------|---------------|-----------------------------|
| `tiny`   | ~1 GB | ~32x realtime | English-only  | Fast, basic transcription  |
| `base`   | ~1 GB | ~16x realtime | Multilingual  | Balanced speed/accuracy     |
| `small`  | ~2 GB | ~6x realtime  | Multilingual  | Good accuracy               |
| `medium` | ~5 GB | ~2x realtime  | Multilingual  | High accuracy               |
| `large`  | ~10GB | ~1x realtime  | Multilingual  | Best accuracy               |
| `turbo`  | ~6 GB | ~8x realtime  | Multilingual  | Optimized large model       |

## Summary Types

### Brief
A concise 2-3 sentence summary capturing the main topic and key message.

### Comprehensive
Detailed summary including:
- Main topic and theme
- Key points and arguments
- Important insights or takeaways
- Notable quotes or memorable moments
- Overall conclusions

### Bullet Points
Easy-to-scan bullet point format with:
- Main topic and theme
- Key discussion points
- Important insights
- Notable quotes or statistics
- Main conclusions

## Output Formats

### JSON
Complete structured data including metadata, timestamps, and processing information.

### Markdown
Formatted document with headings, easy to read and publish.

### Plain Text
Simple text format for basic use cases.

### SRT (Subtitles)
Standard subtitle format with timing information (transcription only).

## Configuration

### Environment Variables

```bash
# Required
export GEMINI_API_KEY='your-google-gemini-api-key'

# Optional
export WHISPER_CACHE_DIR='/path/to/whisper/cache'
export YT_DLP_CACHE_DIR='/path/to/yt-dlp/cache'
```

### Configuration File

Create `.env` file in your project directory:

```env
GEMINI_API_KEY=your-api-key-here
WHISPER_CACHE_DIR=/tmp/whisper_cache
YT_DLP_CACHE_DIR=/tmp/yt_dlp_cache
```

## Examples

### Basic Podcast Processing

```bash
# Simple processing with defaults
podcast-summarize process "https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk"

# Custom settings
podcast-summarize process \
  "https://open.spotify.com/episode/..." \
  --output-dir ./my_podcasts \
  --whisper-model medium \
  --summary-type bullet_points \
  --keep-audio
```

### Long Episode Processing

For episodes longer than 5 minutes, the tool automatically uses chunked processing:

```bash
podcast-summarize process \
  "https://open.spotify.com/episode/..." \
  --chunk-duration 600 \
  --whisper-model small
```

This creates:
- Individual summaries for each 10-minute chunk
- A comprehensive final summary combining all chunks

### Transcription Only

```bash
# Basic transcription
podcast-summarize transcribe episode.mp3

# High-quality transcription with specific language
podcast-summarize transcribe episode.mp3 \
  --model large \
  --language en \
  --format srt
```

### Summarization Only

```bash
# Summarize existing transcript
podcast-summarize summarize transcript.txt

# Extract key topics
podcast-summarize summarize transcript.txt \
  --topics 5 \
  --type bullet_points
```

## Troubleshooting

### Common Issues

**FFmpeg not found:**
```bash
# Install FFmpeg first
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Ubuntu
```

**Gemini API key not set:**
```bash
export GEMINI_API_KEY='your-key-here'
# Or add to ~/.bashrc or ~/.zshrc
```

**Spotify URL not working:**
- Ensure the URL is for a podcast episode, not music
- Try copying the URL directly from Spotify
- Check if the episode is publicly available

**Out of memory during transcription:**
- Use a smaller Whisper model (`tiny` or `base`)
- Process shorter chunks with `--chunk-duration`

### Performance Tips

1. **Choose the right Whisper model:**
   - Use `tiny` or `base` for speed
   - Use `medium` or `large` for accuracy
   - Use `turbo` for balanced performance

2. **Optimize for long episodes:**
   - Use chunked processing (`--chunk-duration 300`)
   - Process chunks in smaller segments
   - Keep intermediate files for debugging

3. **Manage API costs:**
   - Use brief summaries for quick overviews
   - Process shorter chunks to reduce token usage
   - Cache transcriptions for reprocessing

## Development

### Project Structure

```
podcast_summarize/
├── src/
│   └── podcast_summarize/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py           # Command-line interface
│       ├── audio_downloader.py  # YouTube/yt-dlp download logic
│       ├── metadata.py      # Spotify metadata extraction
│       ├── transcriber.py   # Whisper transcription
│       └── summarizer.py    # Gemini summarization
├── tests/                   # Test files
├── pyproject.toml          # Project configuration
└── README.md              # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT License - see LICENSE file for details.

## Credits

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [Google Gemini](https://ai.google.dev/) for text summarization
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube and multi-platform downloads
- [Click](https://click.palletsprojects.com/) for CLI framework

## Changelog

### v0.1.0
- Initial release
- Basic podcast download, transcription, and summarization
- Support for multiple Whisper models
- Google Gemini Flash 2.5 integration
- Chunked processing for long episodes
- Multiple output formats
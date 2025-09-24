"""Command line interface for the podcast summarization tool."""

import os
import tempfile
from pathlib import Path
from typing import Optional

import click

from .downloader import PodcastDownloader
from .transcriber import PodcastTranscriber
from .summarizer import PodcastSummarizer


@click.group(invoke_without_command=True)
@click.version_option()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def main(ctx, verbose):
    """Podcast Summarization Tool

    Download podcasts from Spotify URLs, transcribe them, and generate summaries
    using Google Gemini Flash 2.5 API.

    Examples:
        podcast-summarize process "https://open.spotify.com/episode/..."
        podcast-summarize transcribe audio.mp3
        podcast-summarize summarize transcript.txt
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("spotify_url")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory for files")
@click.option("--whisper-model", "-m", default="base",
              type=click.Choice(["tiny", "base", "small", "medium", "large", "turbo"]),
              help="Whisper model to use for transcription")
@click.option("--summary-type", "-s", default="comprehensive",
              type=click.Choice(["brief", "comprehensive", "bullet_points"]),
              help="Type of summary to generate")
@click.option("--language", "-l", help="Language code for transcription (auto-detect if not specified)")
@click.option("--keep-audio", is_flag=True, help="Keep downloaded audio file")
@click.option("--keep-transcript", is_flag=True, help="Keep transcription file")
@click.option("--chunk-duration", default=300, type=int, help="Duration of chunks in seconds for long podcasts")
@click.pass_context
def process(ctx, spotify_url, output_dir, whisper_model, summary_type, language,
           keep_audio, keep_transcript, chunk_duration):
    """Process a podcast from Spotify URL to summary.

    This command downloads the podcast, transcribes it, and generates a summary
    in a single workflow.

    SPOTIFY_URL: Spotify URL of the podcast episode
    """
    verbose = ctx.obj.get("verbose", False)

    # Set up output directory
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path.cwd()

    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        click.echo("❌ Error: GEMINI_API_KEY environment variable not set.", err=True)
        click.echo("Please set your Google Gemini API key:")
        click.echo("export GEMINI_API_KEY='your-api-key-here'")
        ctx.exit(1)

    try:
        # Step 1: Download podcast
        click.echo("🎵 Starting podcast processing...")
        downloader = PodcastDownloader(output_dir=str(output_path) if keep_audio else None)

        # Get episode info first
        click.echo("📡 Fetching episode information...")
        episode_info = downloader.get_episode_info(spotify_url)
        click.echo(f"📺 Title: {episode_info['title']}")
        click.echo(f"👤 Artist: {episode_info['artist']}")
        click.echo(f"⏱️  Duration: {episode_info['duration']} seconds")

        # Download audio
        audio_file = downloader.download(spotify_url)

        # Step 2: Transcribe
        click.echo("🎤 Transcribing audio...")
        transcriber = PodcastTranscriber(model_name=whisper_model)

        # Estimate transcription time
        estimated_time = transcriber.estimate_transcription_time(
            episode_info['duration'], whisper_model
        )
        click.echo(f"⏱️  Estimated transcription time: {estimated_time:.1f} seconds")

        # Transcribe with chunks for long episodes
        if episode_info['duration'] > chunk_duration:
            click.echo(f"📝 Long episode detected. Using {chunk_duration}s chunks...")
            transcription_result = transcriber.transcribe_with_summary_chunks(
                audio_file, chunk_duration=chunk_duration, language=language
            )
        else:
            transcription_result = {
                "full_transcription": transcriber.transcribe(
                    audio_file, language=language, include_timestamps=True
                )
            }

        # Save transcription if requested
        if keep_transcript:
            transcript_file = output_path / f"{Path(audio_file).stem}_transcript.json"
            transcriber.save_transcription(transcription_result, transcript_file)

        # Step 3: Summarize
        click.echo("🤖 Generating summary with Gemini Flash 2.5...")
        summarizer = PodcastSummarizer()

        if "chunks" in transcription_result:
            # Chunk-based summarization for long episodes
            summary_result = summarizer.summarize_chunks(
                transcription_result["chunks"],
                chunk_summary_type="brief",
                final_summary_type=summary_type
            )
        else:
            # Direct summarization for shorter episodes
            summary_result = summarizer.summarize(
                transcription_result["full_transcription"]["text"],
                summary_type=summary_type
            )

        # Step 4: Save results
        episode_name = Path(audio_file).stem

        # Save summary in multiple formats
        summary_json = output_path / f"{episode_name}_summary.json"
        summary_md = output_path / f"{episode_name}_summary.md"
        summary_txt = output_path / f"{episode_name}_summary.txt"

        summarizer.save_summary(summary_result, summary_json, format="json")
        summarizer.save_summary(summary_result, summary_md, format="md")
        summarizer.save_summary(summary_result, summary_txt, format="txt")

        # Cleanup
        if not keep_audio:
            downloader.cleanup(audio_file)

        # Show results
        click.echo("\n✅ Processing complete!")
        click.echo(f"📄 Summary saved to: {summary_md}")
        click.echo(f"📊 JSON data saved to: {summary_json}")
        click.echo(f"📝 Text summary saved to: {summary_txt}")

        if verbose:
            click.echo(f"\n📈 Statistics:")
            if "final_summary" in summary_result:
                click.echo(f"   • Total chunks: {summary_result['total_chunks']}")
                click.echo(f"   • Compression ratio: {summary_result['final_summary'].get('compression_ratio', 'N/A')}")
            else:
                click.echo(f"   • Compression ratio: {summary_result.get('compression_ratio', 'N/A')}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--whisper-model", "-m", default="base",
              type=click.Choice(["tiny", "base", "small", "medium", "large", "turbo"]),
              help="Whisper model to use for transcription")
@click.option("--summary-type", "-s", default="comprehensive",
              type=click.Choice(["brief", "comprehensive", "bullet_points"]),
              help="Type of summary to generate")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory for files")
@click.option("--language", "-l", help="Language code for transcription")
@click.pass_context
def demo(ctx, input_file, whisper_model, summary_type, output_dir, language):
    """Demo mode: Process an audio file without Spotify.

    This command transcribes and summarizes an audio file directly,
    bypassing Spotify download requirements.

    INPUT_FILE: Path to an audio file (MP3, WAV, etc.)
    """
    verbose = ctx.obj.get("verbose", False)

    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        click.echo("❌ Error: GEMINI_API_KEY environment variable not set.", err=True)
        click.echo("Please set your Google Gemini API key:")
        click.echo("export GEMINI_API_KEY='your-api-key-here'")
        ctx.exit(1)

    # Set up output directory
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path.cwd()

    try:
        audio_file = Path(input_file)
        click.echo(f"🎵 Processing audio file: {audio_file.name}")

        # Step 1: Transcribe
        click.echo("🎤 Transcribing audio...")
        transcriber = PodcastTranscriber(model_name=whisper_model)

        transcription_result = transcriber.transcribe(
            audio_file, language=language, include_timestamps=True
        )

        # Step 2: Summarize
        click.echo("🤖 Generating summary with Gemini Flash 2.5...")
        summarizer = PodcastSummarizer()

        summary_result = summarizer.summarize(
            transcription_result["text"],
            summary_type=summary_type
        )

        # Step 3: Save results
        base_name = audio_file.stem

        # Save in multiple formats
        summary_json = output_path / f"{base_name}_summary.json"
        summary_md = output_path / f"{base_name}_summary.md"
        summary_txt = output_path / f"{base_name}_summary.txt"
        transcript_json = output_path / f"{base_name}_transcript.json"

        # Save transcription
        transcriber.save_transcription({"full_transcription": transcription_result}, transcript_json)

        # Save summaries
        summarizer.save_summary(summary_result, summary_json, format="json")
        summarizer.save_summary(summary_result, summary_md, format="md")
        summarizer.save_summary(summary_result, summary_txt, format="txt")

        # Show results
        click.echo("\n✅ Processing complete!")
        click.echo(f"📄 Summary saved to: {summary_md}")
        click.echo(f"📊 JSON data saved to: {summary_json}")
        click.echo(f"📝 Text summary saved to: {summary_txt}")
        click.echo(f"🎤 Transcript saved to: {transcript_json}")

        if verbose:
            click.echo(f"\n📈 Statistics:")
            click.echo(f"   • Original words: {summary_result.get('original_length', 'N/A')}")
            click.echo(f"   • Summary words: {summary_result.get('summary_length', 'N/A')}")
            click.echo(f"   • Compression ratio: {summary_result.get('compression_ratio', 'N/A')}")
            click.echo(f"   • Language detected: {transcription_result.get('language', 'unknown')}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@main.command()
@click.argument("audio_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--model", "-m", default="base",
              type=click.Choice(["tiny", "base", "small", "medium", "large", "turbo"]),
              help="Whisper model to use")
@click.option("--language", "-l", help="Language code for transcription")
@click.option("--format", "-f", default="json",
              type=click.Choice(["json", "txt", "srt"]),
              help="Output format")
@click.option("--timestamps", is_flag=True, default=True, help="Include timestamps")
@click.pass_context
def transcribe(ctx, audio_file, output, model, language, format, timestamps):
    """Transcribe an audio file using Whisper.

    AUDIO_FILE: Path to the audio file to transcribe
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        click.echo(f"🎤 Transcribing {audio_file} with {model} model...")

        transcriber = PodcastTranscriber(model_name=model)
        result = transcriber.transcribe(
            audio_file,
            language=language,
            include_timestamps=timestamps,
            verbose=verbose
        )

        # Determine output file
        if output:
            output_file = Path(output)
        else:
            audio_path = Path(audio_file)
            output_file = audio_path.parent / f"{audio_path.stem}_transcript.{format}"

        # Save transcription
        transcriber.save_transcription(result, output_file, format=format)

        click.echo(f"✅ Transcription saved to: {output_file}")

        if verbose:
            click.echo(f"📈 Statistics:")
            click.echo(f"   • Language detected: {result.get('language', 'unknown')}")
            click.echo(f"   • Segments: {len(result.get('segments', []))}")
            click.echo(f"   • Words: {len(result.get('text', '').split())}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@main.command()
@click.argument("text_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--type", "-t", default="comprehensive",
              type=click.Choice(["brief", "comprehensive", "bullet_points"]),
              help="Type of summary to generate")
@click.option("--format", "-f", default="md",
              type=click.Choice(["json", "txt", "md"]),
              help="Output format")
@click.option("--topics", type=int, help="Extract N key topics")
@click.pass_context
def summarize(ctx, text_file, output, type, format, topics):
    """Summarize a text file using Gemini Flash 2.5.

    TEXT_FILE: Path to the text file to summarize
    """
    verbose = ctx.obj.get("verbose", False)

    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        click.echo("❌ Error: GEMINI_API_KEY environment variable not set.", err=True)
        click.echo("Please set your Google Gemini API key:")
        click.echo("export GEMINI_API_KEY='your-api-key-here'")
        ctx.exit(1)

    try:
        # Read text file
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()

        click.echo(f"🤖 Summarizing {text_file} with Gemini Flash 2.5...")

        summarizer = PodcastSummarizer()
        result = summarizer.summarize(text, summary_type=type)

        # Extract topics if requested
        if topics:
            click.echo(f"🏷️  Extracting {topics} key topics...")
            key_topics = summarizer.extract_key_topics(text, num_topics=topics)
            result["key_topics"] = key_topics

        # Determine output file
        if output:
            output_file = Path(output)
        else:
            text_path = Path(text_file)
            output_file = text_path.parent / f"{text_path.stem}_summary.{format}"

        # Save summary
        summarizer.save_summary(result, output_file, format=format)

        click.echo(f"✅ Summary saved to: {output_file}")

        if verbose:
            click.echo(f"📈 Statistics:")
            click.echo(f"   • Original words: {result.get('original_length', 'N/A')}")
            click.echo(f"   • Summary words: {result.get('summary_length', 'N/A')}")
            click.echo(f"   • Compression ratio: {result.get('compression_ratio', 'N/A')}")
            if topics and "key_topics" in result:
                click.echo(f"   • Key topics: {', '.join(result['key_topics'])}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        ctx.exit(1)


@main.command()
@click.argument("spotify_url")
@click.pass_context
def info(ctx, spotify_url):
    """Get information about a Spotify podcast episode.

    SPOTIFY_URL: Spotify URL of the podcast episode
    """
    try:
        downloader = PodcastDownloader()
        episode_info = downloader.get_episode_info(spotify_url)

        click.echo("📺 Episode Information:")
        click.echo(f"   Title: {episode_info['title']}")
        click.echo(f"   Artist: {episode_info['artist']}")
        click.echo(f"   Album: {episode_info['album']}")
        click.echo(f"   Duration: {episode_info['duration']} seconds ({episode_info['duration']//60:.0f}:{episode_info['duration']%60:02.0f})")
        click.echo(f"   Release Date: {episode_info['release_date']}")
        click.echo(f"   URL: {episode_info['url']}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        ctx.exit(1)


@main.command()
def models():
    """List available Whisper models and their characteristics."""
    click.echo("🎤 Available Whisper Models:")
    click.echo()

    models_info = [
        ("tiny", "~1 GB", "~32x realtime", "English-only"),
        ("base", "~1 GB", "~16x realtime", "Multilingual"),
        ("small", "~2 GB", "~6x realtime", "Multilingual"),
        ("medium", "~5 GB", "~2x realtime", "Multilingual"),
        ("large", "~10 GB", "~1x realtime", "Multilingual"),
        ("turbo", "~6 GB", "~8x realtime", "Multilingual (optimized)")
    ]

    for model, size, speed, lang in models_info:
        click.echo(f"   {model:<8} | {size:<8} | {speed:<15} | {lang}")


@main.command()
def setup():
    """Help set up the environment and API keys."""
    click.echo("🛠️  Setup Guide for Podcast Summarization Tool")
    click.echo()

    click.echo("1. Install FFmpeg (required for audio processing):")
    click.echo("   macOS: brew install ffmpeg")
    click.echo("   Ubuntu: sudo apt install ffmpeg")
    click.echo("   Windows: Download from https://ffmpeg.org/")
    click.echo()

    click.echo("2. Get Google Gemini API Key:")
    click.echo("   • Visit: https://ai.google.dev/")
    click.echo("   • Create an account and get your API key")
    click.echo("   • Set environment variable: export GEMINI_API_KEY='your-key'")
    click.echo()

    click.echo("3. Install the tool:")
    click.echo("   pip install -e .")
    click.echo()

    click.echo("4. Test the installation:")
    click.echo("   podcast-summarize models")
    click.echo()

    # Check current environment
    click.echo("📋 Current Environment Status:")

    # Check FFmpeg
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        click.echo("   ✅ FFmpeg: Installed")
    except:
        click.echo("   ❌ FFmpeg: Not found")

    # Check API key
    if os.getenv("GEMINI_API_KEY"):
        click.echo("   ✅ Gemini API Key: Set")
    else:
        click.echo("   ❌ Gemini API Key: Not set")


if __name__ == "__main__":
    main()
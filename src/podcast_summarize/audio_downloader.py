"""Download audio files using yt-dlp for YouTube and other platforms."""

import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import click
import yt_dlp


class AudioDownloader:
    """Download audio files using yt-dlp."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the audio downloader.

        Args:
            output_dir: Directory to save downloaded files. If None, uses temp directory.
        """
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir())
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_by_search(self, title: str, artist_or_show: str) -> Path:
        """Download audio by searching with title and artist/show name on YouTube.

        Args:
            title: Episode or track title
            artist_or_show: Artist name or podcast show name

        Returns:
            Path to the downloaded audio file

        Raises:
            RuntimeError: If download fails
        """
        try:
            # Create search query
            search_query = f"{title} {artist_or_show}"
            click.echo(f"🔍 Searching YouTube for: {search_query}")

            # Configure yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': '320K',
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
            }

            click.echo("⬇️ Downloading audio...")

            # Search and download using yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search for the video
                search_url = f"ytsearch1:{search_query}"
                info = ydl.extract_info(search_url, download=False)

                if not info or 'entries' not in info or len(info['entries']) == 0:
                    raise RuntimeError("No videos found for the search query")

                video_info = info['entries'][0]
                video_url = video_info['webpage_url']

                click.echo(f"Found: {video_info.get('title', 'Unknown')}")

                # Download the audio
                ydl.download([video_url])

            # Find the downloaded file
            downloaded_files = list(self.output_dir.glob("*.mp3")) + list(self.output_dir.glob("*.m4a")) + list(self.output_dir.glob("*.webm"))

            if not downloaded_files:
                raise RuntimeError("No audio files found after download")

            # Get the most recently created file
            downloaded_file = max(downloaded_files, key=lambda p: p.stat().st_ctime)

            click.echo(f"✅ Downloaded: {downloaded_file.name}")
            return downloaded_file

        except Exception as e:
            raise RuntimeError(f"Download failed: {str(e)}") from e

    def download_from_url(self, url: str) -> Path:
        """Download audio directly from a YouTube URL or other supported platforms.

        Args:
            url: YouTube URL or other platform URL supported by yt-dlp

        Returns:
            Path to the downloaded audio file

        Raises:
            RuntimeError: If download fails
        """
        try:
            click.echo(f"⬇️ Downloading from URL: {url}")

            # Configure yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': '320K',
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
            }

            # Download using yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find the downloaded file
            downloaded_files = list(self.output_dir.glob("*.mp3")) + list(self.output_dir.glob("*.m4a")) + list(self.output_dir.glob("*.webm"))

            if not downloaded_files:
                raise RuntimeError("No audio files found after download")

            # Get the most recently created file
            downloaded_file = max(downloaded_files, key=lambda p: p.stat().st_ctime)

            click.echo(f"✅ Downloaded: {downloaded_file.name}")
            return downloaded_file

        except Exception as e:
            raise RuntimeError(f"Download failed: {str(e)}") from e

    def cleanup(self, file_path: Path) -> None:
        """Clean up downloaded files.

        Args:
            file_path: Path to the file to delete
        """
        try:
            if file_path.exists():
                file_path.unlink()
                click.echo(f"Cleaned up: {file_path}")
        except Exception as e:
            click.echo(f"Warning: Could not clean up {file_path}: {e}")
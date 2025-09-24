"""Download podcasts from Spotify URLs using spotdl."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import click
from tqdm import tqdm


class PodcastDownloader:
    """Download podcasts from Spotify URLs."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the downloader.

        Args:
            output_dir: Directory to save downloaded files. If None, uses temp directory.
        """
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir())
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # spotdl CLI works without credentials for public content
        # We'll use subprocess to call spotdl directly
        self.spotdl = None  # We'll use CLI instead

    def is_valid_spotify_url(self, url: str) -> bool:
        """Check if the URL is a valid Spotify URL.

        Args:
            url: The URL to validate

        Returns:
            True if valid Spotify URL, False otherwise
        """
        try:
            parsed = urlparse(url)
            return (
                parsed.netloc in ["open.spotify.com", "spotify.com"] and
                any(parsed.path.startswith(prefix) for prefix in ["/episode/", "/show/", "/track/", "/playlist/", "/album/"])
            )
        except Exception:
            return False

    def download(self, spotify_url: str, progress_callback=None) -> Path:
        """Download a podcast episode from Spotify URL.

        Args:
            spotify_url: Spotify URL of the podcast episode
            progress_callback: Optional callback for progress updates

        Returns:
            Path to the downloaded audio file

        Raises:
            ValueError: If the URL is invalid
            RuntimeError: If download fails
        """
        if not self.is_valid_spotify_url(spotify_url):
            raise ValueError(f"Invalid Spotify URL: {spotify_url}")

        try:
            click.echo("📡 Fetching episode information...")

            # Use spotdl CLI to download without requiring credentials
            cmd = [
                "spotdl",
                "download",
                spotify_url,
                "--output", str(self.output_dir),
                "--format", "mp3",
                "--bitrate", "320k"
            ]

            click.echo("⬇️ Downloading audio...")

            # Run spotdl command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.output_dir)
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                raise RuntimeError(f"spotdl download failed: {error_msg}")

            # Find the downloaded file
            downloaded_files = list(self.output_dir.glob("*.mp3"))

            if not downloaded_files:
                raise RuntimeError("No MP3 files found after download")

            # Get the most recently created file
            downloaded_file = max(downloaded_files, key=lambda p: p.stat().st_ctime)

            click.echo(f"✅ Downloaded: {downloaded_file.name}")
            return downloaded_file

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Download command failed: {str(e)}") from e
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

    def get_episode_info(self, spotify_url: str) -> dict:
        """Get information about the episode without downloading.

        Args:
            spotify_url: Spotify URL of the podcast episode

        Returns:
            Dictionary with episode information

        Raises:
            ValueError: If the URL is invalid
            RuntimeError: If fetching info fails
        """
        if not self.is_valid_spotify_url(spotify_url):
            raise ValueError(f"Invalid Spotify URL: {spotify_url}")

        try:
            # Use spotdl to get metadata without downloading
            cmd = ["spotdl", "save", spotify_url, "--save-file", "-"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                error_msg = result.stderr or "Failed to get episode info"
                raise RuntimeError(f"spotdl info failed: {error_msg}")

            # Parse the output (spotdl save outputs JSON array)
            import json
            try:
                # Find where JSON starts (after the processing lines)
                output = result.stdout
                json_start = output.find('[')

                if json_start != -1:
                    json_data = output[json_start:].strip()
                    songs_data = json.loads(json_data)

                    if songs_data and len(songs_data) > 0:
                        song_data = songs_data[0]  # Get first song

                        return {
                            "title": song_data.get("name", "Unknown"),
                            "artist": ", ".join(song_data.get("artists", ["Unknown"])),
                            "album": song_data.get("album_name", "Unknown"),
                            "duration": song_data.get("duration", 0),
                            "url": spotify_url,
                            "release_date": song_data.get("date", "Unknown"),
                        }
                    else:
                        raise RuntimeError("Empty songs array returned")
                else:
                    raise RuntimeError("No JSON data found in output")

            except json.JSONDecodeError:
                # Fallback: try to parse from stdout text
                output = result.stdout
                return {
                    "title": "Unknown (parsing failed)",
                    "artist": "Unknown",
                    "album": "Unknown",
                    "duration": 0,
                    "url": spotify_url,
                    "release_date": "Unknown",
                    "raw_output": output
                }

        except Exception as e:
            raise RuntimeError(f"Failed to get episode info: {str(e)}") from e
"""Download audio files using yt-dlp for YouTube and other platforms."""

import re
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import click
import yt_dlp


class AudioDownloader:
    """Download audio files using yt-dlp."""

    def __init__(self, output_dir: Optional[str] = None, auto_confirm: bool = False, verbose: bool = False):
        """Initialize the audio downloader.

        Args:
            output_dir: Directory to save downloaded files. If None, uses temp directory.
            auto_confirm: If True, skip confirmation prompts and download automatically.
            verbose: If True, show detailed search and download information.
        """
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir())
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.auto_confirm = auto_confirm
        self.verbose = verbose

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
            # Create search query with fallback strategies (show name first for better podcast discovery)
            original_query = f"{artist_or_show} {title}"
            click.echo(f"🔍 Searching YouTube for: {original_query}")

            # Create fallback queries in case the first one fails
            fallback_queries = self._create_fallback_queries(title, artist_or_show)

            if fallback_queries:
                click.echo(f"   🔄 Fallback strategies prepared: {len(fallback_queries)} alternatives")
                for i, query in enumerate(fallback_queries, 1):
                    click.echo(f"      {i}. {query}")

            if self.verbose:
                click.echo(f"   📋 Search parameters:")
                click.echo(f"      Title: '{title}'")
                click.echo(f"      Show: '{artist_or_show}'")
                click.echo(f"      Full query: '{original_query}' ({len(original_query)} chars)")

            # Configure yt-dlp options for search only (minimal to avoid issues)
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 10,
            }

            # Search using minimal yt-dlp options
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                # Try the original query first, then fallbacks
                all_queries = [original_query] + fallback_queries
                video_info = None
                successful_query = None

                for i, query in enumerate(all_queries):
                    try:
                        if i > 0:
                            click.echo(f"   🔄 Trying fallback query {i}: '{query}'")

                        search_url = f"ytsearch1:{query}"
                        info = ydl.extract_info(search_url, download=False)

                        if info and 'entries' in info and len(info['entries']) > 0:
                            video_info = info['entries'][0]
                            successful_query = query
                            if i > 0:
                                click.echo(f"   ✅ Success with query: '{query}'")
                            break
                        else:
                            click.echo(f"   ❌ No results for: '{query}'")

                    except Exception as e:
                        click.echo(f"   ❌ Query failed: '{query}' - {e}")
                        continue

                if not video_info:
                    raise RuntimeError(f"No videos found for any search query (tried {len(all_queries)} variations)")

                if self.verbose:
                    click.echo(f"   ✅ Found {len(info['entries'])} result(s)")

                video_info = info['entries'][0]
                video_url = video_info['webpage_url']

                if self.verbose:
                    view_count = video_info.get('view_count', 'Unknown')
                    upload_date = video_info.get('upload_date', 'Unknown')
                    click.echo(f"   📊 Video details:")
                    click.echo(f"      ID: {video_info.get('id', 'Unknown')}")
                    click.echo(f"      Views: {view_count:,}" if isinstance(view_count, int) else f"      Views: {view_count}")
                    click.echo(f"      Upload date: {upload_date}")
                    click.echo(f"      URL: {video_url}")

                # Show user what was found and ask for confirmation
                title = video_info.get('title', 'Unknown')
                uploader = video_info.get('uploader', 'Unknown Channel')
                duration = video_info.get('duration', 0)
                duration_str = f"{duration//60}:{duration%60:02d}" if duration else "Unknown"

                click.echo(f"\n📺 Found YouTube video:")
                click.echo(f"   Title: {title}")
                click.echo(f"   Channel: {uploader}")
                click.echo(f"   Duration: {duration_str}")
                click.echo(f"   URL: {video_url}")

                # Ask for confirmation unless auto-confirm is enabled
                if not self.auto_confirm:
                    if not click.confirm(f"\nIs this the correct video? Download audio from '{title}'?"):
                        raise RuntimeError("User cancelled download - video not confirmed")
                else:
                    click.echo(f"\n✅ Auto-confirming download of '{title}'")

                # Configure yt-dlp options for download
                download_opts = {
                    'format': 'bestaudio/best',
                    'extractaudio': True,
                    'audioformat': 'mp3',
                    'audioquality': '320K',
                    'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 30,
                }

                click.echo("⬇️ Downloading audio...")
                # Download the audio with separate downloader instance
                with yt_dlp.YoutubeDL(download_opts) as download_ydl:
                    download_ydl.download([video_url])

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
            click.echo(f"📡 Getting video information from: {url}")

            # Configure yt-dlp options for info extraction
            info_opts = {
                'quiet': True,
                'no_warnings': True,
            }

            # Get video info first
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)

                # Show user what was found and ask for confirmation
                title = video_info.get('title', 'Unknown')
                uploader = video_info.get('uploader', 'Unknown Channel')
                duration = video_info.get('duration', 0)
                duration_str = f"{duration//60}:{duration%60:02d}" if duration else "Unknown"

                click.echo(f"\n📺 Found YouTube video:")
                click.echo(f"   Title: {title}")
                click.echo(f"   Channel: {uploader}")
                click.echo(f"   Duration: {duration_str}")
                click.echo(f"   URL: {url}")

                # Ask for confirmation unless auto-confirm is enabled
                if not self.auto_confirm:
                    if not click.confirm(f"\nIs this the correct video? Download audio from '{title}'?"):
                        raise RuntimeError("User cancelled download - video not confirmed")
                else:
                    click.echo(f"\n✅ Auto-confirming download of '{title}'")

            # Configure yt-dlp options for download
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

    def _create_fallback_queries(self, title: str, show: str) -> list[str]:
        """Create fallback search queries with different strategies."""
        fallback_queries = []

        # Clean up title by removing special characters and common words
        title_cleaned = re.sub(r'[^\w\s-]', ' ', title)  # Remove special chars except hyphens
        title_words = [w for w in title_cleaned.split() if len(w) > 2 and w.lower() not in ['the', 'and', 'vs', 'with']]

        # Apply common term substitutions for better matching
        title_with_substitutions = self._apply_term_substitutions(title)
        title_sub_cleaned = re.sub(r'[^\w\s-]', ' ', title_with_substitutions)
        title_sub_words = [w for w in title_sub_cleaned.split() if len(w) > 2 and w.lower() not in ['the', 'and', 'vs', 'with']]

        # Clean up show name
        show_cleaned = re.sub(r'[^\w\s]', ' ', show)

        # Strategy 1: Show name + key title words with substitutions
        if len(title_sub_words) > 3:
            key_words = title_sub_words[:3]  # First 3 meaningful words
            fallback_queries.append(f"{show_cleaned} {' '.join(key_words)}")

        # Strategy 2: Show name + key title words (original)
        if len(title_words) > 3:
            key_words = title_words[:3]  # First 3 meaningful words
            fallback_queries.append(f"{show_cleaned} {' '.join(key_words)}")

        # Strategy 3: Show name + fewer title words with substitutions
        if len(title_sub_words) >= 2:
            fallback_queries.append(f"{show_cleaned} {' '.join(title_sub_words[:2])}")

        # Strategy 4: Show name + fewer title words (original)
        if len(title_words) >= 2:
            fallback_queries.append(f"{show_cleaned} {' '.join(title_words[:2])}")

        return fallback_queries

    def _apply_term_substitutions(self, title: str) -> str:
        """Apply common term substitutions to improve search matching."""
        substitutions = {
            'GPT-OSS': 'OpenAI',
            'GPT OSS': 'OpenAI',
            'ChatGPT': 'OpenAI',
            'GPT': 'OpenAI',
        }

        result = title
        for original, replacement in substitutions.items():
            result = re.sub(r'\b' + re.escape(original) + r'\b', replacement, result, flags=re.IGNORECASE)

        return result
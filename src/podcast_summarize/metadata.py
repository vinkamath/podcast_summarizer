"""Extract podcast metadata from Spotify URLs."""

import re
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import click
import requests
from bs4 import BeautifulSoup


class SpotifyMetadataExtractor:
    """Extract podcast metadata from Spotify URLs without authentication."""

    def __init__(self):
        """Initialize the metadata extractor."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def is_valid_spotify_url(self, url: str) -> bool:
        """Check if the URL is a valid Spotify podcast URL.

        Args:
            url: The URL to validate

        Returns:
            True if valid Spotify podcast URL, False otherwise
        """
        try:
            parsed = urlparse(url)
            return (
                parsed.netloc in ["open.spotify.com", "spotify.com"] and
                any(parsed.path.startswith(prefix) for prefix in ["/episode/", "/show/"])
            )
        except Exception:
            return False

    def extract_spotify_id(self, url: str) -> tuple[str, str]:
        """Extract Spotify ID and type from URL.

        Args:
            url: Spotify URL

        Returns:
            Tuple of (content_type, spotify_id)

        Raises:
            ValueError: If URL format is invalid
        """
        # Pattern to match Spotify URLs, including query parameters
        pattern = r'https://open\.spotify\.com/(episode|show)/([a-zA-Z0-9]+)(?:\?.*)?'
        match = re.match(pattern, url)

        if not match:
            raise ValueError(f"Invalid Spotify URL format: {url}")

        content_type, spotify_id = match.groups()
        return content_type, spotify_id

    def get_episode_metadata(self, spotify_url: str) -> Dict[str, Any]:
        """Get podcast episode metadata from Spotify URL.

        Args:
            spotify_url: Spotify URL of the podcast episode

        Returns:
            Dictionary with episode metadata

        Raises:
            ValueError: If the URL is invalid
            RuntimeError: If metadata extraction fails
        """
        if not self.is_valid_spotify_url(spotify_url):
            raise ValueError(f"Invalid Spotify URL: {spotify_url}")

        try:
            click.echo("📡 Fetching episode metadata...")

            # Get the webpage content
            response = self.session.get(spotify_url, timeout=10)
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract metadata from various sources
            metadata = self._extract_metadata_from_html(soup, spotify_url)

            click.echo(f"✅ Retrieved metadata for: {metadata.get('title', 'Unknown')}")
            return metadata

        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch webpage: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Metadata extraction failed: {str(e)}") from e

    def _extract_metadata_from_html(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract metadata from Spotify webpage HTML.

        Args:
            soup: BeautifulSoup object of the webpage
            url: Original Spotify URL

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            "url": url,
            "title": "Unknown",
            "description": "",
            "show_name": "Unknown",
            "publisher": "Unknown",
            "duration": "Unknown",
            "release_date": "Unknown",
            "image_url": None
        }

        try:
            # Try to extract from JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        data = data[0] if data else {}

                    if data.get('@type') == 'PodcastEpisode':
                        metadata.update({
                            "title": data.get('name', metadata['title']),
                            "description": data.get('description', metadata['description']),
                            "duration": data.get('duration', metadata['duration']),
                            "release_date": data.get('datePublished', metadata['release_date']),
                        })

                        # Extract show info
                        if 'partOfSeries' in data:
                            series = data['partOfSeries']
                            metadata['show_name'] = series.get('name', metadata['show_name'])
                            metadata['publisher'] = series.get('publisher', {}).get('name', metadata['publisher'])

                        # Extract image
                        if 'image' in data:
                            if isinstance(data['image'], str):
                                metadata['image_url'] = data['image']
                            elif isinstance(data['image'], dict):
                                metadata['image_url'] = data['image'].get('url')

                        return metadata
                except (json.JSONDecodeError, KeyError):
                    continue

            # Fallback: extract from meta tags
            title_tag = soup.find('meta', property='og:title')
            if title_tag:
                metadata['title'] = title_tag.get('content', metadata['title'])

            desc_tag = soup.find('meta', property='og:description')
            if desc_tag:
                metadata['description'] = desc_tag.get('content', metadata['description'])

            image_tag = soup.find('meta', property='og:image')
            if image_tag:
                metadata['image_url'] = image_tag.get('content')

            # Try to extract from page title
            if metadata['title'] == 'Unknown':
                title_element = soup.find('title')
                if title_element:
                    title_text = title_element.get_text().strip()
                    # Parse format like "Episode Name | Show Name | Spotify"
                    if ' | ' in title_text:
                        parts = title_text.split(' | ')
                        if len(parts) >= 2:
                            metadata['title'] = parts[0].strip()
                            metadata['show_name'] = parts[1].strip()

            # Try to extract show name from description if still unknown
            if metadata['show_name'] == 'Unknown' and metadata['description']:
                desc = metadata['description']
                # Handle format "Show Name · Episode" or "Show Name · Something"
                if ' · ' in desc:
                    parts = desc.split(' · ')
                    if len(parts) >= 1:
                        potential_show = parts[0].strip()
                        # Avoid using "Unknown" or very short strings as show names
                        if potential_show and potential_show != 'Unknown' and len(potential_show) > 3:
                            metadata['show_name'] = potential_show

        except Exception as e:
            click.echo(f"Warning: Error extracting some metadata: {e}")

        return metadata

    def get_show_metadata(self, spotify_show_url: str) -> Dict[str, Any]:
        """Get podcast show metadata from Spotify URL.

        Args:
            spotify_show_url: Spotify URL of the podcast show

        Returns:
            Dictionary with show metadata

        Raises:
            ValueError: If the URL is invalid
            RuntimeError: If metadata extraction fails
        """
        if not self.is_valid_spotify_url(spotify_show_url):
            raise ValueError(f"Invalid Spotify URL: {spotify_show_url}")

        content_type, _ = self.extract_spotify_id(spotify_show_url)
        if content_type != 'show':
            raise ValueError(f"URL must be a show, not {content_type}")

        try:
            click.echo("📡 Fetching show metadata...")

            # Get the webpage content
            response = self.session.get(spotify_show_url, timeout=10)
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract show metadata
            metadata = self._extract_show_metadata_from_html(soup, spotify_show_url)

            click.echo(f"✅ Retrieved show metadata for: {metadata.get('name', 'Unknown')}")
            return metadata

        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch webpage: {str(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Show metadata extraction failed: {str(e)}") from e

    def _extract_show_metadata_from_html(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract show metadata from Spotify webpage HTML.

        Args:
            soup: BeautifulSoup object of the webpage
            url: Original Spotify URL

        Returns:
            Dictionary with extracted show metadata
        """
        metadata = {
            "url": url,
            "name": "Unknown",
            "description": "",
            "publisher": "Unknown",
            "image_url": None,
            "total_episodes": "Unknown"
        }

        try:
            # Try to extract from JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        data = data[0] if data else {}

                    if data.get('@type') == 'PodcastSeries':
                        metadata.update({
                            "name": data.get('name', metadata['name']),
                            "description": data.get('description', metadata['description']),
                            "publisher": data.get('publisher', {}).get('name', metadata['publisher']) if isinstance(data.get('publisher'), dict) else data.get('publisher', metadata['publisher']),
                        })

                        # Extract image
                        if 'image' in data:
                            if isinstance(data['image'], str):
                                metadata['image_url'] = data['image']
                            elif isinstance(data['image'], dict):
                                metadata['image_url'] = data['image'].get('url')

                        return metadata
                except (json.JSONDecodeError, KeyError):
                    continue

            # Fallback: extract from meta tags
            title_tag = soup.find('meta', property='og:title')
            if title_tag:
                metadata['name'] = title_tag.get('content', metadata['name'])

            desc_tag = soup.find('meta', property='og:description')
            if desc_tag:
                metadata['description'] = desc_tag.get('content', metadata['description'])

            image_tag = soup.find('meta', property='og:image')
            if image_tag:
                metadata['image_url'] = image_tag.get('content')

        except Exception as e:
            click.echo(f"Warning: Error extracting some show metadata: {e}")

        return metadata
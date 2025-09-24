#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from podcast_summarize.downloader import PodcastDownloader

# Test with real debugging
downloader = PodcastDownloader()
url = "https://open.spotify.com/episode/2kH22WJJL6k6HRk6oHxNNI?si=333ef8da1388424d"

try:
    print("Testing with debug...")

    # Get the webpage content directly
    response = downloader.session.get(url, timeout=10)
    response.raise_for_status()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    print(f"Status: {response.status_code}")

    # Test our metadata extraction function directly
    metadata = downloader._extract_metadata_from_html(soup, url)

    print("Metadata extracted:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    # Also check what we can see directly
    title_tag = soup.find('meta', property='og:title')
    print(f"\nDirect og:title check: {title_tag.get('content') if title_tag else 'Not found'}")

    desc_tag = soup.find('meta', property='og:description')
    print(f"Direct og:description check: {desc_tag.get('content')[:100] + '...' if desc_tag and desc_tag.get('content') else 'Not found'}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
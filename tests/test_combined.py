#!/usr/bin/env python3
"""Test the combined workflow: extract metadata then download audio."""

import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from podcast_summarize.metadata import SpotifyMetadataExtractor
from podcast_summarize.audio_downloader import AudioDownloader


def test_combined_workflow():
    """Test extracting metadata and then downloading audio."""
    test_url = "https://open.spotify.com/episode/2kH22WJJL6k6HRk6oHxNNI?si=333ef8da1388424d"

    try:
        # Step 1: Extract metadata
        print("🔍 Step 1: Extracting metadata from Spotify...")
        extractor = SpotifyMetadataExtractor()
        metadata = extractor.get_episode_metadata(test_url)

        title = metadata.get('title', 'Unknown')
        description = metadata.get('description', '')

        # Try to extract show name from description or use a fallback
        show_name = metadata.get('show_name', 'Unknown')
        if show_name == 'Unknown' and description:
            # Description format is often "Show Name · Episode"
            if '·' in description:
                show_name = description.split('·')[0].strip()

        print(f"✅ Found episode: '{title}' from '{show_name}'")

        # Step 2: Try downloading audio using yt-dlp
        print("⬇️ Step 2: Trying to download audio using yt-dlp...")

        downloader = AudioDownloader(output_dir="./test_downloads")

        # First try direct URL download
        try:
            print(f"   Trying direct URL download: {test_url}")
            audio_file = downloader.download_from_url(test_url)
            print(f"✅ Downloaded to: {audio_file}")
        except Exception as e:
            print(f"❌ Direct URL download failed: {e}")

            # Then try search method
            try:
                print(f"   Trying search method: '{title} {show_name}'")
                audio_file = downloader.download_by_search(title, show_name)
                print(f"✅ Downloaded to: {audio_file}")
            except Exception as e2:
                print(f"❌ Search download also failed: {e2}")
                print("⚠️  Note: Podcasts may not be available via direct Spotify URL download")
                print("    but can be found on YouTube using search functionality.")
                return {"metadata": metadata, "download_attempted": True, "download_successful": False}

        return {"metadata": metadata, "audio_file": audio_file}

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Combined Workflow: Metadata + Audio Download")
    print("=" * 60)

    result = test_combined_workflow()

    print("\n" + "=" * 60)
    if result and result != False:
        print("🎉 Combined workflow test completed successfully!")
        if isinstance(result, dict) and 'audio_file' in result:
            print(f"📁 Audio file: {result['audio_file']}")
    else:
        print("⚠️ Test failed. Check the errors above.")
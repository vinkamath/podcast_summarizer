#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from podcast_summarize.metadata import SpotifyMetadataExtractor
from podcast_summarize.audio_downloader import AudioDownloader

# Test with real debugging
def test_metadata_extraction():
    extractor = SpotifyMetadataExtractor()
    url = "https://open.spotify.com/episode/2kH22WJJL6k6HRk6oHxNNI?si=333ef8da1388424d"

    try:
        print("Testing metadata extraction...")
        metadata = extractor.get_episode_metadata(url)

        print("Metadata extracted:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")

        return metadata

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_audio_download():
    downloader = AudioDownloader(output_dir="./test_output")

    try:
        print("\nTesting audio download...")
        audio_file = downloader.download_by_search("How to Spend Your 20s in the AI Era", "Lightcone Podcast")
        print(f"Downloaded: {audio_file}")
        return audio_file
    except Exception as e:
        print(f"Download error: {e}")
        return None

if __name__ == "__main__":
    metadata = test_metadata_extraction()
    if metadata:
        test_audio_download()
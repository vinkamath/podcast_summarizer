"""Transcribe audio files using OpenAI Whisper."""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

import click
import whisper
from tqdm import tqdm


class PodcastTranscriber:
    """Transcribe audio files using OpenAI Whisper."""

    def __init__(self, model_name: str = "base"):
        """Initialize the transcriber.

        Args:
            model_name: Whisper model to use ("tiny", "base", "small", "medium", "large", "turbo")
        """
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the Whisper model."""
        click.echo(f"Loading Whisper model: {self.model_name}")
        try:
            with click.progressbar(
                length=100,
                label="Loading model",
                show_percent=True
            ) as bar:
                self.model = whisper.load_model(self.model_name)
                bar.update(100)
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model: {str(e)}") from e

    def transcribe(
        self,
        audio_file: Union[str, Path],
        language: Optional[str] = None,
        include_timestamps: bool = True,
        verbose: bool = False
    ) -> Dict:
        """Transcribe an audio file.

        Args:
            audio_file: Path to the audio file
            language: Language code (e.g., "en", "es"). Auto-detect if None
            include_timestamps: Whether to include word-level timestamps
            verbose: Whether to show detailed progress

        Returns:
            Dictionary containing transcription results

        Raises:
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If transcription fails
        """
        audio_path = Path(audio_file)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if self.model is None:
            raise RuntimeError("Whisper model not loaded")

        click.echo(f"Transcribing: {audio_path.name}")

        try:
            # Transcribe with progress indication
            with click.progressbar(
                length=100,
                label="Transcribing audio",
                show_percent=True
            ) as bar:
                # Whisper transcription options
                options = {
                    "language": language,
                    "task": "transcribe",
                    "word_timestamps": include_timestamps,
                    "verbose": verbose
                }

                # Remove None values
                options = {k: v for k, v in options.items() if v is not None}

                result = self.model.transcribe(str(audio_path), **options)
                bar.update(100)

            # Process the result
            processed_result = self._process_result(result, include_timestamps)

            click.echo("Transcription completed successfully")
            return processed_result

        except Exception as e:
            raise RuntimeError(f"Transcription failed: {str(e)}") from e

    def _process_result(self, result: Dict, include_timestamps: bool) -> Dict:
        """Process Whisper transcription result.

        Args:
            result: Raw Whisper result
            include_timestamps: Whether timestamps were requested

        Returns:
            Processed transcription result
        """
        processed = {
            "text": result["text"].strip(),
            "language": result.get("language", "unknown"),
            "segments": []
        }

        # Process segments
        for segment in result.get("segments", []):
            segment_data = {
                "id": segment.get("id", 0),
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 0.0),
                "text": segment.get("text", "").strip()
            }

            # Add word-level timestamps if available
            if include_timestamps and "words" in segment:
                segment_data["words"] = [
                    {
                        "word": word.get("word", ""),
                        "start": word.get("start", 0.0),
                        "end": word.get("end", 0.0),
                        "probability": word.get("probability", 0.0)
                    }
                    for word in segment["words"]
                ]

            processed["segments"].append(segment_data)

        return processed

    def transcribe_with_summary_chunks(
        self,
        audio_file: Union[str, Path],
        chunk_duration: int = 300,  # 5 minutes
        language: Optional[str] = None
    ) -> Dict:
        """Transcribe audio and prepare chunks suitable for summarization.

        Args:
            audio_file: Path to the audio file
            chunk_duration: Duration of each chunk in seconds
            language: Language code for transcription

        Returns:
            Dictionary with full transcription and chunks
        """
        # Get full transcription
        result = self.transcribe(audio_file, language=language, include_timestamps=True)

        # Create chunks based on time
        chunks = self._create_time_chunks(result["segments"], chunk_duration)

        return {
            "full_transcription": result,
            "chunks": chunks,
            "chunk_duration": chunk_duration,
            "total_chunks": len(chunks)
        }

    def _create_time_chunks(self, segments: List[Dict], chunk_duration: int) -> List[Dict]:
        """Create time-based chunks from segments.

        Args:
            segments: List of transcription segments
            chunk_duration: Duration of each chunk in seconds

        Returns:
            List of chunks with text and timing information
        """
        chunks = []
        current_chunk = {
            "start_time": 0,
            "end_time": chunk_duration,
            "text": "",
            "segment_count": 0
        }

        for segment in segments:
            segment_start = segment["start"]
            segment_end = segment["end"]
            segment_text = segment["text"]

            # If segment starts after current chunk end, create new chunk
            if segment_start >= current_chunk["end_time"]:
                if current_chunk["text"].strip():
                    chunks.append(current_chunk)

                # Start new chunk
                chunk_start = (segment_start // chunk_duration) * chunk_duration
                current_chunk = {
                    "start_time": chunk_start,
                    "end_time": chunk_start + chunk_duration,
                    "text": segment_text,
                    "segment_count": 1
                }
            else:
                # Add to current chunk
                current_chunk["text"] += " " + segment_text
                current_chunk["segment_count"] += 1
                current_chunk["end_time"] = max(current_chunk["end_time"], segment_end)

        # Add final chunk
        if current_chunk["text"].strip():
            chunks.append(current_chunk)

        return chunks

    def save_transcription(
        self,
        result: Dict,
        output_path: Union[str, Path],
        format: str = "json"
    ) -> None:
        """Save transcription to file.

        Args:
            result: Transcription result dictionary
            output_path: Output file path
            format: Output format ("json", "txt", "srt")

        Raises:
            ValueError: If format is not supported
        """
        output_path = Path(output_path)

        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

        elif format == "txt":
            with open(output_path, "w", encoding="utf-8") as f:
                if "full_transcription" in result:
                    f.write(result["full_transcription"]["text"])
                else:
                    f.write(result["text"])

        elif format == "srt":
            self._save_as_srt(result, output_path)

        else:
            raise ValueError(f"Unsupported format: {format}")

        click.echo(f"Transcription saved: {output_path}")

    def _save_as_srt(self, result: Dict, output_path: Path) -> None:
        """Save transcription as SRT subtitle file.

        Args:
            result: Transcription result
            output_path: Output SRT file path
        """
        segments = result.get("segments", [])
        if "full_transcription" in result:
            segments = result["full_transcription"]["segments"]

        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start_time = self._seconds_to_srt_time(segment["start"])
                end_time = self._seconds_to_srt_time(segment["end"])

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text'].strip()}\n\n")

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format.

        Args:
            seconds: Time in seconds

        Returns:
            Time in SRT format (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

    @staticmethod
    def get_available_models() -> List[str]:
        """Get list of available Whisper models.

        Returns:
            List of model names
        """
        return ["tiny", "base", "small", "medium", "large", "turbo"]

    @staticmethod
    def estimate_transcription_time(audio_duration: float, model_name: str) -> float:
        """Estimate transcription time based on audio duration and model.

        Args:
            audio_duration: Duration of audio in seconds
            model_name: Whisper model name

        Returns:
            Estimated transcription time in seconds
        """
        # Rough estimates based on model complexity
        model_multipliers = {
            "tiny": 0.1,
            "base": 0.2,
            "small": 0.3,
            "medium": 0.5,
            "large": 0.8,
            "turbo": 0.15
        }

        multiplier = model_multipliers.get(model_name, 0.5)
        return audio_duration * multiplier
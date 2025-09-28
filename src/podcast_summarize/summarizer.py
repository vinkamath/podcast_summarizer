"""Summarize text using Google Gemini Flash 2.5 API."""

import os
import json
from typing import Dict, List, Optional, Union
from pathlib import Path

import click
from google import genai
from dotenv import load_dotenv


class PodcastSummarizer:
    """Summarize podcast transcriptions using Google Gemini Flash 2.5."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the summarizer.

        Args:
            api_key: Google Gemini API key. If None, will try to get from environment.
        """
        # Load environment variables
        load_dotenv()

        # Get API key
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google Gemini API key is required. "
                "Set GEMINI_API_KEY environment variable or pass api_key parameter."
            )

        # Initialize the client
        try:
            os.environ["GEMINI_API_KEY"] = self.api_key
            self.client = genai.Client()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini client: {str(e)}") from e

        self.model_name = "gemini-2.5-flash"

    def summarize(
        self,
        text: str,
        summary_type: str = "comprehensive",
        max_length: Optional[int] = None,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Union[str, List[str]]]:
        """Summarize text using Gemini Flash 2.5.

        Args:
            text: Text to summarize
            summary_type: Type of summary ("brief", "comprehensive", "bullet_points")
            max_length: Maximum length of summary in words
            focus_areas: Specific areas to focus on in the summary

        Returns:
            Dictionary containing the summary and metadata

        Raises:
            ValueError: If text is too short or summary_type is invalid
            RuntimeError: If API call fails
        """
        if len(text.split()) < 50:
            raise ValueError("Text too short for meaningful summarization (minimum 50 words)")

        valid_types = ["brief", "comprehensive", "bullet_points"]
        if summary_type not in valid_types:
            raise ValueError(f"Invalid summary_type. Must be one of: {valid_types}")

        try:
            prompt = self._build_prompt(text, summary_type, max_length, focus_areas)

            click.echo("Generating summary with Gemini Flash 2.5...")

            with click.progressbar(
                length=100,
                label="Summarizing",
                show_percent=True
            ) as bar:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                bar.update(100)

            if not hasattr(response, 'text') or response.text is None:
                error_msg = "No text content in API response"
                if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason'):
                    error_msg += f" - Block reason: {response.prompt_feedback.block_reason}"
                if hasattr(response, 'candidates') and response.candidates:
                    if hasattr(response.candidates[0], 'finish_reason'):
                        error_msg += f" - Finish reason: {response.candidates[0].finish_reason}"
                    if hasattr(response.candidates[0], 'safety_ratings'):
                        error_msg += f" - Safety ratings: {response.candidates[0].safety_ratings}"
                raise RuntimeError(error_msg)

            summary_text = response.text.strip()

            # Process the response based on summary type
            result = self._process_summary_response(summary_text, summary_type)

            result.update({
                "model": self.model_name,
                "summary_type": summary_type,
                "original_length": len(text.split()),
                "summary_length": len(summary_text.split()),
                "compression_ratio": round(len(text.split()) / len(summary_text.split()), 2)
            })

            click.echo("Summary generated successfully")
            return result

        except Exception as e:
            raise RuntimeError(f"Summarization failed: {str(e)}") from e

    def _build_prompt(
        self,
        text: str,
        summary_type: str,
        max_length: Optional[int],
        focus_areas: Optional[List[str]]
    ) -> str:
        """Build the prompt for Gemini based on parameters.

        Args:
            text: Text to summarize
            summary_type: Type of summary requested
            max_length: Maximum length constraint
            focus_areas: Areas to focus on

        Returns:
            Formatted prompt string
        """
        base_prompt = f"""You are an expert at summarizing podcast content. Please analyze the following podcast transcription and provide a {summary_type} summary.

TRANSCRIPTION:
{text}

"""

        if summary_type == "brief":
            base_prompt += """Please provide a BRIEF summary (2-3 sentences) that captures the main topic and key message of this podcast episode."""

        elif summary_type == "comprehensive":
            base_prompt += """Please provide a COMPREHENSIVE summary that includes:
1. Main topic and theme
2. Key points and arguments presented
3. Important insights or takeaways
4. Notable quotes or memorable moments
5. Overall conclusions or call-to-action

Format your response in clear paragraphs with appropriate headings."""

        elif summary_type == "bullet_points":
            base_prompt += """Please provide a summary in BULLET POINT format that includes:
• Main topic and theme
• Key points discussed (3-5 main points)
• Important insights or revelations
• Notable quotes or statistics mentioned
• Main conclusions or recommendations

Use clear, concise bullet points that are easy to scan."""

        # Add length constraint if specified
        if max_length:
            base_prompt += f"\n\nPlease keep the summary under {max_length} words."

        # Add focus areas if specified
        if focus_areas:
            focus_list = ", ".join(focus_areas)
            base_prompt += f"\n\nPlease pay special attention to these topics: {focus_list}"

        base_prompt += "\n\nSUMMARY:"

        return base_prompt

    def _process_summary_response(self, response_text: str, summary_type: str) -> Dict[str, Union[str, List[str]]]:
        """Process the Gemini response based on summary type.

        Args:
            response_text: Raw response from Gemini
            summary_type: Type of summary that was requested

        Returns:
            Processed summary dictionary
        """
        result = {"raw_summary": response_text}

        if summary_type == "bullet_points":
            # Extract bullet points
            lines = response_text.split("\n")
            bullet_points = []

            for line in lines:
                line = line.strip()
                if line.startswith(("•", "-", "*")) or line.startswith(tuple(f"{i}." for i in range(1, 10))):
                    # Clean up the bullet point
                    clean_point = line.lstrip("•-*0123456789. ").strip()
                    if clean_point:
                        bullet_points.append(clean_point)

            result["bullet_points"] = bullet_points
            result["summary"] = response_text

        else:
            result["summary"] = response_text

        return result

    def summarize_chunks(
        self,
        chunks: List[Dict],
        chunk_summary_type: str = "brief",
        final_summary_type: str = "comprehensive"
    ) -> Dict:
        """Summarize multiple chunks and create a final summary.

        Args:
            chunks: List of text chunks with timing information
            chunk_summary_type: Summary type for individual chunks
            final_summary_type: Summary type for final combined summary

        Returns:
            Dictionary with chunk summaries and final summary
        """
        click.echo(f"Summarizing {len(chunks)} chunks...")

        chunk_summaries = []

        # Summarize each chunk
        for i, chunk in enumerate(chunks):
            click.echo(f"Summarizing chunk {i+1}/{len(chunks)} ({chunk['start_time']:.0f}-{chunk['end_time']:.0f}s)")

            try:
                summary = self.summarize(
                    chunk["text"],
                    summary_type=chunk_summary_type,
                    max_length=200  # Keep chunk summaries concise
                )

                chunk_summary = {
                    "chunk_id": i,
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "summary": summary["summary"],
                    "original_length": len(chunk["text"].split())
                }

                chunk_summaries.append(chunk_summary)

            except Exception as e:
                click.echo(f"Warning: Failed to summarize chunk {i+1}: {e}")
                chunk_summaries.append({
                    "chunk_id": i,
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "summary": f"[Failed to summarize: {str(e)}]",
                    "original_length": len(chunk["text"].split())
                })

        # Create final summary from chunk summaries
        combined_summaries = "\n\n".join([
            f"Segment {cs['start_time']:.0f}-{cs['end_time']:.0f}s: {cs['summary']}"
            for cs in chunk_summaries
        ])

        click.echo("Creating final comprehensive summary...")

        final_summary = self.summarize(
            combined_summaries,
            summary_type=final_summary_type
        )

        return {
            "chunk_summaries": chunk_summaries,
            "final_summary": final_summary,
            "total_chunks": len(chunks),
            "processing_info": {
                "chunk_summary_type": chunk_summary_type,
                "final_summary_type": final_summary_type
            }
        }

    def extract_key_topics(self, text: str, num_topics: int = 5) -> List[str]:
        """Extract key topics from the text.

        Args:
            text: Text to analyze
            num_topics: Number of key topics to extract

        Returns:
            List of key topics
        """
        prompt = f"""Analyze the following podcast transcription and extract the {num_topics} most important topics or themes discussed.

TRANSCRIPTION:
{text}

Please provide exactly {num_topics} key topics, one per line, in order of importance. Format each topic as a short phrase (2-5 words).

KEY TOPICS:"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )

            topics = []
            for line in response.text.strip().split("\n"):
                topic = line.strip().lstrip("1234567890.-• ").strip()
                if topic and len(topics) < num_topics:
                    topics.append(topic)

            return topics[:num_topics]

        except Exception as e:
            click.echo(f"Warning: Failed to extract topics: {e}")
            return []

    def save_summary(
        self,
        summary_data: Dict,
        output_path: Union[str, Path],
        format: str = "json"
    ) -> None:
        """Save summary to file.

        Args:
            summary_data: Summary data dictionary
            output_path: Output file path
            format: Output format ("json", "txt", "md")

        Raises:
            ValueError: If format is not supported
        """
        output_path = Path(output_path)

        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)

        elif format == "txt":
            with open(output_path, "w", encoding="utf-8") as f:
                if "final_summary" in summary_data:
                    f.write(summary_data["final_summary"]["summary"])
                else:
                    f.write(summary_data.get("summary", str(summary_data)))

        elif format == "md":
            self._save_as_markdown(summary_data, output_path)

        else:
            raise ValueError(f"Unsupported format: {format}")

        click.echo(f"Summary saved: {output_path}")

    def _save_as_markdown(self, summary_data: Dict, output_path: Path) -> None:
        """Save summary as Markdown file.

        Args:
            summary_data: Summary data
            output_path: Output Markdown file path
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Podcast Summary\n\n")

            if "final_summary" in summary_data:
                # Multi-chunk summary format
                f.write("## Overview\n\n")
                f.write(summary_data["final_summary"]["summary"])
                f.write("\n\n")

                f.write("## Segment Summaries\n\n")
                for chunk in summary_data["chunk_summaries"]:
                    start_min = int(chunk["start_time"] // 60)
                    start_sec = int(chunk["start_time"] % 60)
                    end_min = int(chunk["end_time"] // 60)
                    end_sec = int(chunk["end_time"] % 60)

                    f.write(f"### Segment {start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}\n\n")
                    f.write(chunk["summary"])
                    f.write("\n\n")

            else:
                # Single summary format
                f.write(summary_data.get("summary", str(summary_data)))
                f.write("\n\n")

            # Add metadata
            f.write("---\n\n")
            f.write("*Generated using Google Gemini Flash 2.5*\n")
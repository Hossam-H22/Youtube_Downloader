"""Subtitle listing and downloading backed by youtube-transcript-api."""

import logging

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import SRTFormatter

from .interfaces import SubtitleService

logger = logging.getLogger(__name__)


class TranscriptApiSubtitleService(SubtitleService):
    """Lists and downloads subtitles using youtube-transcript-api."""

    def list_available(self, video_id: str) -> list[str]:
        try:
            # Retrieve the list of available transcripts
            transcripts = YouTubeTranscriptApi().list(video_id)
            languages = [transcript.language_code for transcript in transcripts]
            logger.debug("Subtitles available for %s: %s", video_id, languages)
            return languages
        except Exception as e:
            # No transcripts available (private/region-locked video, rate limit, ...)
            logger.debug("No subtitles for %s (%s)", video_id, e)
            return []

    def download(
        self,
        video_id: str,
        title: str,
        output_path: str = '.',
        language_code: str = 'en',
    ) -> str:
        logger.info("Downloading subtitles (%s) for '%s'", language_code, title)
        try:
            transcript_list = YouTubeTranscriptApi().list(video_id)  # Get the transcript for the video
            transcript = transcript_list.find_transcript([language_code])  # Find the transcript in the desired language
            transcript_data = transcript.fetch()  # Fetch the transcript

            # Format the transcript into SRT format
            formatter = SRTFormatter()
            srt_text = formatter.format_transcript(transcript_data)

            # Save the subtitle as SRT file
            filename = f'{output_path}/{title}.srt'
            with open(filename, "w", encoding="utf-8") as file:
                file.write(srt_text)
            logger.info("Subtitle saved: %s", filename)
            print(f"Subtitle saved as {filename}")
            return filename
        except Exception as e:
            logger.warning("Subtitle download failed for '%s' (%s): %s", title, language_code, e)
            print(f"An error occurred: {e} \n")
            return ""

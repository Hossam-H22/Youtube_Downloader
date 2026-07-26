"""Subtitle listing and downloading backed by youtube-transcript-api."""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import SRTFormatter

from .interfaces import SubtitleService


class TranscriptApiSubtitleService(SubtitleService):
    """Lists and downloads subtitles using youtube-transcript-api."""

    def list_available(self, video_id: str) -> list[str]:
        try:
            # Retrieve the list of available transcripts
            transcripts = YouTubeTranscriptApi().list(video_id)
            return [transcript.language_code for transcript in transcripts]
        except Exception:
            # No transcripts available (private/region-locked video, rate limit, ...)
            return []

    def download(
        self,
        video_id: str,
        title: str,
        output_path: str = '.',
        language_code: str = 'en',
    ) -> str:
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
            print(f"Subtitle saved as {filename}")
            return filename
        except Exception as e:
            print(f"An error occurred: {e} \n")
            return ""

"""Video / playlist metadata provider backed by yt-dlp."""

import yt_dlp

from .interfaces import InfoProvider
from .models import Chapter, PlaylistInfo, VideoInfo
from .utils import clean_filename


class YtDlpInfoProvider(InfoProvider):
    """Fetches video and playlist metadata using yt-dlp."""

    def get_video_info(self, url: str) -> VideoInfo:
        ydl_opts = {
            'quiet': True,  # Suppress output
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        raw_chapters = info.get('chapters', []) or []
        chapters = [
            Chapter(
                title=chapter['title'],
                start_time=chapter['start_time'],
                end_time=chapter['end_time'],
            )
            for chapter in raw_chapters
        ]

        return VideoInfo(
            url=url,
            id=info['id'],
            title=clean_filename(info['title']),
            length_seconds=info['duration'],
            description=info['description'],
            thumbnail=info['thumbnail'],
            chapters=chapters,
        )

    def get_playlist_info(self, url: str) -> PlaylistInfo:
        ydl_opts = {
            'quiet': True,        # Suppress output
            'extract_flat': True,  # Only list the playlist entries, don't resolve each video yet
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        entries = info.get('entries', []) or []
        video_urls = [
            f"https://www.youtube.com/watch?v={entry['id']}" for entry in entries
        ]

        videos_info = [self.get_video_info(video_url) for video_url in video_urls]

        return PlaylistInfo(
            url=url,
            id=info['id'],
            title=clean_filename(info.get('title', '')),
            videos_info=videos_info,
        )

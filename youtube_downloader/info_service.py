"""Video / playlist metadata provider backed by yt-dlp."""

import logging

import yt_dlp

from .interfaces import InfoProvider
from .models import Chapter, PlaylistInfo, VideoInfo
from .utils import clean_filename
from .ytdlp_support import js_runtime_opts

logger = logging.getLogger(__name__)


class YtDlpInfoProvider(InfoProvider):
    """Fetches video and playlist metadata using yt-dlp."""

    def get_video_info(self, url: str) -> VideoInfo:
        logger.info("Fetching video info: %s", url)
        ydl_opts = {
            'quiet': True,  # Suppress output
            **js_runtime_opts(),  # opt-in nsig solving (see metadata.json settings)
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

        video = VideoInfo(
            url=url,
            id=info['id'],
            title=clean_filename(info['title']),
            length_seconds=info['duration'],
            description=info['description'],
            thumbnail=info['thumbnail'],
            chapters=chapters,
        )
        logger.info(
            "Fetched video '%s' (%s, %d chapters)",
            video.title, video.length, len(chapters),
        )
        return video

    def get_playlist_info(self, url: str) -> PlaylistInfo:
        logger.info("Fetching playlist info: %s", url)
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
        logger.info("Playlist '%s' has %d videos; resolving each…",
                    info.get('title', ''), len(video_urls))

        videos_info = [self.get_video_info(video_url) for video_url in video_urls]

        playlist = PlaylistInfo(
            url=url,
            id=info['id'],
            title=clean_filename(info.get('title', '')),
            videos_info=videos_info,
        )
        logger.info("Resolved playlist '%s' (%d videos, total %s)",
                    playlist.title, playlist.number_videos, playlist.length)
        return playlist

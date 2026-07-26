"""Video downloader backed by yt-dlp."""

import yt_dlp

from .interfaces import VideoDownloader


class YtDlpDownloader(VideoDownloader):
    """Downloads the best-quality MP4 for a video using yt-dlp."""

    def download(self, url: str, title: str, output_path: str = '.') -> bool:
        ydl_opts = {
            'outtmpl': f'{output_path}/{title}.%(ext)s',
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',  # Download the best quality
            'noplaylist': True,  # Only download single video, not the whole playlist
            'retries': 10,           # Retry the whole download on network errors
            'fragment_retries': 10,  # Retry individual fragments (fixes "Connection reset by peer")
            'socket_timeout': 30,    # Give up on a stalled connection sooner, then retry
            'continuedl': True,      # Resume partially downloaded files instead of restarting
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            print(f"\nFailed to download '{title}': {e}\n")
            return False

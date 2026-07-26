"""Video downloader backed by yt-dlp."""

import logging

import yt_dlp

from .ffmpeg_support import ffmpeg_location
from .interfaces import VideoDownloader
from .models import DownloadOutcome
from .ytdlp_support import js_runtime_opts

logger = logging.getLogger(__name__)


class YtDlpDownloader(VideoDownloader):
    """Downloads the best-quality MP4 for a video using yt-dlp.

    YouTube 403s: the ``android_vr`` client that yt-dlp falls back to (when no
    proof-of-origin token / JS runtime is available) is heavily throttled and its
    AV1-only formats (e.g. 399) intermittently return ``HTTP Error 403``. To stay
    reliable we (1) prefer H.264 ``avc1`` MP4, which the ``tv``/``web_safari``
    clients serve without a PO token, (2) let yt-dlp source formats from several
    clients, and (3) retry with a fresh extraction on failure.
    """

    def download(
        self,
        url: str,
        title: str,
        output_path: str = '.',
        progress_hook=None,
    ) -> DownloadOutcome:
        ydl_opts = {
            'outtmpl': f'{output_path}/{title}.%(ext)s',
            # Prefer H.264 (avc1) MP4 from the reliable clients, then any MP4.
            'format': (
                'bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/'
                'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
            ),
            'merge_output_format': 'mp4',  # always produce a .mp4 (chapter split relies on it)
            'ffmpeg_location': ffmpeg_location(),  # use the bundled ffmpeg for the stream merge
            'noplaylist': True,       # Only download single video, not the whole playlist
            'retries': 10,            # Retry the whole download on network errors
            'fragment_retries': 10,   # Retry individual fragments (fixes "Connection reset by peer")
            'extractor_retries': 5,   # Re-extract (fresh URLs) on transient extractor errors
            'socket_timeout': 30,     # Give up on a stalled connection sooner, then retry
            'continuedl': True,       # Resume partially downloaded files instead of restarting
            # Source formats from several player clients so a throttled / HTTP-403
            # client (e.g. android_vr) can fall back to a working one.
            'extractor_args': {'youtube': {'player_client': ['default', 'tv', 'web_safari']}},
            # Optionally enable a JS runtime + EJS solver (opt-in via metadata.json)
            # to solve the nsig challenge and unlock all formats.
            **js_runtime_opts(),
        }
        if progress_hook is not None:
            ydl_opts['progress_hooks'] = [progress_hook]

        logger.info("Downloading '%s' -> %s", title, output_path)
        last_error = None
        for attempt in range(1, 4):  # up to 3 fresh-extraction attempts for transient 403s
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                logger.info("Downloaded '%s'", title)
                return DownloadOutcome(success=True)
            except Exception as e:
                last_error = e
                logger.warning("Attempt %d/3 failed for '%s': %s", attempt, title, e)
                print(f"\nAttempt {attempt}/3 failed for '{title}': {e}")
        logger.error("Failed to download '%s' after 3 attempts: %s", title, last_error)
        print(f"\nFailed to download '{title}': {last_error}\n")
        return DownloadOutcome(success=False, error=str(last_error))

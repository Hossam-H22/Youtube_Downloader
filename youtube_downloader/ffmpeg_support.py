"""Locate the ffmpeg binary the app should use.

ffmpeg is an external binary the app needs to merge yt-dlp's separate video/audio
streams (:mod:`youtube_downloader.downloader`) and to split a video into
per-chapter files (:mod:`youtube_downloader.chapters`). Rather than require every
user to install it, we depend on the ``imageio-ffmpeg`` package, which ships a
static ffmpeg build and is bundled into the frozen executable. That way the packaged
app has ffmpeg with zero external setup, while a source checkout still falls back to
a system ffmpeg on ``PATH``.
"""

import logging
import shutil
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def ffmpeg_location() -> str:
    """Return a path to an ffmpeg binary, preferring the bundled static build.

    Resolution order: the ``imageio-ffmpeg`` bundled binary, then an ffmpeg found
    on ``PATH``, then the bare name ``"ffmpeg"`` as a last resort. Memoized so the
    lookup (and its log line) happens once per process.

    Accepted by both yt-dlp's ``ffmpeg_location`` option and as the executable in a
    ``subprocess`` command list.
    """
    try:
        import imageio_ffmpeg

        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path:
            logger.info("Using bundled ffmpeg: %s", path)
            return path
    except Exception as e:  # noqa: BLE001 - any failure just means fall back to PATH
        logger.debug("imageio-ffmpeg unavailable (%s); falling back to PATH", e)

    path = shutil.which('ffmpeg')
    if path:
        logger.info("Using ffmpeg from PATH: %s", path)
        return path

    logger.warning("No ffmpeg found (bundled or on PATH); using bare 'ffmpeg'")
    return 'ffmpeg'

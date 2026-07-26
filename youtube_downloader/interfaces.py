"""Abstract interfaces the CLI depends on (dependency inversion).

Each interface is intentionally narrow (interface segregation) so that a
consumer only depends on the operations it actually uses. Concrete
implementations live in the sibling service modules and are wired together in
``main.py``.
"""

from abc import ABC, abstractmethod

from .models import Chapter, DownloadOutcome, PlaylistInfo, VideoInfo


class InfoProvider(ABC):
    """Fetches metadata about videos and playlists."""

    @abstractmethod
    def get_video_info(self, url: str) -> VideoInfo:
        """Return metadata for a single video."""

    @abstractmethod
    def get_playlist_info(self, url: str) -> PlaylistInfo:
        """Return metadata for a playlist and each of its videos."""


class VideoDownloader(ABC):
    """Downloads a video to disk."""

    @abstractmethod
    def download(
        self,
        url: str,
        title: str,
        output_path: str = '.',
        progress_hook=None,
    ) -> DownloadOutcome:
        """Download ``url`` as ``title`` into ``output_path``.

        ``progress_hook`` is an optional callable invoked with progress updates
        (the yt-dlp hook contract). Passing ``None`` disables progress reporting,
        which is the console default. Returns a :class:`DownloadOutcome` (truthy on
        success; ``.error`` holds the failure reason on failure).
        """


class SubtitleService(ABC):
    """Lists and downloads subtitles for a video."""

    @abstractmethod
    def list_available(self, video_id: str) -> list[str]:
        """Return the language codes with available subtitles (may be empty)."""

    @abstractmethod
    def download(
        self,
        video_id: str,
        title: str,
        output_path: str = '.',
        language_code: str = 'en',
    ) -> str:
        """Download subtitles as an ``.srt`` file and return its path (``""`` on failure)."""


class ChapterSplitter(ABC):
    """Splits a downloaded video and its subtitles into per-chapter files."""

    @abstractmethod
    def split_video(
        self, video_path: str, chapters: list[Chapter], output_path: str
    ) -> None:
        """Cut ``video_path`` into one file per chapter under ``output_path``."""

    @abstractmethod
    def split_subtitles(
        self, subtitle_path: str, chapters: list[Chapter], output_path: str
    ) -> None:
        """Cut ``subtitle_path`` into one ``.srt`` per chapter under ``output_path``."""

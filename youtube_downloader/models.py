"""Typed data models describing videos, playlists, and their chapters.

These dataclasses replace the untyped dictionaries the original script passed
around, giving the rest of the package a stable, self-documenting shape.
"""

from dataclasses import dataclass, field

from .utils import format_video_length


@dataclass
class Chapter:
    """A single chapter within a video.

    ``title`` is stored raw (as returned by the source); callers clean it for
    display / file names via :func:`youtube_downloader.utils.clean_filename`.
    """

    title: str
    start_time: float
    end_time: float


@dataclass
class VideoInfo:
    """Everything the app needs to know about a single video."""

    url: str
    id: str
    title: str
    length_seconds: int
    description: str
    thumbnail: str
    chapters: list[Chapter] = field(default_factory=list)
    transcript_list: list[str] = field(default_factory=list)

    @property
    def length(self) -> str:
        """Human-readable duration of the video."""
        return format_video_length(self.length_seconds)


@dataclass
class PlaylistInfo:
    """A playlist and the videos it contains."""

    url: str
    id: str
    title: str
    videos_info: list[VideoInfo] = field(default_factory=list)
    transcript_list: list[str] = field(default_factory=list)

    @property
    def number_videos(self) -> int:
        """Number of videos in the playlist."""
        return len(self.videos_info)

    @property
    def length(self) -> str:
        """Human-readable total duration across every video."""
        total_seconds = sum(video.length_seconds for video in self.videos_info)
        return format_video_length(total_seconds)


# --------------------------------------------------------------------------- #
# Download options / results — the parameters a front-end (console or GUI)
# collects, and the outcome the workflow layer returns.
# --------------------------------------------------------------------------- #
@dataclass
class VideoDownloadOptions:
    """Choices for downloading a single video.

    ``subtitle_language`` is a language code (e.g. ``"en"``) or ``None`` for no
    subtitles. ``split_chapters`` also wraps the video in a title folder and
    writes a ``Link.txt``, matching the console behavior.
    """

    save_path: str
    subtitle_language: "str | None" = None
    split_chapters: bool = False


@dataclass
class PlaylistDownloadOptions:
    """Choices for downloading a playlist.

    ``selected_indices`` restricts the download to specific videos by their
    1-based position in the playlist; ``None`` (the default) downloads all.
    """

    save_path: str
    subtitle_language: "str | None" = None
    numerate: bool = False
    selected_indices: "set[int] | None" = None


@dataclass
class DownloadOutcome:
    """Result of downloading a single video: success plus a failure reason.

    Truthy when successful, so existing ``if downloader.download(...)`` checks keep
    working while callers that want the reason can read ``error``.
    """

    success: bool
    error: str = ""

    def __bool__(self) -> bool:
        return self.success


@dataclass
class VideoDownloadResult:
    """Outcome of a single-video download."""

    output_path: str
    subtitle_file: str = ""
    chapters_split: bool = False


@dataclass
class PlaylistDownloadResult:
    """Outcome of a playlist download, including any per-video failures."""

    output_path: str
    failed_videos: list[str] = field(default_factory=list)

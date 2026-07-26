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

"""Shared download orchestration used by every front-end.

``DownloadWorkflows`` holds the download → subtitle → chapter-split → text-file
sequence that used to live inside ``ConsoleApp``. It performs no user I/O: the
console and the GUI both call it, supplying their own progress/status callbacks.
"""

import logging
import os

from .filesystem import create_text_file, ensure_dir
from .interfaces import ChapterSplitter, SubtitleService, VideoDownloader
from .models import (
    PlaylistDownloadOptions,
    PlaylistDownloadResult,
    PlaylistInfo,
    VideoDownloadOptions,
    VideoDownloadResult,
    VideoInfo,
)
from .utils import format_counter

logger = logging.getLogger(__name__)


class DownloadWorkflows:
    """Orchestrates the actual download work behind any front-end."""

    def __init__(
        self,
        downloader: VideoDownloader,
        subtitle_service: SubtitleService,
        chapter_splitter: ChapterSplitter,
    ) -> None:
        self.downloader = downloader
        self.subtitle_service = subtitle_service
        self.chapter_splitter = chapter_splitter

    def download_video(
        self,
        info: VideoInfo,
        options: VideoDownloadOptions,
        progress_hook=None,
    ) -> VideoDownloadResult:
        """Download one video, optionally with subtitles and chapter splitting.

        When ``options.split_chapters`` is set, the video is wrapped in a folder
        named after its title, a ``Link.txt`` is written, and (if the video has
        chapters) the video and subtitles are split into a ``Chapters`` subfolder.
        """
        logger.info(
            "Video workflow start: '%s' (subs=%s, split_chapters=%s) -> %s",
            info.title, options.subtitle_language, options.split_chapters, options.save_path,
        )
        save_path = options.save_path
        if options.split_chapters:
            save_path = os.path.join(save_path, info.title)
            ensure_dir(save_path)

        self.downloader.download(info.url, info.title, save_path, progress_hook)

        subtitle_file = ""
        if options.subtitle_language:
            subtitle_file = self.subtitle_service.download(
                info.id, info.title, save_path, options.subtitle_language
            )

        chapters_split = False
        if options.split_chapters:
            text_file = [
                "Video Url: \n",
                info.url,
                "\n\n\n\n\n\n\n\n\n\n",
                f"Title: \n{info.title}\n\n",
                "Description: \n",
                info.description,
            ]
            create_text_file(text_file, save_path)
            video_path = os.path.join(save_path, f"{info.title}.mp4")
            if info.chapters:
                chapters_folder_path = os.path.join(save_path, 'Chapters')
                ensure_dir(chapters_folder_path)
                self.chapter_splitter.split_video(video_path, info.chapters, chapters_folder_path)
                if len(subtitle_file) > 0:
                    self.chapter_splitter.split_subtitles(subtitle_file, info.chapters, chapters_folder_path)
                chapters_split = True

        logger.info("Video workflow done: '%s' -> %s (subtitles=%s, chapters_split=%s)",
                    info.title, save_path, bool(subtitle_file), chapters_split)
        return VideoDownloadResult(
            output_path=save_path,
            subtitle_file=subtitle_file,
            chapters_split=chapters_split,
        )

    def download_playlist(
        self,
        info: PlaylistInfo,
        options: PlaylistDownloadOptions,
        on_video=None,
        progress_hook=None,
    ) -> PlaylistDownloadResult:
        """Download every video in a playlist into a folder named after it.

        ``on_video(index, total, title)`` is called before each video starts so a
        front-end can report per-video progress. Failed videos are collected and
        returned; re-running skips already-downloaded files.
        """
        logger.info(
            "Playlist workflow start: '%s' (%d videos, subs=%s, numerate=%s)",
            info.title, info.number_videos, options.subtitle_language, options.numerate,
        )
        save_path = os.path.join(options.save_path, info.title)
        ensure_dir(save_path)

        text_file = ["Playlist Url: \n", info.url, "\n\n\n\n\n\n\n\n\n\n", "Videos Information: \n\n\n\n"]
        failed_videos = []
        for index, video in enumerate(info.videos_info):
            if options.numerate:
                video_title = f"{format_counter(index + 1, info.number_videos)}{video.title}"
            else:
                video_title = video.title

            text_file.append(f"Video #{index+1}\n")
            text_file.append("====================================\n")
            text_file.append(f"Title: {video_title}\n")
            text_file.append(f"Description: {video.description} \n")
            text_file.append("====================================\n\n\n\n\n\n\n")

            if on_video is not None:
                on_video(index + 1, info.number_videos, video_title)

            logger.info("Playlist video %d/%d: %s", index + 1, info.number_videos, video_title)
            if self.downloader.download(video.url, video_title, save_path, progress_hook):
                if options.subtitle_language:
                    self.subtitle_service.download(
                        video.id, video_title, save_path, options.subtitle_language
                    )
            else:
                failed_videos.append(f"#{index+1} - {video_title}")

        create_text_file(text_file, save_path)
        logger.info("Playlist workflow done: '%s' -> %s (%d failed)",
                    info.title, save_path, len(failed_videos))
        return PlaylistDownloadResult(output_path=save_path, failed_videos=failed_videos)

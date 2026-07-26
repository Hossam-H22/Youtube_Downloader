"""Entry point: construct the concrete services and run the console app.

This is the only place concrete implementations are chosen; ``ConsoleApp``
itself depends solely on the abstract interfaces (dependency inversion), so a
service can be swapped here without touching the rest of the package.
"""

from youtube_downloader.chapters import FfmpegChapterSplitter
from youtube_downloader.cli import ConsoleApp
from youtube_downloader.downloader import YtDlpDownloader
from youtube_downloader.info_service import YtDlpInfoProvider
from youtube_downloader.subtitles import TranscriptApiSubtitleService


def build_app() -> ConsoleApp:
    """Wire the concrete services into the console application."""
    return ConsoleApp(
        info_provider=YtDlpInfoProvider(),
        downloader=YtDlpDownloader(),
        subtitle_service=TranscriptApiSubtitleService(),
        chapter_splitter=FfmpegChapterSplitter(),
    )


if __name__ == '__main__':
    build_app().run()

"""Entry point: construct the shared services and launch a front-end.

By default the web GUI is launched (Flask server + browser). Pass
``--console-view`` (or the bare token ``console-view``) to run the interactive
console instead. Concrete services are chosen only here; both front-ends depend
solely on the abstract interfaces (dependency inversion).
"""

import logging
import sys

from youtube_downloader.chapters import FfmpegChapterSplitter
from youtube_downloader.cli import ConsoleApp
from youtube_downloader.downloader import YtDlpDownloader
from youtube_downloader.info_service import YtDlpInfoProvider
from youtube_downloader.logging_config import setup_logging
from youtube_downloader.metadata import get_metadata
from youtube_downloader.settings import get_settings
from youtube_downloader.subtitles import TranscriptApiSubtitleService
from youtube_downloader.workflows import DownloadWorkflows

CONSOLE_FLAGS = {"--console-view", "console-view"}


def _log_level() -> int:
    """Resolve the log level from the app settings (default INFO)."""
    name = get_settings().get('log_level', 'INFO')
    return getattr(logging, str(name).upper(), logging.INFO)


def build_services():
    """Construct the concrete services and the shared workflow layer."""
    info_provider = YtDlpInfoProvider()
    subtitle_service = TranscriptApiSubtitleService()
    workflows = DownloadWorkflows(
        downloader=YtDlpDownloader(),
        subtitle_service=subtitle_service,
        chapter_splitter=FfmpegChapterSplitter(),
    )
    return info_provider, subtitle_service, workflows


def build_console_app() -> ConsoleApp:
    """Wire the shared services into the interactive console app."""
    info_provider, subtitle_service, workflows = build_services()
    return ConsoleApp(info_provider, subtitle_service, workflows)


def main(argv: "list[str] | None" = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    console_mode = bool(CONSOLE_FLAGS & set(args))
    # Console app keeps logs out of the interactive menu (file only); GUI logs to
    # both its terminal and the file.
    setup_logging(to_console=not console_mode, level=_log_level())
    logger = logging.getLogger('youtube_downloader.main')
    logger.info("Starting %s in %s mode", get_metadata().get('name', 'app'),
                'console' if console_mode else 'GUI')

    if console_mode:
        build_console_app().run()
    else:
        # Imported lazily so the console mode doesn't require Flask installed.
        from youtube_downloader.gui.server import run_gui

        run_gui(*build_services())


if __name__ == '__main__':
    main()

"""Entry point: construct the shared services and launch a front-end.

By default the web GUI is launched (Flask server + browser). Pass
``--console-view`` (or the bare token ``console-view``) to run the interactive
console instead. Concrete services are chosen only here; both front-ends depend
solely on the abstract interfaces (dependency inversion).
"""

import sys

from youtube_downloader.chapters import FfmpegChapterSplitter
from youtube_downloader.cli import ConsoleApp
from youtube_downloader.downloader import YtDlpDownloader
from youtube_downloader.info_service import YtDlpInfoProvider
from youtube_downloader.subtitles import TranscriptApiSubtitleService
from youtube_downloader.workflows import DownloadWorkflows

CONSOLE_FLAGS = {"--console-view", "console-view"}


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
    if CONSOLE_FLAGS & set(args):
        build_console_app().run()
    else:
        # Imported lazily so the console mode doesn't require Flask installed.
        from youtube_downloader.gui.server import run_gui

        run_gui(*build_services())


if __name__ == '__main__':
    main()

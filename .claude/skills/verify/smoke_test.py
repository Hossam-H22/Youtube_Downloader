"""Network-free smoke test for the YouTube Downloader.

Injects fake services (implementing the four ABCs in ``interfaces.py``) into
``ConsoleApp``, drives the video flow with monkeypatched ``input``, and asserts
the display output plus the pure helpers and model properties. No downloads,
no YouTube, no ffmpeg.

Run from the repo root:  PYTHONPATH="$(pwd)" python .claude/skills/verify/smoke_test.py
"""

import builtins
import contextlib
import io
import os
import sys

# Make the repo root importable no matter where this script is launched from.
# This file lives at <repo>/.claude/skills/verify/smoke_test.py, so the repo
# root is three directories up.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from youtube_downloader.cli import ConsoleApp
from youtube_downloader.interfaces import (
    ChapterSplitter,
    InfoProvider,
    SubtitleService,
    VideoDownloader,
)
from youtube_downloader.models import Chapter, PlaylistInfo, VideoInfo
from youtube_downloader.utils import (
    clean_filename,
    format_counter,
    format_video_length,
)


def test_helpers():
    assert format_video_length(3661) == "1 hours and 1 minutes and 1 seconds"
    assert format_video_length(59) == "59 seconds"
    assert format_video_length(600) == "10 minutes"
    assert format_counter(2, 100) == "002. "
    assert format_counter(7, 9) == "7. "
    assert clean_filename('a<b>c:d/e"f') == 'abcdef'


def test_models():
    v = VideoInfo(
        url="u", id="i", title="t", length_seconds=3661, description="d",
        thumbnail="th", chapters=[Chapter("Intro", 0, 90), Chapter("Body", 90, 3661)],
    )
    assert v.length == "1 hours and 1 minutes and 1 seconds"
    p = PlaylistInfo(
        url="pu", id="pi", title="pt",
        videos_info=[v, VideoInfo("u2", "i2", "t2", 100, "", "")],
    )
    assert p.number_videos == 2
    assert p.length == format_video_length(3761)
    return v, p


class _FakeInfo(InfoProvider):
    def __init__(self, video, playlist):
        self._v, self._p = video, playlist

    def get_video_info(self, url):
        return self._v

    def get_playlist_info(self, url):
        return self._p


class _FakeDownloader(VideoDownloader):
    def download(self, url, title, output_path='.'):
        return True


class _FakeSubs(SubtitleService):
    def list_available(self, video_id):
        return ["en", "ar"]

    def download(self, *a, **k):
        return ""


class _FakeSplitter(ChapterSplitter):
    def split_video(self, *a):
        pass

    def split_subtitles(self, *a):
        pass


def test_video_display(video, playlist):
    app = ConsoleApp(_FakeInfo(video, playlist), _FakeDownloader(), _FakeSubs(), _FakeSplitter())

    inputs = iter(["N"])  # answer "N" to the download prompt -> only info is shown
    original_input = builtins.input
    builtins.input = lambda *a: next(inputs)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            app.video_processes("someurl")
    finally:
        builtins.input = original_input

    out = buf.getvalue()
    assert "Video Information:" in out
    assert "Title: t" in out
    assert "Duration: 1 hours and 1 minutes and 1 seconds" in out
    assert "Video have subtitles: ['en', 'ar']" in out
    assert "Video Chapters:" in out
    assert "1. Intro  =>  1 minutes and 30 seconds" in out
    assert "2. Body  =>  59 minutes and 31 seconds" in out


if __name__ == '__main__':
    test_helpers()
    video, playlist = test_models()
    test_video_display(video, playlist)
    print("ALL ASSERTIONS PASSED")

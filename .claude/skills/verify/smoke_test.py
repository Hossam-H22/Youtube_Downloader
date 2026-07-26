"""Network-free smoke test for the YouTube Downloader.

Injects fake services (implementing the ABCs in ``interfaces.py``) into the
console app and the shared workflow layer, and checks the Flask app offline via
its test client. Asserts display output, helpers, model properties, workflow
orchestration, and the web wiring. No downloads, no YouTube, no ffmpeg.

Run from anywhere:  python .claude/skills/verify/smoke_test.py
"""

import builtins
import contextlib
import io
import os
import sys
import tempfile

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
from youtube_downloader.models import (
    Chapter,
    PlaylistDownloadOptions,
    PlaylistInfo,
    VideoDownloadOptions,
    VideoInfo,
)
from youtube_downloader.utils import (
    clean_filename,
    format_counter,
    format_video_length,
)
from youtube_downloader.workflows import DownloadWorkflows


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
    def __init__(self, fail_titles=()):
        self.calls = []
        self.fail_titles = set(fail_titles)

    def download(self, url, title, output_path='.', progress_hook=None):
        self.calls.append(title)
        return title not in self.fail_titles


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


def _workflows(downloader=None):
    return DownloadWorkflows(downloader or _FakeDownloader(), _FakeSubs(), _FakeSplitter())


def test_video_display(video, playlist):
    app = ConsoleApp(_FakeInfo(video, playlist), _FakeSubs(), _workflows())

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


def test_workflow_video(video):
    dl = _FakeDownloader()
    result = _workflows(dl).download_video(
        video, VideoDownloadOptions(save_path="/nowhere", subtitle_language=None, split_chapters=False)
    )
    assert dl.calls == [video.title]
    assert result.output_path == "/nowhere"
    assert result.subtitle_file == ""


def test_workflow_playlist(playlist):
    with tempfile.TemporaryDirectory() as tmp:
        dl = _FakeDownloader(fail_titles={"t2"})  # second video "fails"
        events = []
        result = _workflows(dl).download_playlist(
            playlist,
            PlaylistDownloadOptions(save_path=tmp, subtitle_language=None, numerate=False),
            on_video=lambda i, total, title: events.append((i, total, title)),
        )
        assert len(events) == 2               # on_video fired for both videos
        assert dl.calls == ["t", "t2"]
        assert result.failed_videos == ["#2 - t2"]


def test_flask_offline(video, playlist):
    try:
        from youtube_downloader.gui.server import create_app
    except Exception as e:  # flask not installed -> skip rather than fail hard
        print(f"(skipping Flask check: {e})")
        return
    app = create_app(_FakeInfo(video, playlist), _FakeSubs(), _workflows())
    client = app.test_client()
    assert client.get("/").status_code == 200
    meta = client.get("/api/metadata")
    assert meta.status_code == 200
    data = meta.get_json()
    assert "name" in data and "version" in data

    # /api/playlist-info returns per-video details for the whole playlist
    pl = client.post("/api/playlist-info", json={"url": "x"})
    assert pl.status_code == 200
    body = pl.get_json()
    assert body["number_videos"] == 2
    assert len(body["videos"]) == 2
    assert body["videos"][0]["index"] == 1
    assert "title" in body["videos"][0] and "length" in body["videos"][0]


if __name__ == '__main__':
    test_helpers()
    video, playlist = test_models()
    test_video_display(video, playlist)
    test_workflow_video(video)
    test_workflow_playlist(playlist)
    test_flask_offline(video, playlist)
    print("ALL ASSERTIONS PASSED")

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
    DownloadOutcome,
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
        if title in self.fail_titles:
            return DownloadOutcome(success=False, error=f"failed: {title}")
        return DownloadOutcome(success=True)


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
    options = VideoDownloadOptions(save_path="/nowhere", subtitle_language=None, split_chapters=False)
    result = _workflows(dl).download_video(video, options)
    assert dl.calls == [video.title]
    assert result.output_path == "/nowhere"
    assert result.subtitle_file == ""
    assert result.success and result.error == ""

    # A failed download is reported, not silently treated as success — and the
    # subtitle step is skipped, since there is no file to put subtitles beside.
    subs = _FakeSubs()
    failing = _FakeDownloader(fail_titles={video.title})
    result = DownloadWorkflows(
        downloader=failing, subtitle_service=subs, chapter_splitter=_FakeSplitter(),
    ).download_video(
        video,
        VideoDownloadOptions(save_path="/nowhere", subtitle_language="en", split_chapters=False),
    )
    assert result.success is False
    assert "failed" in result.error
    assert result.subtitle_file == ""


def test_workflow_playlist(playlist):
    with tempfile.TemporaryDirectory() as tmp:
        dl = _FakeDownloader(fail_titles={"t2"})  # second video "fails"
        events = []
        results = []
        result = _workflows(dl).download_playlist(
            playlist,
            PlaylistDownloadOptions(save_path=tmp, subtitle_language=None, numerate=False),
            on_video=lambda i, total, title: events.append((i, total, title)),
            on_video_result=lambda i, total, video, title, path, outcome: results.append(
                (title, bool(outcome), getattr(outcome, 'error', ''))
            ),
        )
        assert len(events) == 2               # on_video fired for both videos
        assert dl.calls == ["t", "t2"]
        # failure reason is captured and included in the failed list
        assert result.failed_videos == ["#2 - t2: failed: t2"]
        # per-video results: first ok (no error), second failed with reason
        assert len(results) == 2
        assert results[0] == ("t", True, "")
        assert results[1][0] == "t2" and results[1][1] is False and "t2" in results[1][2]


def test_js_runtime_opts():
    import youtube_downloader.ytdlp_support as ys

    orig_settings = ys.get_settings
    orig_which = ys.shutil.which
    try:
        # Setting off -> no change to yt-dlp options
        ys.get_settings = lambda: {'use_js_runtime': False}
        assert ys.js_runtime_opts() == {}

        # Setting on + a runtime on PATH -> enable runtime + remote solver
        ys.get_settings = lambda: {'use_js_runtime': True}
        ys.shutil.which = lambda name: '/usr/bin/deno' if name == 'deno' else None
        opts = ys.js_runtime_opts()
        assert opts.get('js_runtimes') == {'deno': {}}
        assert opts.get('remote_components') == ['ejs:github']

        # Setting on but no runtime installed -> no change (still works via H.264)
        ys.shutil.which = lambda name: None
        assert ys.js_runtime_opts() == {}
    finally:
        ys.get_settings = orig_settings
        ys.shutil.which = orig_which


def test_cookie_opts():
    import youtube_downloader.ytdlp_support as ys

    orig = ys.get_settings
    try:
        # Nothing configured -> no cookie options at all
        ys.get_settings = lambda: {}
        assert ys.cookie_opts() == {}

        # A supported browser -> yt-dlp's (browser,) tuple
        ys.get_settings = lambda: {'cookies_from_browser': 'chrome'}
        assert ys.cookie_opts() == {'cookiesfrombrowser': ('chrome',)}

        # Case/whitespace tolerant
        ys.get_settings = lambda: {'cookies_from_browser': '  Firefox '}
        assert ys.cookie_opts() == {'cookiesfrombrowser': ('firefox',)}

        # An unknown browser is ignored rather than crashing the download
        ys.get_settings = lambda: {'cookies_from_browser': 'netscape'}
        assert ys.cookie_opts() == {}

        # A cookies file is used only when it actually exists
        ys.get_settings = lambda: {'cookies_file': '/definitely/not/here.txt'}
        assert ys.cookie_opts() == {}
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            ys.get_settings = lambda: {'cookies_file': f.name}
            assert ys.cookie_opts() == {'cookiefile': f.name}

            # Both sources can be active at once
            ys.get_settings = lambda: {'cookies_from_browser': 'safari', 'cookies_file': f.name}
            assert ys.cookie_opts() == {
                'cookiesfrombrowser': ('safari',), 'cookiefile': f.name,
            }

        # base_ydl_opts always carries the shared player-client list
        ys.get_settings = lambda: {}
        assert ys.base_ydl_opts()['extractor_args'] == {
            'youtube': {'player_client': ['default', 'tv', 'web_safari']}
        }
    finally:
        ys.get_settings = orig


def test_auth_error_classification():
    from youtube_downloader.ytdlp_support import friendly_error, is_auth_error

    blocked = Exception(
        "ERROR: [youtube] saKNFPAybaY: Sign in to confirm you\u2019re not a bot. "
        "Use --cookies-from-browser or --cookies for the authentication."
    )
    assert is_auth_error(blocked)
    message = friendly_error(blocked)
    assert message and "not a bot" in message and "Settings" in message

    # Unrelated failures are left exactly as they were
    transient = Exception("HTTP Error 500: Internal Server Error")
    assert not is_auth_error(transient)
    assert friendly_error(transient) is None


def test_settings_layering():
    import youtube_downloader.settings as st

    with tempfile.TemporaryDirectory() as tmp:
        orig_writable = st.writable_dir
        orig_meta = st.get_metadata
        try:
            st.writable_dir = lambda: tmp
            st.get_metadata = lambda: {'settings': {'log_level': 'INFO', 'use_js_runtime': True}}

            # With no user file, the bundled defaults win
            assert st.get_settings()['use_js_runtime'] is True
            assert st.get_settings()['cookies_from_browser'] == ''

            # A saved override shadows the bundled default and round-trips
            merged = st.update_settings({'cookies_from_browser': 'chrome'})
            assert merged['cookies_from_browser'] == 'chrome'
            assert merged['log_level'] == 'INFO'      # untouched keys survive
            assert st.get_settings()['cookies_from_browser'] == 'chrome'

            # A second write merges rather than replacing
            st.update_settings({'use_js_runtime': False})
            assert st.get_settings()['cookies_from_browser'] == 'chrome'
            assert st.get_settings()['use_js_runtime'] is False

            # A corrupt settings file must not stop the app starting
            with open(st.settings_path(), 'w', encoding='utf-8') as f:
                f.write("{not json")
            assert st.get_settings()['use_js_runtime'] is True   # falls back to defaults
        finally:
            st.writable_dir = orig_writable
            st.get_metadata = orig_meta


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

    # /api/retry-video starts a background retry job and returns its id
    retry = client.post("/api/retry-video", json={
        "url": "u", "id": "i", "title": "t", "save_path": "/tmp",
    })
    assert retry.status_code == 200
    assert "job_id" in retry.get_json()

    # /api/settings exposes the current values, the file backing them, and the
    # browser choices the Settings panel offers.
    got = client.get("/api/settings")
    assert got.status_code == 200
    body = got.get_json()
    assert "settings" in body and "settings_path" in body
    assert "chrome" in body["browsers"]

    # A POST with no recognized key is rejected rather than writing an empty file
    assert client.post("/api/settings", json={"nope": 1}).status_code == 400


if __name__ == '__main__':
    test_helpers()
    video, playlist = test_models()
    test_video_display(video, playlist)
    test_workflow_video(video)
    test_workflow_playlist(playlist)
    test_js_runtime_opts()
    test_cookie_opts()
    test_auth_error_classification()
    test_settings_layering()
    test_flask_offline(video, playlist)
    print("ALL ASSERTIONS PASSED")

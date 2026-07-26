"""Flask server exposing the download workflows to the browser UI."""

import dataclasses
import logging
import os
import socket
import threading
import webbrowser

from flask import Flask, Response, jsonify, request, send_from_directory

from ..filesystem import open_folder, pick_folder
from ..interfaces import InfoProvider, SubtitleService
from ..metadata import get_metadata
from ..models import PlaylistDownloadOptions, VideoDownloadOptions
from ..workflows import DownloadWorkflows
from . import jobs

logger = logging.getLogger(__name__)

WEB_DIR = os.path.join(os.path.dirname(__file__), 'web')
DEFAULT_SAVE_PATH = os.path.join(os.path.expanduser('~'), 'Downloads')


def _progress_hook(job: "jobs.Job"):
    """Translate yt-dlp progress dicts into UI progress events."""
    def hook(d: dict) -> None:
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            percent = (downloaded / total * 100) if total else 0
            job.emit(
                type='progress',
                percent=round(percent, 1),
                speed=d.get('speed'),
                eta=d.get('eta'),
            )
        elif status == 'finished':
            job.emit(type='progress', percent=100, stage='processing')
    return hook


def create_app(
    info_provider: InfoProvider,
    subtitle_service: SubtitleService,
    workflows: DownloadWorkflows,
) -> Flask:
    """Build the Flask app wired to the injected services."""
    app = Flask(__name__, static_folder=None)

    # ------------------------------------------------------------------ #
    # Static UI
    # ------------------------------------------------------------------ #
    def _no_cache(response):
        # Local dev app: always serve the current asset so an edit is never
        # masked by a cached copy in the browser.
        response.headers['Cache-Control'] = 'no-cache'
        return response

    @app.get('/')
    def index():
        return _no_cache(send_from_directory(WEB_DIR, 'index.html'))

    @app.get('/static/<path:filename>')
    def static_files(filename: str):
        return _no_cache(send_from_directory(WEB_DIR, filename))

    @app.get('/api/metadata')
    def api_metadata():
        meta = dict(get_metadata())
        meta['default_save_path'] = DEFAULT_SAVE_PATH
        return jsonify(meta)

    # ------------------------------------------------------------------ #
    # Info fetching
    # ------------------------------------------------------------------ #
    @app.post('/api/video-info')
    def api_video_info():
        url = (request.get_json(silent=True) or {}).get('url', '').strip()
        logger.info("GUI request: video-info %s", url or '(empty)')
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        try:
            info = info_provider.get_video_info(url)
            info.transcript_list = subtitle_service.list_available(info.id)
            return jsonify({**dataclasses.asdict(info), 'length': info.length})
        except Exception as e:  # noqa: BLE001
            return jsonify({'error': str(e)}), 500

    @app.post('/api/playlist-info')
    def api_playlist_info():
        url = (request.get_json(silent=True) or {}).get('url', '').strip()
        logger.info("GUI request: playlist-info %s", url or '(empty)')
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        try:
            info = info_provider.get_playlist_info(url)
            transcript_list = []
            for video in info.videos_info:
                langs = subtitle_service.list_available(video.id)
                if langs:
                    transcript_list = langs
                    break
            info.transcript_list = transcript_list
            return jsonify({
                'title': info.title,
                'number_videos': info.number_videos,
                'length': info.length,
                'transcript_list': info.transcript_list,
                'videos': [
                    {
                        'index': i + 1,
                        'title': v.title,
                        'length': v.length,
                        'thumbnail': v.thumbnail,
                        'chapters': len(v.chapters),
                    }
                    for i, v in enumerate(info.videos_info)
                ],
            })
        except Exception as e:  # noqa: BLE001
            return jsonify({'error': str(e)}), 500

    # ------------------------------------------------------------------ #
    # Downloads (background jobs + SSE progress)
    # ------------------------------------------------------------------ #
    @app.post('/api/download-video')
    def api_download_video():
        data = request.get_json(silent=True) or {}
        url = data.get('url', '').strip()
        options = VideoDownloadOptions(
            save_path=data.get('save_path') or DEFAULT_SAVE_PATH,
            subtitle_language=data.get('subtitle_language') or None,
            split_chapters=bool(data.get('split_chapters')),
        )
        job = jobs.create_job()
        logger.info("GUI request: download-video %s (job %s)", url or '(empty)', job.id)

        def runner(job: "jobs.Job") -> None:
            info = info_provider.get_video_info(url)
            job.emit(type='status', message=f'Downloading: {info.title}')
            result = workflows.download_video(info, options, progress_hook=_progress_hook(job))
            job.emit(
                type='done',
                output_path=result.output_path,
                subtitle_file=result.subtitle_file,
                chapters_split=result.chapters_split,
                failed_videos=[],
            )

        jobs.run_in_thread(job, runner)
        return jsonify({'job_id': job.id})

    @app.post('/api/download-playlist')
    def api_download_playlist():
        data = request.get_json(silent=True) or {}
        url = data.get('url', '').strip()
        options = PlaylistDownloadOptions(
            save_path=data.get('save_path') or DEFAULT_SAVE_PATH,
            subtitle_language=data.get('subtitle_language') or None,
            numerate=bool(data.get('numerate')),
        )
        job = jobs.create_job()
        logger.info("GUI request: download-playlist %s (job %s)", url or '(empty)', job.id)

        def runner(job: "jobs.Job") -> None:
            info = info_provider.get_playlist_info(url)

            def on_video(index: int, total: int, title: str) -> None:
                job.emit(type='video', index=index, total=total, title=title)

            result = workflows.download_playlist(
                info, options, on_video=on_video, progress_hook=_progress_hook(job)
            )
            job.emit(type='done', output_path=result.output_path, failed_videos=result.failed_videos)

        jobs.run_in_thread(job, runner)
        return jsonify({'job_id': job.id})

    @app.get('/api/progress/<job_id>')
    def api_progress(job_id: str):
        job = jobs.get_job(job_id)
        if job is None:
            return jsonify({'error': 'Unknown job'}), 404
        return Response(
            jobs.sse_stream(job),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
        )

    # ------------------------------------------------------------------ #
    # Folder helpers
    # ------------------------------------------------------------------ #
    @app.post('/api/pick-folder')
    def api_pick_folder():
        return jsonify({'path': pick_folder()})

    @app.post('/api/open-folder')
    def api_open_folder():
        path = (request.get_json(silent=True) or {}).get('path', '')
        if path:
            open_folder(path)
        return jsonify({'ok': True})

    return app


def _free_port() -> int:
    """Find a free localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def run_gui(
    info_provider: InfoProvider,
    subtitle_service: SubtitleService,
    workflows: DownloadWorkflows,
) -> None:
    """Start the web server and open the app in the default browser."""
    app = create_app(info_provider, subtitle_service, workflows)
    port = _free_port()
    url = f'http://127.0.0.1:{port}/'
    logger.info("Starting GUI server at %s", url)
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Youtube Downloader GUI running at {url}  (press Ctrl+C to stop)")
    app.run(host='127.0.0.1', port=port, threaded=True)

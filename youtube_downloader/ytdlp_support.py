"""Shared yt-dlp option helpers.

Keeps yt-dlp configuration that is shared between the info provider and the
downloader in one place.
"""

import logging
import shutil

from .metadata import get_metadata

logger = logging.getLogger(__name__)

# Runtimes yt-dlp can use to solve YouTube's signature ("nsig") challenge,
# in order of preference (deno is yt-dlp's default/recommended runtime).
_JS_RUNTIMES = ('deno', 'node', 'bun')


def js_runtime_opts() -> dict:
    """yt-dlp options that let it solve YouTube's nsig challenge — when enabled.

    Opt-in via ``"settings": {"use_js_runtime": true}`` in ``metadata.json``.
    When enabled *and* a JavaScript runtime is on ``PATH``, this enables that
    runtime plus the remote EJS solver component (downloaded from the yt-dlp
    GitHub), which unlocks all formats and silences the "No supported JavaScript
    runtime" warning. Returns ``{}`` (no change) when the setting is off or no
    runtime is installed — downloads still work via H.264 formats that don't
    need nsig.
    """
    settings = get_metadata().get('settings', {}) or {}
    if not settings.get('use_js_runtime'):
        return {}
    for runtime in _JS_RUNTIMES:
        if shutil.which(runtime):
            logger.info("JS runtime enabled for nsig solving: %s", runtime)
            return {
                'js_runtimes': {runtime: {}},
                'remote_components': ['ejs:github'],
            }
    logger.warning("use_js_runtime is on but no JS runtime (deno/node/bun) found on PATH")
    return {}

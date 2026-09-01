"""Shared yt-dlp option helpers.

Keeps yt-dlp configuration that is shared between the info provider and the
downloader in one place, so the two never drift apart. Everything the extractor
and the downloader both need comes from :func:`base_ydl_opts`.

Also classifies yt-dlp failures: YouTube's "Sign in to confirm you're not a bot"
block is not a transient network error, so it must not be retried and must be
reported with the fix (configure cookies) rather than as a raw yt-dlp dump.
"""

import logging
import os
import shutil

from .settings import SUPPORTED_COOKIE_BROWSERS, get_settings, settings_path

logger = logging.getLogger(__name__)

# Runtimes yt-dlp can use to solve YouTube's signature ("nsig") challenge,
# in order of preference (deno is yt-dlp's default/recommended runtime).
_JS_RUNTIMES = ('deno', 'node', 'bun')

# Player clients to source formats from. A throttled or HTTP-403 client (e.g. the
# android_vr fallback) can then fall back to a working one.
_PLAYER_CLIENTS = ['default', 'tv', 'web_safari']

# Substrings that identify YouTube refusing to serve us without authentication.
# Matched case-insensitively against the exception text.
_AUTH_ERROR_MARKERS = (
    "sign in to confirm",
    "confirm you're not a bot",
    "confirm you are not a bot",
    "sign in to view",
    "use --cookies",
    "--cookies-from-browser",
    "this video is only available to music premium members",
    "account cookies are no longer valid",
)


def js_runtime_opts() -> dict:
    """yt-dlp options that let it solve YouTube's nsig challenge — when enabled.

    Opt-in via the ``use_js_runtime`` setting. When enabled *and* a JavaScript
    runtime is on ``PATH``, this enables that runtime plus the remote EJS solver
    component (downloaded from the yt-dlp GitHub), which unlocks all formats and
    silences the "No supported JavaScript runtime" warning. Returns ``{}`` (no
    change) when the setting is off or no runtime is installed — downloads still
    work via H.264 formats that don't need nsig.
    """
    if not get_settings().get('use_js_runtime'):
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


def cookie_opts() -> dict:
    """yt-dlp options that send YouTube cookies from a signed-in session.

    This is the fix for "Sign in to confirm you're not a bot": YouTube serves that
    block to clients it doesn't trust, and a logged-in cookie jar clears it. Two
    sources, both optional and both usable together:

    * ``cookies_from_browser`` — a browser name from
      :data:`~youtube_downloader.settings.SUPPORTED_COOKIE_BROWSERS`;
      yt-dlp reads that browser's cookie store directly.
    * ``cookies_file`` — the path to a Netscape-format ``cookies.txt`` export. The
      fallback for when reading the browser store is blocked (on macOS, Safari
      needs Full Disk Access and Chrome prompts for Keychain access).

    An unknown browser name or a missing file logs a warning and is skipped, so a
    bad setting degrades to anonymous access instead of crashing the download.
    """
    settings = get_settings()
    opts: dict = {}

    browser = str(settings.get('cookies_from_browser') or '').strip().lower()
    if browser:
        if browser in SUPPORTED_COOKIE_BROWSERS:
            # yt-dlp expects (browser, profile, keyring, container); the rest are optional.
            opts['cookiesfrombrowser'] = (browser,)
            logger.info("Using cookies from browser: %s", browser)
        else:
            logger.warning(
                "Unknown cookies_from_browser %r; expected one of %s. Ignoring it.",
                browser, ", ".join(SUPPORTED_COOKIE_BROWSERS),
            )

    cookies_file = str(settings.get('cookies_file') or '').strip()
    if cookies_file:
        expanded = os.path.expanduser(cookies_file)
        if os.path.isfile(expanded):
            opts['cookiefile'] = expanded
            logger.info("Using cookies file: %s", expanded)
        else:
            logger.warning("cookies_file %r does not exist; ignoring it", cookies_file)

    return opts


def base_ydl_opts() -> dict:
    """The yt-dlp options every extraction and download should share.

    Sourcing formats from several player clients, the opt-in nsig solver, and any
    configured cookies all matter equally to metadata extraction and to the download
    itself, so both call sites spread this rather than each keeping their own copy.
    """
    return {
        'extractor_args': {'youtube': {'player_client': list(_PLAYER_CLIENTS)}},
        **js_runtime_opts(),
        **cookie_opts(),
    }


def is_auth_error(error: BaseException) -> bool:
    """True when YouTube refused the request for lack of authentication.

    Such a failure is not transient: retrying the same anonymous request just
    repeats the block, so callers should stop early rather than burn their retries.
    """
    text = str(error).lower()
    return any(marker in text for marker in _AUTH_ERROR_MARKERS)


def friendly_error(error: BaseException) -> "str | None":
    """An actionable message for a recognized failure, else ``None``.

    Returning ``None`` for anything unrecognized keeps every existing error message
    exactly as it was; only the bot-check gets rewritten, because the raw yt-dlp
    text points at command-line flags this app doesn't expose.
    """
    if is_auth_error(error):
        return (
            "YouTube asked us to sign in to confirm you're not a bot. "
            "Set your browser in Settings (or point 'cookies_file' at a cookies.txt export) "
            f"so the app can use your signed-in session. Settings file: {settings_path()}"
        )
    return None

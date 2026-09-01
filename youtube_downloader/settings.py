"""User-editable application settings, layered over the bundled defaults.

Defaults ship in ``metadata.json``'s ``settings`` block; user overrides live in a
separate ``settings.json`` that the app writes at runtime.

The split exists because ``metadata.json`` is a *bundled, read-only* resource:
:func:`youtube_downloader.paths.resource_path` resolves it inside PyInstaller's
``sys._MEIPASS`` temp dir, which is wiped when the frozen app exits. Anything the
user can change therefore has to live under :func:`~youtube_downloader.paths.writable_dir`
(next to the executable when frozen, the repo root in a source checkout) — the
same place ``logs/`` goes.

Reads are best-effort: a missing or malformed ``settings.json`` logs a warning and
falls back to the bundled defaults, so a bad config never stops the app starting.
"""

import json
import logging
import os

from .metadata import get_metadata
from .paths import writable_dir

logger = logging.getLogger(__name__)

_SETTINGS_FILE = 'settings.json'

# Browsers the ``cookies_from_browser`` setting accepts — yt-dlp's
# --cookies-from-browser list. Lives here (not with the yt-dlp helpers) so the
# front-ends can offer the choices without importing anything yt-dlp specific.
SUPPORTED_COOKIE_BROWSERS = (
    'brave', 'chrome', 'chromium', 'edge', 'firefox', 'opera', 'safari', 'vivaldi', 'whale',
)

# Fallbacks for keys that may be absent from metadata.json (its `settings` block
# is optional, and metadata.py's own fallback dict has no `settings` key at all).
_DEFAULTS = {
    'use_js_runtime': False,
    'log_level': 'INFO',
    'check_for_updates': True,
    # Cookie sources for yt-dlp — see ytdlp_support.cookie_opts(). Empty = off.
    'cookies_from_browser': '',
    'cookies_file': '',
}


def settings_path() -> str:
    """Absolute path of the user settings file (may not exist yet)."""
    return os.path.join(writable_dir(), _SETTINGS_FILE)


def _user_overrides() -> dict:
    """Settings the user has saved; ``{}`` when the file is absent or unreadable."""
    path = settings_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        logger.warning("Could not read %s (%s); using bundled defaults", path, e)
        return {}
    if not isinstance(data, dict):
        logger.warning("%s does not contain a JSON object; ignoring it", path)
        return {}
    return data


def get_settings() -> dict:
    """Return the effective settings: bundled defaults updated with user overrides."""
    settings = dict(_DEFAULTS)
    settings.update(get_metadata().get('settings', {}) or {})
    settings.update(_user_overrides())
    return settings


def update_settings(changes: dict) -> dict:
    """Merge ``changes`` into the user settings file and return the effective settings.

    Written atomically (temp file + :func:`os.replace`) so an interrupted write can
    never leave a half-written file behind. Raises ``OSError`` if the file cannot be
    written — callers decide how to report that.
    """
    overrides = _user_overrides()
    overrides.update(changes)

    path = settings_path()
    tmp_path = f"{path}.tmp"
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(overrides, f, indent=4)
        f.write("\n")
    os.replace(tmp_path, path)
    logger.info("Saved settings to %s (%s)", path, ", ".join(sorted(changes)) or "no changes")
    return get_settings()

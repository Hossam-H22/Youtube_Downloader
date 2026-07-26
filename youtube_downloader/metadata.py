"""Single source of truth for project metadata.

All project info (name, version, description, author, repository, ...) lives in
``metadata.json`` at the repo root; this module reads it so nothing else has to
hardcode any of it.
"""

import json
import os

_METADATA_FILE = os.path.join(os.path.dirname(__file__), os.pardir, "metadata.json")

_FALLBACK = {
    "name": "Youtube Downloader",
    "version": "0.0.0",
    "description": "",
    "author": {"name": "", "email": ""},
    "repository": "",
}


def get_metadata() -> dict:
    """Return the full project metadata dict from ``metadata.json``.

    Falls back to a minimal dict if the file is missing or malformed, so a
    metadata problem never crashes the app.
    """
    try:
        with open(_METADATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return dict(_FALLBACK)


def get_version() -> str:
    """Convenience accessor for just the version string."""
    return get_metadata().get("version", _FALLBACK["version"])

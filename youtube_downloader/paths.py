"""Frozen-aware path resolution for bundled resources and writable files.

The app can run two ways: from source (``python main.py``) or as a single-file
executable frozen by PyInstaller. When frozen, PyInstaller unpacks bundled data
into a temporary directory pointed to by ``sys._MEIPASS`` and sets ``sys.frozen``.
That temp dir is read-only-ish and wiped on exit, so it is fine for **reading**
bundled resources but wrong for **writing** runtime files (e.g. logs).

This module centralizes the two path questions so every other module stays
agnostic:

* :func:`resource_path` — where a *bundled, read-only* resource lives.
* :func:`writable_dir` — where *runtime-written* files (logs) should go.

In source runs both resolve to today's locations (the repo root / package tree),
so nothing about the dev workflow changes.
"""

import os
import sys


def is_frozen() -> bool:
    """True when running from a PyInstaller-built executable."""
    return getattr(sys, 'frozen', False)


def _repo_root() -> str:
    """Repo root in a source checkout (the parent of this package directory)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts: str) -> str:
    """Absolute path to a bundled read-only resource.

    ``parts`` are joined relative to the bundle root. When frozen this is
    ``sys._MEIPASS``; in a source checkout it is the repo root. The PyInstaller
    spec bundles resources under the same relative layout, so callers pass the
    same repo-relative path in both cases, e.g.
    ``resource_path('youtube_downloader', 'gui', 'web')``.
    """
    base = getattr(sys, '_MEIPASS', None) if is_frozen() else _repo_root()
    return os.path.join(base or _repo_root(), *parts)


def writable_dir() -> str:
    """Directory for runtime-written files (e.g. the ``logs/`` folder).

    Next to the executable when frozen (a portable app writes beside itself);
    the repo root in a source checkout (so ``logs/`` stays where it is today).
    """
    if is_frozen():
        return os.path.dirname(sys.executable)
    return _repo_root()

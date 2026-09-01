"""Check GitHub for a newer released version of the app.

On startup each front-end asks :func:`check_for_update` whether the
``metadata.json`` published on the project's GitHub repository advertises a
version newer than the one we are running. The check is best-effort: any network,
HTTP, or parsing problem is logged and swallowed so it never blocks or crashes
the app. Presentation (a console message vs. a GUI dialog) is left to the caller;
this module only decides *whether* an update exists.
"""

import json
import logging
import ssl
import urllib.request

from .metadata import get_metadata
from .settings import get_settings
from .models import UpdateInfo

logger = logging.getLogger(__name__)

# Keep the startup check snappy — a slow/unreachable network must not stall launch.
_TIMEOUT_SECONDS = 5
# metadata.json may live on either default-branch name; try both.
_BRANCHES = ("master", "main")
# A UA keeps GitHub happy; anonymous requests without one can be treated oddly.
_USER_AGENT = "Youtube-Downloader-UpdateChecker"


def _ssl_context() -> "ssl.SSLContext | None":
    """SSL context using certifi's CA bundle when available.

    On many macOS Python installs the system CA store is not wired into OpenSSL,
    so the default context raises ``CERTIFICATE_VERIFY_FAILED`` against GitHub.
    certifi (already present via yt-dlp) ships a trusted bundle we can point at;
    if it is missing we fall back to the default context.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception as e:  # noqa: BLE001
        logger.debug("Falling back to default SSL context (%s)", e)
        return None


def _parse_version(version: str) -> "tuple[int, ...]":
    """Turn a dotted version string into a comparable tuple of ints.

    Non-numeric characters within a component are dropped (so ``"2.0.0-beta"``
    reads as ``(2, 0, 0)``); missing/garbage components read as ``0``.
    """
    parts = []
    for piece in str(version).split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _is_newer(latest: str, current: str) -> bool:
    """True when ``latest`` is a strictly greater version than ``current``."""
    a, b = _parse_version(latest), _parse_version(current)
    length = max(len(a), len(b))
    a += (0,) * (length - len(a))
    b += (0,) * (length - len(b))
    return a > b


def _raw_metadata_urls(repository: str) -> "list[str]":
    """Raw-content URLs for ``metadata.json`` on the repo's candidate branches."""
    repo = (repository or "").rstrip("/")
    if "github.com" not in repo:
        return []
    base = repo.replace("github.com", "raw.githubusercontent.com")
    return [f"{base}/{branch}/metadata.json" for branch in _BRANCHES]


def _fetch_remote_metadata(repository: str) -> "dict | None":
    """Fetch and parse the remote ``metadata.json``; ``None`` if unreachable.

    Tries each candidate branch in turn and returns the first that parses. A
    per-URL 404 (e.g. the repo uses ``master`` not ``main``) is expected and just
    falls through to the next candidate.
    """
    context = _ssl_context()
    for url in _raw_metadata_urls(repository):
        try:
            logger.debug("Checking for updates at %s", url)
            request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 — best-effort; any failure just skips
            logger.debug("Update check failed for %s (%s)", url, e)
    return None


def check_for_update() -> "UpdateInfo | None":
    """Return :class:`UpdateInfo` if GitHub has a newer version, else ``None``.

    Honors the ``check_for_updates`` setting (default ``True``). Never raises —
    network/parse failures resolve to ``None``.
    """
    meta = get_metadata()
    if not get_settings().get("check_for_updates", True):
        logger.debug("Update check disabled via settings")
        return None

    current = meta.get("version", "0.0.0")
    remote = _fetch_remote_metadata(meta.get("repository", ""))
    if not remote:
        logger.info("Update check: could not reach GitHub; skipping")
        return None

    latest = remote.get("version", "0.0.0")
    if _is_newer(latest, current):
        repo = (meta.get("repository", "") or "").rstrip("/")
        download_url = f"{repo}/releases/latest" if repo else ""
        logger.info("Update available: v%s -> v%s", current, latest)
        return UpdateInfo(
            current_version=current,
            latest_version=latest,
            download_url=download_url,
        )

    logger.info("Update check: running the latest version (v%s)", current)
    return None

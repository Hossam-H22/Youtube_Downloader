"""Central logging configuration.

Call :func:`setup_logging` once at startup (done in ``main.py``). Every module
logs via ``logging.getLogger(__name__)``; those loggers propagate to the package
logger configured here, which always writes to a rotating file and optionally to
the console. This gives an always-on, step-by-step record of what the app does.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

PACKAGE_LOGGER = 'youtube_downloader'
_LOG_DIR = os.path.join(os.path.dirname(__file__), os.pardir, 'logs')
LOG_FILE = os.path.join(_LOG_DIR, 'youtube_downloader.log')
_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

_configured = False


def setup_logging(to_console: bool = True, level: int = logging.INFO) -> str:
    """Configure logging for the whole package. Idempotent; returns the log path.

    A rotating file handler is always installed (``logs/youtube_downloader.log``).
    The console (stderr) handler is optional — enabled for the GUI (its terminal
    shows live activity) and disabled for the console app (so log lines don't
    clutter the interactive menu; tail the log file to monitor it).
    """
    global _configured
    logger = logging.getLogger(PACKAGE_LOGGER)
    if _configured:
        return LOG_FILE

    logger.setLevel(level)
    logger.propagate = False
    formatter = logging.Formatter(_FORMAT)

    os.makedirs(_LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    _configured = True
    logger.info(
        "Logging initialized (level=%s, console=%s, file=%s)",
        logging.getLevelName(level), to_console, LOG_FILE,
    )
    return LOG_FILE


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the package namespace."""
    return logging.getLogger(name)

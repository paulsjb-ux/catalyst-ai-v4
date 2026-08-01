from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import threading

_LOGGER_NAME = "catalyst_ai"
_LOG_DIR = Path("storage/logs")
_LOG_FILE = _LOG_DIR / "catalyst.log"
_CONFIG_LOCK = threading.Lock()
_CONFIGURED = False


def _resolve_level(default: int = logging.INFO) -> int:
    raw = str(os.getenv("CATALYST_LOG_LEVEL", "")).strip().upper()
    return getattr(logging, raw, default) if raw else default


def configure_logging(level: int | None = None) -> logging.Logger:
    """Configure console and rotating file logging once across Streamlit reruns."""
    global _CONFIGURED
    logger = logging.getLogger(_LOGGER_NAME)
    with _CONFIG_LOCK:
        if _CONFIGURED:
            return logger
        resolved_level = _resolve_level(level or logging.INFO)
        logger.setLevel(resolved_level)
        logger.propagate = False
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        console = logging.StreamHandler()
        console.setLevel(resolved_level)
        console.setFormatter(formatter)
        logger.addHandler(console)
        try:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            rotating = RotatingFileHandler(_LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
            rotating.setLevel(resolved_level)
            rotating.setFormatter(formatter)
            logger.addHandler(rotating)
        except OSError:
            logger.warning("File logging unavailable; continuing with console logging only.")
        _CONFIGURED = True
    return logger


def get_log_path() -> Path:
    return _LOG_FILE

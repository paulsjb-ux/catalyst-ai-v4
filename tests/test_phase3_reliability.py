from __future__ import annotations

import ast
import logging
from pathlib import Path

from data.diagnostics import diagnostic_bundle, recent_log_lines
from logging_config import configure_logging
from version import APP_VERSION


def test_phase3_version():
    assert APP_VERSION == "8.6.0"


def test_logging_is_idempotent():
    logger = configure_logging()
    handlers = list(logger.handlers)
    assert configure_logging() is logger
    assert logger.handlers == handlers
    assert logger.name == "catalyst_ai"
    assert logger.level in {logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL}


def test_app_has_error_boundary():
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    route = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "route_page")
    assert any(isinstance(n, ast.Try) for n in ast.walk(route))
    assert "logger.exception" in source


def test_diagnostics_safe_without_log(monkeypatch, tmp_path):
    monkeypatch.setattr("data.diagnostics.get_log_path", lambda: tmp_path / "missing.log")
    assert recent_log_lines() == []
    assert b"No Catalyst log entries" in diagnostic_bundle()

from __future__ import annotations

from logging_config import get_log_path


def recent_log_lines(limit: int = 200) -> list[str]:
    path = get_log_path()
    if not path.exists() or limit <= 0:
        return []
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return []


def diagnostic_bundle() -> bytes:
    lines = recent_log_lines(500)
    text = "\n".join(lines) + "\n" if lines else "No Catalyst log entries are currently available.\n"
    return text.encode("utf-8")

from __future__ import annotations

from typing import Any

from data.storage_service import get, put

PAPER_STATE_KEY = "paper_trading:30_day_trial"


def load_paper_state() -> dict[str, Any] | None:
    state = get(PAPER_STATE_KEY, None)
    return state if isinstance(state, dict) else None


def save_paper_state(state: dict[str, Any]) -> str:
    return put(PAPER_STATE_KEY, state)


def clear_paper_state() -> str:
    return put(PAPER_STATE_KEY, None)

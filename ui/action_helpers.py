from __future__ import annotations

import logging
from typing import Any, Callable
import uuid

import streamlit as st

logger = logging.getLogger("catalyst_ai")


def run_ui_action(action_name: str, action: Callable[[], Any], success_message: str) -> Any | None:
    try:
        result = action()
    except Exception:
        reference = uuid.uuid4().hex[:8]
        logger.exception("Action failed [%s] %s", reference, action_name)
        st.error(f"{action_name} could not be completed. Reference: {reference}. Check Settings → Diagnostics.")
        return None
    st.success(success_message)
    return result

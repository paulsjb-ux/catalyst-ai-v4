from pathlib import Path


def test_mobile_navigation_uses_callback_and_shared_state():
    source = Path("ui/components.py").read_text(encoding="utf-8")
    assert "def _apply_mobile_route()" in source
    assert 'st.session_state["primary_navigation"] = requested' in source
    assert "on_change=_apply_mobile_route" in source
    assert "def _apply_sidebar_route(page: str)" in source
    assert 'st.session_state["mobile_page_navigation"] = page' in source


def test_v1433_version():
    ns = {}
    exec(Path("version.py").read_text(encoding="utf-8"), ns)
    assert ns["APP_VERSION"] == "14.5.1"

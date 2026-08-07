from pathlib import Path


def test_mobile_navigation_uses_returned_selection_and_explicit_rerun():
    source = Path("ui/components.py").read_text(encoding="utf-8")
    assert "requested = st.selectbox(" in source
    assert 'st.session_state["primary_navigation"] = requested' in source
    assert "st.rerun()" in source
    assert "on_change=_apply_mobile_route" not in source


def test_v1433_version():
    ns = {}
    exec(Path("version.py").read_text(encoding="utf-8"), ns)
    assert ns["APP_VERSION"] == "14.3.3"

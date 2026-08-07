from pathlib import Path


def test_sidebar_and_mobile_navigation_are_synchronised():
    source = Path("ui/components.py").read_text(encoding="utf-8")
    assert 'st.session_state["primary_navigation"] = page' in source
    assert 'st.session_state["mobile_page_navigation"] = page' in source
    assert 'on_click=_apply_sidebar_route' in source
    assert 'on_change=_apply_mobile_route' in source
    # Regression: stale selectbox value must not run after widget render and undo sidebar clicks.
    assert 'if requested in ALL_NAVIGATION and requested != selected:' not in source

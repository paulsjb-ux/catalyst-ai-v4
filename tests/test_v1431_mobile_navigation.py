from pathlib import Path


def test_mobile_navigation_selector_is_present():
    source = Path("ui/components.py").read_text(encoding="utf-8")
    assert "def _mobile_navigation" in source
    assert "mobile_page_navigation" in source
    assert "ALL_NAVIGATION" in source
    assert "_mobile_navigation(selected)" in source


def test_mobile_css_provides_sticky_fallback_and_keeps_desktop_hidden():
    source = Path("ui/theme.py").read_text(encoding="utf-8")
    assert ".st-key-mobile_navigation_container{display:none!important;}" in source
    assert "position:sticky!important" in source
    assert "@media(max-width:900px)" in source
    assert "[data-testid=\"stSidebar\"]" in source


def test_patch_version():
    namespace = {}
    exec(Path("version.py").read_text(encoding="utf-8"), namespace)
    assert namespace["APP_VERSION"] == "14.3.3"

from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def test_navigation_css_wraps_and_hides_horizontal_overflow():
    source = (PROJECT / "ui" / "components.py").read_text(
        encoding="utf-8"
    )
    assert "flex-wrap: wrap" in source
    assert "overflow-x: hidden" in source
    assert "max-width: 100%" in source


def test_top_navigation_applies_overflow_fix():
    source = (PROJECT / "ui" / "components.py").read_text(
        encoding="utf-8"
    )
    start = source.index("def top_navigation()")
    block = source[start : start + 400]
    assert "navigation_overflow_fix()" in block

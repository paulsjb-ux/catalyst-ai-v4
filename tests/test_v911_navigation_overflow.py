from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def test_navigation_blocks_horizontal_canvas_overflow():
    source = (PROJECT / "ui" / "components.py").read_text(
        encoding="utf-8"
    )
    assert "overflow-x: clip" in source
    assert "overflow: hidden" in source


def test_top_navigation_applies_overflow_fix():
    source = (PROJECT / "ui" / "components.py").read_text(
        encoding="utf-8"
    )
    block = source[
        source.index("def top_navigation()")
        : source.index("def metric_card(")
    ]
    assert "navigation_overflow_fix()" in block

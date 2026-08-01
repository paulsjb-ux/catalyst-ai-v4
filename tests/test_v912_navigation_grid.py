from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def test_navigation_no_longer_uses_horizontal_radio():
    source = (PROJECT / "ui" / "components.py").read_text(encoding="utf-8")
    assert "st.radio(" not in source
    assert "st.button(" in source


def test_navigation_is_workflow_first():
    source = (PROJECT / "ui" / "components.py").read_text(encoding="utf-8")
    assert "PRIMARY_NAVIGATION" in source
    assert "TOOL_NAVIGATION" in source
    assert "More tools" in source


def test_columns_constrain_button_width():
    source = (PROJECT / "ui" / "components.py").read_text(encoding="utf-8")
    assert 'div[data-testid="column"]' in source
    assert "min-width:0" in source
    assert "max-width:100%" in source

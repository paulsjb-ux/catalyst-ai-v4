from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def test_navigation_no_longer_uses_horizontal_radio():
    source = (PROJECT / "ui" / "components.py").read_text(
        encoding="utf-8"
    )
    block = source[
        source.index("def top_navigation()")
        : source.index("def metric_card(")
    ]
    assert "st.radio(" not in block
    assert "st.button(" in block
    assert "st.columns(" in block


def test_navigation_is_split_into_fixed_rows():
    source = (PROJECT / "ui" / "components.py").read_text(
        encoding="utf-8"
    )
    assert "buttons_per_row = 5" in source
    assert "use_container_width=True" in source


def test_columns_constrain_button_width():
    source = (PROJECT / "ui" / "components.py").read_text(
        encoding="utf-8"
    )
    assert 'div[data-testid="column"]' in source
    assert "min-width: 0" in source
    assert "overflow-wrap: anywhere" in source

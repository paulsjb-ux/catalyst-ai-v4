from pathlib import Path


def test_v13_version_and_compact_workspace_css():
    assert '14.5' in Path('version.py').read_text(encoding='utf-8')
    theme = Path('ui/theme.py').read_text(encoding='utf-8')
    assert 'header[data-testid="stHeader"]{display:none' in theme
    assert 'width:218px' in theme
    assert 'grid-template-columns:repeat(4' in theme


def test_v13_verdict_precedes_metric_cards():
    source = Path('ui/daily_routine.py').read_text(encoding='utf-8')
    assert source.index('daily-verdict') < source.index('c1.markdown(metric_card')

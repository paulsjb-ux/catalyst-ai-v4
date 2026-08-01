from pathlib import Path

def test_v111_version():
    assert '14.3' in Path('version.py').read_text()

def test_ultra_compact_overrides():
    text = Path('ui/theme.py').read_text()
    assert 'ultra-compact workspace' in text
    assert 'height:30px' in text
    assert 'min-height:38px' in text

def test_daily_desk_version_label():
    assert 'Daily Routine <span>· v{APP_VERSION}</span>' in Path('ui/daily_routine.py').read_text()

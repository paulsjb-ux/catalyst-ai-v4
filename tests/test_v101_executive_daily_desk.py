from pathlib import Path


def test_v101_version_and_daily_desk_markers():
    assert '14.1' in Path('version.py').read_text()
    daily = Path('ui/daily_routine.py').read_text()
    assert 'desk-status-strip' in daily
    assert 'RUN DAILY ROUTINE' in daily
    assert 'TODAY’S VERDICT' in daily
    assert 'Advanced routine settings' in daily


def test_daily_routine_owns_compact_header():
    app = Path('app.py').read_text()
    assert 'if page != "Daily Routine"' in app

from pathlib import Path


def test_v11_version():
    assert '14.0' in Path('version.py').read_text()


def test_workflow_first_navigation():
    text = Path('ui/components.py').read_text()
    assert 'PRIMARY_NAVIGATION' in text
    assert '"Daily Routine"' in text
    assert '"More tools"' in text
    assert 'TOOL_NAVIGATION' in text


def test_compact_workspace_header():
    text = Path('ui/components.py').read_text()
    assert 'workspace-header' in text
    assert 'compact-hero' not in text


def test_daily_desk_version_label():
    assert 'Daily Routine <span>· v{APP_VERSION}</span>' in Path('ui/daily_routine.py').read_text()

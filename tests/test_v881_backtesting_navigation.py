from pathlib import Path
import ast


PROJECT = Path(__file__).resolve().parents[1]


def _assigned_literal(path: Path, variable: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable:
                    return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == variable:
                return ast.literal_eval(node.value)
    raise AssertionError(f"{variable} not found in {path}")


def test_backtesting_is_visible_in_primary_navigation():
    navigation = _assigned_literal(
        PROJECT / "ui" / "components.py",
        "PRIMARY_NAVIGATION",
    )
    assert "Backtesting" in navigation


def test_backtesting_route_exists():
    routes = _assigned_literal(PROJECT / "app.py", "ROUTES")
    assert routes["Backtesting"] == (
        "ui.backtesting",
        "render_backtesting",
    )


def test_backtesting_renderer_file_exists():
    source = (PROJECT / "ui" / "backtesting.py").read_text(
        encoding="utf-8"
    )
    assert "def render_backtesting()" in source

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import argparse

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
EXCLUDED_NAMES = {".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
RUNTIME_PREFIXES = (
    Path("storage/logs"),
    Path("storage/market_cache"),
    Path("storage/scans"),
    Path("storage/exports"),
    Path("storage/daily_routine"),
)


def include(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith("._"):
        return False
    return not any(rel == prefix or prefix in rel.parents for prefix in RUNTIME_PREFIXES)


def build_release(root: Path, output: Path) -> Path:
    root = root.resolve()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.resolve() != output and include(path, root):
                archive.write(path, Path(root.name) / path.relative_to(root))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a clean Catalyst AI release ZIP.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build_release(args.root, args.output))


if __name__ == "__main__":
    main()

from pathlib import Path
import importlib.util

REQUIRED_PATHS = [
    "app.py",
    "config.py",
    "logging_config.py",
    "version.py",
    "requirements.txt",
    "ui/components.py",
    "ui/theme.py",
    "ui/dashboard.py",
    "ui/market_scan.py",
    "data/market_data.py",
    "data/history_store.py",
    "data/universe.py",
    "engine/scanner.py",
    "engine/scoring.py",
    "engine/indicators.py",
    "engine/repeat_winners.py",
]

REQUIRED_PACKAGES = ["streamlit", "pandas", "numpy", "yfinance"]

def check_project_files(base_path: Path | str = ".") -> dict[str, bool]:
    base = Path(base_path)
    return {path: (base / path).exists() for path in REQUIRED_PATHS}

def check_required_packages() -> dict[str, bool]:
    return {package: importlib.util.find_spec(package) is not None for package in REQUIRED_PACKAGES}

def health_summary(base_path: Path | str = ".") -> dict:
    file_checks = check_project_files(base_path)
    package_checks = check_required_packages()
    return {
        "files_ok": all(file_checks.values()),
        "packages_ok": all(package_checks.values()),
        "missing_files": [key for key, ok in file_checks.items() if not ok],
        "missing_packages": [key for key, ok in package_checks.items() if not ok],
    }

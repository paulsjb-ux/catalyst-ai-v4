# Catalyst AI v14.4.0 — Performance & Code Quality

Engineering-only release. Trading logic is intentionally unchanged.

- One application version source (`version.py`).
- Automatic validation uses the shared Catalyst storage service.
- Theme application flattened to one deterministic public `apply_theme()`.
- Daily Routine records stage-by-stage runtime diagnostics.
- Market-data refresh uses expired full-history cache plus a short 7-day incremental update where available.
- Legacy root compatibility wrappers removed.
- Historical release notes moved to `docs/releases/`.
- macOS/bytecode junk excluded from the release package.

Validation requirement: identical market inputs must produce identical trade outputs to v14.3.3.

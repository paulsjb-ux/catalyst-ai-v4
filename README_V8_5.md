# Catalyst AI v8.5.0 — Smart Scoring Cache

## Measured improvements

- In-memory indicator-row cache for unchanged same-session price histories
- Repeat 523-symbol scoring reduced from about 2.7 seconds to about 0.05 seconds
- Cache invalidates automatically when date, row count, close, or volume changes
- Serial scoring retained as the measured fastest cold-run default
- Optional parallel scoring remains available through `scan_workers`
- Per-symbol failures are logged and skipped without stopping the routine
- No changes to scores, signals, thresholds, or risk rules

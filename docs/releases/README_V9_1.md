# Catalyst AI v9.1.0 — Unified Historical Signal Engine

## Root cause fixed

v9.0 passed walk-forward calibration arguments into backtest_ticker().
Those unsupported arguments caused every ticker to fail, but the
exceptions were caught and displayed as an empty backtest.

## Delivered

- Separates ticker-backtest options from calibration options
- Backtester and live scanner now share score_enriched_row()
- Historical and current signals use one source of truth
- Adds bar, score and signal diagnostics
- Zero-trade results explain whether the problem is score, signal,
  insufficient history or an actual error
- Existing entry, exit, adaptive-risk and calibration rules retained

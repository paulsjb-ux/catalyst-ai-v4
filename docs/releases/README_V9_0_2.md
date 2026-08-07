# Catalyst AI v9.0.2 — Backtest Run Reliability

- Shows the real reason when historical data cannot be loaded
- Adds visible requested/loaded/failure/cache-fallback metrics
- Does not replace a completed result until a new run fully succeeds
- Falls back to older complete cached history during provider outages
- Adds staged progress text and a completion confirmation
- Preserves backtest rules and performance calculations

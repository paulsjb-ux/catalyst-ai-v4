# Catalyst AI v8.4.3 — Multi-column Market Data Fix

- Flattens residual yfinance MultiIndex columns
- Removes duplicate OHLCV fields deterministically
- Guarantees Close resolves to one numeric Series
- Adds a defensive duplicate-column guard to indicator calculation
- Prevents: Cannot set a DataFrame with multiple columns to sma_20

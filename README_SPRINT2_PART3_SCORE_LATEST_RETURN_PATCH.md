# Catalyst AI v4 — Sprint 2 Part 3 score_latest Return Patch

Fixes the old scoring test that expects:

```python
score, signal, trend, reason = score_latest(row)
```

## Fix

`score_latest()` now returns the original four-value tuple while still using the smarter Sprint 2 Part 3 scoring engine internally.

It also supports both new and legacy column names:

- close / Close
- sma_20 / SMA20
- sma_50 / SMA50
- sma_200 / SMA200
- rsi_14 / RSI14
- volume_ratio / VolumeRatio
- change_20d_pct / Change20D

## Replaces

- engine/scoring.py
- version.py

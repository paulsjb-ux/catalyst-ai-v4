# Catalyst AI v9.2.1 — Proof & Performance

This release freezes the v9.2 trading logic and adds a repeatable proof layer.

## Added

- One-click Proof Validation in the Validation Centre.
- Locked configuration and trade-set hashes for reproducibility.
- Performance breakdown by year, ticker, score band and market regime.
- Profit factor, expectancy, compounded return and maximum drawdown checks.
- Execution stress test with extra costs and delayed-entry penalty.
- PASS / CONDITIONAL PASS / FAIL verdict using explicit thresholds.
- Downloadable versioned JSON proof report.
- Command-line report generator: `python scripts/run_proof_validation.py trades.csv`.

## Important

A PASS is evidence that the supplied historical trade set meets the configured checks. It is not a guarantee of future returns. Paper-trading validation remains required before live capital is increased.

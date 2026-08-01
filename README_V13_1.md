# Catalyst AI v13.1 — Validation Centre

v13.1 adds a versioned validation workflow without changing the v13 trading logic.

## Workflow
1. Run a historical backtest, or upload a completed-trades CSV in Validation.
2. Open **Analytics → Validation**.
3. Press **Generate v13.1 Validation Report**.
4. Review proof checks, baseline comparison, year/score/ticker/regime diagnostics and stress results.
5. Download PDF, JSON and CSV outputs.

Generated reports are archived in `storage/validation/history/` with configuration and trade hashes for reproducibility.

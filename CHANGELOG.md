# v14.3.1

- Added reliable sticky mobile navigation for iPhone and narrow screens.
- Preserved desktop sidebar navigation.
- Improved mobile button, spacing and table behaviour.
- No trading or validation logic changes.

# v14.0
- Added walk-forward adaptive confidence, dynamic evidence sizing, and holding-period diagnostics.
- UI frozen from v13.1.

# Changelog

## 8.0.1 — Supabase API-key compatibility

- Fixed HTTP 401 errors when using modern `sb_publishable_` Supabase keys.
- Modern Supabase API keys are now sent only in the `apikey` header.
- Legacy JWT-style anon/service-role keys continue to use Bearer authentication.
- Added regression tests for both key formats.

## 8.0.0 — Today’s Decision

- Added a simplified default landing page with TRADE, WATCH or NO TRADE.
- Added conservative decision rules and plain-English explanations.
- Added leading-opportunity summary and one-click navigation.
- Added decision-engine regression tests.
- Updated release metadata to 8.0.0.

## 7.0.2 — Alert Simplification

- Removed Pushover configuration, delivery code, UI controls, secrets and tests.
- Retained SMTP email and generic webhook alerts.
- Updated release version to 7.0.2.

## 4.3.2-sprint2-part3-score-latest-return

- Added smarter scoring compatibility patch
- Restored legacy `score_latest(row)` four-value return format
- Preserved Sprint 2 Part 3 scoring model
- Tests passing: 19

## 4.3.0-sprint2-part3

- Added smarter scoring engine
- Added trend strength scoring
- Added momentum quality scoring
- Added volume confirmation
- Added relative strength proxy
- Added volatility penalty
- Added overextension penalty
- Added scoring breakdown table

## 4.2.2-sprint2-part2-validation-compat

- Added validation compatibility patch
- Supported saved scans with and without `saved_at`
- Tests passing: 14

## 4.2.0-sprint2-part2

- Added targets and stops
- Added ATR-based trade plans
- Added risk/reward calculations
- Added position quality

## 4.1.1-sprint2-part1-validation-fix

- Fixed validation date anchoring
- Added pending-window logic

## 4.1.0-sprint2-part1

- Added forward validation engine
- Added 1D / 5D / 10D / 20D validation
- Added validation summary and exports

## 4.0.0-sprint1-part5

- Completed Sprint 1 production foundation

## 7.0.1 — Stability & Speed
- Added batched market-data downloads, cache and failed-symbol retries.
- Added Supabase retry/backoff and explicit degraded fallback status.
- Added export retention and cleaner release packaging.
- Aligned version metadata and fixed RSI pandas warning.

## 9.2
- Added regime-specific, exponentially weighted confidence overlay.
- Added automatic PROVEN expiry and confidence direction tracking.
- Added REDUCED position cap and v9.2 portfolio return columns.
- Added score-band calibration diagnostics.
- Rebuilt home header/navigation into a compact professional layout.

## v9.2.1 — Proof & Performance
- Added reproducible proof validation, stress testing, diagnostic breakdowns and downloadable reports.

## 12.0
- Replaced top navigation grid with a compact left-rail workstation.
- Fixed navigation overlap with Streamlit's fixed top header.
- Grouped specialist pages into Trading tools, Analytics and System.
- Preserved the one-button swing desk and all trading logic.

## v14.1 — Research Diagnostics
- Added adaptive restriction diagnostics.
- Added separate cost, delay and combined stress scenarios.
- Added confidence-component outcome attribution.
- Added confidence-band calibration against observed win rates.
- Added all diagnostics to Validation Centre and PDF/JSON exports.
- Trading rules and v14 returns remain unchanged.

## v14.2 — Quant Research Lab
- Added named, reproducible A/B experiments on identical completed-trade evidence.
- Added locked research benchmark and explicit promotion gates.
- Added research presets, experiment archive, and JSON/CSV comparison exports.
- Production trading logic remains unchanged from v14.1.

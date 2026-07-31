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

# Sprint 3 Part 3 — Automated Alerts & Scheduled Delivery

Catalyst now evaluates stored scan changes, portfolio-monitor snapshots and market regime data, records important events, and optionally delivers them by email or webhook.

## Alert policy

- `CRITICAL`: breached stop
- `HIGH`: near stop, BUY downgraded to AVOID/SELL, defensive market regime
- `MEDIUM`: BUY upgrade, BUY lost to WATCH, near target
- `INFO`: test/system information

Quiet mode prevents empty daily notifications. Duplicate protection prevents the same event being delivered repeatedly within the configured window.

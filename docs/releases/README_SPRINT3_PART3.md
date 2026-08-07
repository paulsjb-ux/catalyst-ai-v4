# Catalyst AI — Sprint 3 Part 3

## Automated Alerts & Scheduled Delivery

Adds:

- configurable alert rules
- quiet mode
- BUY upgrade alerts
- BUY signal-loss alerts
- near-target and near-stop alerts
- defensive market-regime alerts
- persistent Supabase alert history
- delivery history and duplicate protection
- SMTP email delivery
- webhook delivery
- test notification controls
- scheduler-ready Python command
- weekday GitHub Actions workflow template

## Required secrets

Email delivery:

```toml
SMTP_HOST = "smtp.example.com"
SMTP_PORT = "587"
SMTP_USERNAME = "your-user"
SMTP_PASSWORD = "your-password"
SMTP_FROM = "alerts@example.com"
SMTP_USE_TLS = "true"
```

Optional webhook:

```toml
ALERT_WEBHOOK_URL = "https://..."
```

The existing `SUPABASE_URL` and `SUPABASE_KEY` are also required for scheduled runs to access persistent Catalyst data.

## Manual scheduled-run test

```bash
python3 scripts/run_daily_alerts.py
```

## Important limitation

Streamlit Community Cloud is not a guaranteed background scheduler. The included GitHub Actions workflow is the reliable scheduled trigger. Add the same secrets to the GitHub repository's Actions secrets before enabling it.

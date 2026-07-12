# Catalyst AI — Sprint 3 Part 4

## Alert Delivery Setup & Live Scheduler

This release completes the operational alert loop:

- persistent scheduler health
- last successful run status
- delivery failure status and error details
- automatic retries with backoff
- scheduler trigger labels
- GitHub Actions weekday workflow
- manual workflow launch support
- UI setup checklist
- expanded secret template
- automated tests

## Schedule

The included workflow runs at **08:00 UTC, Monday to Friday**. GitHub Actions cron uses UTC.

## Required GitHub repository secrets

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_USE_TLS`

`ALERT_WEBHOOK_URL` is optional.

Never commit real credentials.

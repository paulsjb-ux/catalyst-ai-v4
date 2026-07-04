# Catalyst AI v4 — Sprint 2 Part 2 Anchor Patch

Fixes a validation test failure caused by anchoring to the exact timestamp instead of the daily market bar date.

## Problem

Saved scans can be timestamped midday, for example:

```text
2026-01-03T12:00:00+00:00
```

Daily market data bars are usually timestamped at midnight:

```text
2026-01-03 00:00:00
```

The previous logic skipped the same-day bar and marked the 1D window as pending.

## Fix

Validation now anchors by calendar date for daily bars.

## Replaces

- engine/validation.py
- version.py

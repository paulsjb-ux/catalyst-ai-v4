# Sprint 2 Part 1 — Validation Accuracy Fix

## Problem

The initial validation logic could calculate forward returns from the start of the downloaded price window instead of from the saved scan date.

## Fix

The validation engine now anchors each ticker to:

1. saved_at timestamp from the saved scan
2. first available market close at or after that timestamp
3. future close after the requested validation window

Incomplete future windows are PENDING.

## Status

Ready for local testing.

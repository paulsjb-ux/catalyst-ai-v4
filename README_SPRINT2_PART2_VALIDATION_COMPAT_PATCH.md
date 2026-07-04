# Catalyst AI v4 — Sprint 2 Part 2 Validation Compatibility Patch

Fixes the remaining legacy validation test failure.

## Problem

Older tests and older scan rows may not include `saved_at`.

The previous anchor patch treated missing `saved_at` as "use latest close", which made old forward-return tests show PENDING.

## Fix

- If `saved_at` exists: anchor to saved scan date.
- If `saved_at` is missing: anchor to the first available price bar for backwards compatibility.

## Replaces

- engine/validation.py
- version.py

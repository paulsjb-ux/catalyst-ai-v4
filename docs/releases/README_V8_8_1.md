# Catalyst AI v8.8.1 — Backtesting Navigation Fix

Backtesting existed in the route table and the page module, but the
separate hard-coded top-navigation list omitted it.

Fixes:
- Adds Backtesting after Paper Trading in the visible navigation
- Extracts visible pages into PRIMARY_NAVIGATION
- Adds regression checks for navigation, route, and renderer alignment

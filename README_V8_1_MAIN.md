# Catalyst AI v8.1.0 — Main Branch Reliability Release

This release consolidates development onto `main` and repairs persistent storage.

## Changes
- Fixed cloud storage function shadowing/recursion in `data/storage_service.py`.
- Added modern Supabase publishable-key support via the `apikey` header.
- Preserved compatibility with legacy JWT-shaped keys.
- Added atomic, JSON-safe local fallback writes.
- Added short-lived cloud read caching and batched backup writes.
- Removed Finder-numbered duplicate files, Python caches, and macOS metadata.
- Aligned all application version sources to 8.1.0.

# Catalyst AI v8.2.0 — Phase 2 Performance and Cleanup

- Lazy-loads page modules so the selected page starts faster.
- Retries failed market symbols concurrently with a bounded worker pool.
- Adds an in-process market-data cache on top of the disk cache.
- Replaces duplicate root engine implementations with compatibility wrappers.
- Keeps all existing navigation and behaviour intact.

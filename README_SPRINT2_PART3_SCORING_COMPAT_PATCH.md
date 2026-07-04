# Catalyst AI v4 — Sprint 2 Part 3 Scoring Compatibility Patch

Fixes the existing test import error:

```text
cannot import name 'score_latest' from 'engine.scoring'
```

## Problem

Sprint 2 Part 3 replaced the old scoring API with smarter component scoring, but the older test suite still imports `score_latest`.

## Fix

Adds a compatibility wrapper:

```python
score_latest(row)
```

The wrapper uses the new smarter scoring engine and returns:

- score
- signal
- reason
- component scores

## Replaces

- engine/scoring.py
- version.py

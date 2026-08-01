# Catalyst AI v14.2 — Quant Research Lab

v14.2 freezes the v14 trading logic and adds a controlled research workflow:

- named, reproducible experiments on the same completed trade set;
- baseline-versus-candidate A/B comparison;
- locked benchmark storage;
- explicit promotion gates for profit factor, expectancy, drawdown, stress resilience and sample size;
- experiment history and JSON/CSV exports;
- research presets for ticker subsets/exclusions, score ranges, confidence floors, holding periods and market regimes.

Experiments are research-only. A PROMOTE result means the configured historical gates were met; it is not proof of future returns.

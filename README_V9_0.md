# Catalyst AI v9.0.0 — Evidence-Calibrated Confidence

## Core change

FULL position size is no longer granted by strategy score alone.

For every historical trade, Catalyst uses only trades that had already closed
before the new trade's entry date. Evidence is grouped by score band and the
original adaptive-risk label.

## Evidence states

- UNPROVEN — no prior evidence; size capped at 50%
- BUILDING — fewer than the required evidence trades; size capped
- MIXED — positive but insufficient out-of-sample performance
- PROVEN — profit factor, win rate, average return and sample-size thresholds met
- WEAK — prior out-of-sample evidence does not support confidence

## Delivered

- Walk-forward confidence calibration
- Evidence-gated FULL sizing
- Configurable minimum evidence sample
- Calibrated return and drawdown
- Calibrated equity curve
- Confidence Evidence table
- Original raw and adaptive results retained for comparison
- No future trade information used in any sizing decision

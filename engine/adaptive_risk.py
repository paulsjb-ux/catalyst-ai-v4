from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class AdaptiveRiskPlan:
    target_atr_multiple: float
    stop_atr_multiple: float
    position_size_pct: float
    risk_label: str
    rationale: str

def _safe(value, default=0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except (TypeError, ValueError):
        return default

def adaptive_risk_plan(
    *,
    score: float,
    volatility_20d_pct: float,
    change_20d_pct: float,
    change_60d_pct: float,
    rsi_14: float,
    signal: str = "BUY",
    base_target_atr: float = 2.0,
    base_stop_atr: float = 1.3,
    base_position_pct: float = 20.0,
) -> AdaptiveRiskPlan:
    score = _safe(score)
    volatility = max(0.0, _safe(volatility_20d_pct))
    change_20d = _safe(change_20d_pct)
    change_60d = _safe(change_60d_pct)
    rsi = _safe(rsi_14, 50)
    signal = str(signal or "").upper()

    target = float(base_target_atr)
    stop = float(base_stop_atr)
    size = float(base_position_pct)
    reasons = []

    strong = score >= 85 and change_20d >= 4 and change_60d >= 10 and 48 <= rsi <= 72
    weak = score < 80 or change_20d < 0 or change_60d < 3 or rsi > 76

    if strong:
        target += 0.45; stop += 0.10; size *= 1.10; reasons.append("strong trend")
    elif weak:
        target -= 0.25; stop -= 0.10; size *= 0.70; reasons.append("weaker setup")
    else:
        reasons.append("balanced setup")

    if volatility >= 5.0:
        target += 0.30; stop += 0.35; size *= 0.50; reasons.append("high volatility")
    elif volatility >= 3.5:
        target += 0.15; stop += 0.20; size *= 0.75; reasons.append("elevated volatility")
    elif 0 < volatility <= 2.2:
        stop -= 0.10; size *= 1.10; reasons.append("controlled volatility")

    if signal == "WATCH":
        size *= 0.50; target -= 0.10; reasons.append("WATCH sizing")

    if score >= 92:
        size *= 1.15
    elif score >= 86:
        size *= 1.00
    elif score >= 80:
        size *= 0.80
    else:
        size *= 0.60

    target = round(min(3.25, max(1.35, target)), 2)
    stop = round(min(2.20, max(0.90, stop)), 2)
    size = round(min(25.0, max(2.5, size)), 2)
    label = "FULL" if size >= 18 else ("REDUCED" if size >= 10 else "SMALL")

    return AdaptiveRiskPlan(target, stop, size, label, "; ".join(reasons))

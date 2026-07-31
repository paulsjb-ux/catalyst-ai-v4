from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd

from engine.executive_dashboard import best_trade, market_health, ranked_opportunities


@dataclass(frozen=True)
class TodaysDecision:
    action: str
    headline: str
    guidance: str
    confidence: int
    tone: str
    market_state: str
    market_score: int
    best_opportunity: dict[str, Any]
    buy_count: int
    watch_count: int
    scanned_count: int
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _signal_count(frame: pd.DataFrame, signal: str) -> int:
    if not isinstance(frame, pd.DataFrame) or frame.empty or "signal" not in frame.columns:
        return 0
    return int(frame["signal"].astype(str).str.upper().eq(signal).sum())


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if pd.isna(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def build_todays_decision(
    scan: pd.DataFrame | None,
    plans: pd.DataFrame | None,
    regime: dict | None,
) -> TodaysDecision:
    """Turn the latest trading-desk payload into one conservative daily decision.

    TRADE is reserved for a genuine BUY candidate in a supportive or neutral market.
    WATCH is used when candidates exist but conditions or signal quality are not strong
    enough. NO TRADE is a valid result when no qualified opportunities exist.
    """
    frame = scan if isinstance(scan, pd.DataFrame) else pd.DataFrame()
    plan_frame = plans if isinstance(plans, pd.DataFrame) else pd.DataFrame()
    regime = regime if isinstance(regime, dict) else {}

    health = market_health(regime, frame)
    opportunities = ranked_opportunities(frame, plan_frame, limit=10)
    trade = best_trade(opportunities)
    buy_count = _signal_count(frame, "BUY")
    watch_count = _signal_count(frame, "WATCH")
    scanned_count = int(len(frame))
    risk_state = str(health.get("risk_state", "NEUTRAL"))
    market_score = int(health.get("score", 0) or 0)

    best_signal = str(trade.get("signal", "")).upper()
    best_score = _safe_float(trade.get("score"))
    risk_reward = _safe_float(trade.get("risk_reward"))

    reasons: list[str] = []
    if scanned_count:
        reasons.append(f"{scanned_count} stocks were scored in the latest routine.")
    if risk_state == "RISK OFF":
        reasons.append("The market posture is defensive, so new risk should be limited.")
    elif risk_state == "RISK ON":
        reasons.append("The market posture is supportive of selective new positions.")
    else:
        reasons.append("The market posture is mixed, so selectivity remains important.")

    qualifies_as_trade = (
        buy_count > 0
        and best_signal == "BUY"
        and risk_state != "RISK OFF"
        and best_score >= 75
        and (risk_reward >= 2.0 or risk_reward == 0.0)
    )

    if qualifies_as_trade:
        action = "TRADE"
        tone = "trade"
        headline = "A qualified opportunity is ready for review."
        guidance = "Review the entry, target and stop before deciding whether to act."
        confidence = min(95, max(70, int(round(best_score))))
        reasons.append(f"{buy_count} BUY signal{'s' if buy_count != 1 else ''} passed the scanner.")
        if risk_reward:
            reasons.append(f"The leading plan offers approximately {risk_reward:.1f}:1 risk/reward.")
    elif buy_count > 0 or watch_count > 0:
        action = "WATCH"
        tone = "watch"
        headline = "There are candidates, but no trade should be chased."
        guidance = "Keep the strongest names under review and wait for the rules to confirm an entry."
        base = best_score if best_score else min(70, 45 + watch_count)
        confidence = min(88, max(50, int(round(base))))
        if buy_count > 0 and risk_state == "RISK OFF":
            reasons.append(f"{buy_count} BUY signal{'s were' if buy_count != 1 else ' was'} found, but the market filter is defensive.")
        else:
            reasons.append(f"{watch_count} WATCH candidate{'s' if watch_count != 1 else ''} remain below full BUY qualification.")
    else:
        action = "NO TRADE"
        tone = "no-trade"
        headline = "No high-quality trade is available today."
        guidance = "Stay patient. Cash is a position, and no trade is a valid decision."
        confidence = 90 if scanned_count else 55
        reasons.append("No BUY or WATCH candidate met the current decision threshold.")

    return TodaysDecision(
        action=action,
        headline=headline,
        guidance=guidance,
        confidence=confidence,
        tone=tone,
        market_state=risk_state,
        market_score=market_score,
        best_opportunity=trade,
        buy_count=buy_count,
        watch_count=watch_count,
        scanned_count=scanned_count,
        reasons=reasons[:4],
    )

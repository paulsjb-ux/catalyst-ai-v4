from __future__ import annotations

import pandas as pd

from engine.trade_plans import build_trade_plans, filter_trade_plan_candidates


def index_detail(regime: dict, ticker: str) -> dict:
    for item in regime.get("indices", []) if isinstance(regime, dict) else []:
        if isinstance(item, dict) and item.get("ticker") == ticker:
            return item
    return {}


def regime_is_complete(regime: dict) -> bool:
    if not isinstance(regime, dict) or not regime:
        return False
    return bool(index_detail(regime, "SPY") and index_detail(regime, "QQQ"))


def plans_are_complete(plans: pd.DataFrame) -> bool:
    required = {"ticker", "entry_price", "target_price", "stop_loss", "risk_reward"}
    if not isinstance(plans, pd.DataFrame) or plans.empty or not required.issubset(plans.columns):
        return False
    return bool(plans["entry_price"].notna().any())


def derive_regime_from_scan(frame: pd.DataFrame) -> dict:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return {}
    first = frame.iloc[0]
    regime_name = str(first.get("market_regime", "UNKNOWN") or "UNKNOWN")
    score = int(pd.to_numeric(pd.Series([first.get("market_score", 0)]), errors="coerce").fillna(0).iloc[0])
    adjustment = int(pd.to_numeric(pd.Series([first.get("market_adjustment", 0)]), errors="coerce").fillna(0).iloc[0])
    risk_labels = {
        "RISK_ON": "Supportive",
        "CONSTRUCTIVE": "Positive",
        "NEUTRAL": "Mixed",
        "DEFENSIVE": "Cautious",
        "RISK_OFF": "Hostile",
    }
    return {
        "regime": regime_name,
        "market_score": score,
        "regime_adjustment": adjustment,
        "risk_label": risk_labels.get(regime_name, "Unknown"),
        "reason": str(first.get("regime_reason", "Saved scan market context")),
        "indices": [],
        "vix": {},
    }


def repair_plans(frame: pd.DataFrame, plans: pd.DataFrame) -> pd.DataFrame:
    if plans_are_complete(plans):
        return plans
    candidates = filter_trade_plan_candidates(frame)
    if candidates.empty:
        return pd.DataFrame()
    return build_trade_plans(candidates, {})

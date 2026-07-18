from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd


def _frame(value: pd.DataFrame | None) -> pd.DataFrame:
    return value.copy() if value is not None and not value.empty else pd.DataFrame()


def top_buy_candidates(scan: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    frame = _frame(scan)
    if frame.empty or "signal" not in frame.columns:
        return pd.DataFrame()
    frame = frame[frame["signal"] == "BUY"].copy()
    if frame.empty:
        return frame
    if "score" in frame.columns:
        frame = frame.sort_values("score", ascending=False)
    columns = ["ticker", "signal", "score", "close", "market_regime", "market_adjustment", "reason"]
    return frame[[c for c in columns if c in frame.columns]].head(limit).reset_index(drop=True)


def top_repeat_winners(repeat_winners: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    frame = _frame(repeat_winners)
    if frame.empty:
        return frame
    for column in ["priority_score", "appearance_count", "buy_count", "avg_score", "average_score"]:
        if column in frame.columns:
            frame = frame.sort_values(column, ascending=False)
            break
    return frame.head(limit).reset_index(drop=True)


def portfolio_alerts(monitor: pd.DataFrame) -> pd.DataFrame:
    frame = _frame(monitor)
    if frame.empty or "alerts" not in frame.columns:
        return pd.DataFrame()
    frame = frame[frame["alerts"].fillna("NONE") != "NONE"].copy()
    columns = ["ticker", "current_price", "latest_signal", "holding_status", "distance_to_target_pct", "distance_to_stop_pct", "alerts"]
    return frame[[c for c in columns if c in frame.columns]].reset_index(drop=True)


def near_target_positions(monitor: pd.DataFrame, threshold: float = 5.0) -> pd.DataFrame:
    frame = _frame(monitor)
    if frame.empty or "distance_to_target_pct" not in frame.columns:
        return pd.DataFrame()
    distance = pd.to_numeric(frame["distance_to_target_pct"], errors="coerce")
    frame = frame[(distance >= 0) & (distance <= threshold)].copy()
    columns = ["ticker", "current_price", "target_price", "distance_to_target_pct", "latest_signal", "holding_status"]
    result = frame[[c for c in columns if c in frame.columns]]
    return result.sort_values("distance_to_target_pct").reset_index(drop=True) if not result.empty else result


def near_stop_positions(monitor: pd.DataFrame, threshold: float = 5.0) -> pd.DataFrame:
    frame = _frame(monitor)
    if frame.empty or "distance_to_stop_pct" not in frame.columns:
        return pd.DataFrame()
    distance = pd.to_numeric(frame["distance_to_stop_pct"], errors="coerce")
    frame = frame[(distance >= 0) & (distance <= threshold)].copy()
    columns = ["ticker", "current_price", "stop_loss", "distance_to_stop_pct", "latest_signal", "holding_status"]
    result = frame[[c for c in columns if c in frame.columns]]
    return result.sort_values("distance_to_stop_pct").reset_index(drop=True) if not result.empty else result


def signal_changes(comparison: pd.DataFrame) -> pd.DataFrame:
    frame = _frame(comparison)
    if frame.empty:
        return pd.DataFrame()
    if "signal_change" in frame.columns:
        frame = frame[~frame["signal_change"].fillna("UNCHANGED").isin(["UNCHANGED", ""])]
    elif {"signal_now", "signal_prev"}.issubset(frame.columns):
        frame = frame[frame["signal_now"] != frame["signal_prev"]]
    else:
        return pd.DataFrame()
    columns = ["ticker", "signal_prev", "signal_now", "signal_change", "score_prev", "score_now", "score_change"]
    return frame[[c for c in columns if c in frame.columns]].reset_index(drop=True)


def validation_updates(validation: pd.DataFrame) -> pd.DataFrame:
    frame = _frame(validation)
    if frame.empty:
        return frame
    status_columns = [c for c in ["status_1d", "status_5d", "status_10d", "status_20d"] if c in frame.columns]
    if status_columns:
        mask = pd.Series(False, index=frame.index)
        for column in status_columns:
            mask |= frame[column].eq("COMPLETE")
        frame = frame[mask].copy()
    columns = ["ticker", "signal", "score", "return_1d_pct", "return_5d_pct", "return_10d_pct", "return_20d_pct", "validation_status"]
    return frame[[c for c in columns if c in frame.columns]].reset_index(drop=True)


def build_priorities(regime: dict | None, buys: pd.DataFrame, alerts: pd.DataFrame, near_target: pd.DataFrame, near_stop: pd.DataFrame, changes: pd.DataFrame, validation: pd.DataFrame) -> list[dict]:
    items: list[dict] = []
    label = (regime or {}).get("regime", "UNKNOWN")
    score = (regime or {}).get("market_score", 0)

    if label in {"RISK_OFF", "DEFENSIVE"}:
        items.append({"level": "HIGH", "title": "Protect capital", "detail": f"Market regime is {label} with score {score}. Tighten risk."})
    elif label in {"RISK_ON", "CONSTRUCTIVE"}:
        items.append({"level": "INFO", "title": "Supportive market", "detail": f"Market regime is {label} with score {score}. Strong setups have a tailwind."})

    if not near_stop.empty:
        items.append({"level": "HIGH", "title": "Positions near stop", "detail": ", ".join(near_stop["ticker"].astype(str).head(5))})
    if not near_target.empty:
        items.append({"level": "MEDIUM", "title": "Positions near target", "detail": ", ".join(near_target["ticker"].astype(str).head(5))})
    if not alerts.empty:
        critical = alerts[alerts["alerts"].astype(str).str.contains("STOP BREACHED|SIGNAL LOST", regex=True)]
        if not critical.empty:
            items.append({"level": "HIGH", "title": "Critical portfolio alerts", "detail": ", ".join(critical["ticker"].astype(str).head(5))})
    if not changes.empty and "signal_now" in changes.columns:
        upgrades = changes[changes["signal_now"] == "BUY"]
        if not upgrades.empty:
            items.append({"level": "MEDIUM", "title": "Fresh BUY upgrades", "detail": ", ".join(upgrades["ticker"].astype(str).head(5))})
    if not buys.empty:
        items.append({"level": "INFO", "title": "Top BUY candidates", "detail": ", ".join(buys["ticker"].astype(str).head(3))})
    if not validation.empty:
        items.append({"level": "INFO", "title": "Validation updated", "detail": f"{len(validation)} rows have completed evidence."})
    if not items:
        items.append({"level": "INFO", "title": "No urgent action", "detail": "No major alerts or fresh changes found."})

    order = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
    return sorted(items, key=lambda item: order.get(item["level"], 9))


def build_daily_brief(regime: dict | None, scan_frame: pd.DataFrame | None, repeat_frame: pd.DataFrame | None, monitor_frame: pd.DataFrame | None, comparison_frame: pd.DataFrame | None, validation_frame: pd.DataFrame | None) -> dict:
    buys = top_buy_candidates(_frame(scan_frame))
    repeats = top_repeat_winners(_frame(repeat_frame))
    alerts = portfolio_alerts(_frame(monitor_frame))
    targets = near_target_positions(_frame(monitor_frame))
    stops = near_stop_positions(_frame(monitor_frame))
    changes = signal_changes(_frame(comparison_frame))
    validation = validation_updates(_frame(validation_frame))
    regime_value = regime or {"regime": "UNKNOWN", "market_score": 0, "regime_adjustment": 0, "risk_label": "UNKNOWN", "reason": "Run Market Scan to refresh context."}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "regime": regime_value,
        "top_buys": buys,
        "repeat_winners": repeats,
        "portfolio_alerts": alerts,
        "near_target": targets,
        "near_stop": stops,
        "signal_changes": changes,
        "validation_updates": validation,
        "priorities": build_priorities(regime_value, buys, alerts, targets, stops, changes, validation),
    }


def daily_brief_to_markdown(brief: dict) -> str:
    regime = brief["regime"]
    lines = [
        "# Catalyst AI Daily Intelligence Brief", "", f"Generated: {brief['generated_at']}", "",
        "## Market Regime", f"- Regime: {regime.get('regime', 'UNKNOWN')}",
        f"- Market score: {regime.get('market_score', 0)}", f"- Adjustment: {regime.get('regime_adjustment', 0)}",
        f"- Risk label: {regime.get('risk_label', 'UNKNOWN')}", f"- Context: {regime.get('reason', '')}", "", "## What Matters Today",
    ]
    for item in brief["priorities"]:
        lines.append(f"- **{item['level']} — {item['title']}**: {item['detail']}")
    for title, key in [("Top BUY Candidates", "top_buys"), ("Repeat Winners", "repeat_winners"), ("Portfolio Alerts", "portfolio_alerts"), ("Near Target", "near_target"), ("Near Stop", "near_stop"), ("Signal Changes", "signal_changes"), ("Validation Updates", "validation_updates")]:
        frame = brief[key]
        lines.extend(["", f"## {title}", "No items." if frame is None or frame.empty else frame.to_markdown(index=False)])
    return "\n".join(lines)

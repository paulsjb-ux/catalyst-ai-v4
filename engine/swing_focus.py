from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import math

import pandas as pd

DEFAULT_PROOF_REPORT = Path("storage/validation/latest_proof_report.json")
PREFERRED_SCORE_MIN = 80.0
PREFERRED_SCORE_MAX = 85.0
DEFAULT_POSITION_CAP_PCT = 15.0


@dataclass(frozen=True)
class SwingPolicy:
    score_min: float = PREFERRED_SCORE_MIN
    score_max: float = PREFERRED_SCORE_MAX
    minimum_risk_reward: float = 2.0
    maximum_new_positions: int = 2
    position_cap_pct: float = DEFAULT_POSITION_CAP_PCT
    preferred_tickers: tuple[str, ...] = ("JPM", "MSFT", "GOOGL")

    def to_dict(self) -> dict:
        data = asdict(self)
        data["preferred_tickers"] = list(self.preferred_tickers)
        return data


def load_proof_report(path: str | Path = DEFAULT_PROOF_REPORT) -> dict:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def policy_from_proof(report: dict | None) -> SwingPolicy:
    """Create a conservative daily swing policy from validated evidence.

    The proof report is used only to prioritise—not guarantee—opportunities. A ticker
    is preferred when it has at least 30 trades and profit factor >= 1.20. The best
    profitable score band becomes the preferred range when it can be parsed.
    """
    report = report if isinstance(report, dict) else {}
    preferred: list[str] = []
    for row in report.get("by_ticker", []) or []:
        try:
            if int(row.get("trades", 0)) >= 30 and float(row.get("profit_factor", 0)) >= 1.20:
                preferred.append(str(row.get("ticker", "")).upper())
        except (TypeError, ValueError):
            continue

    score_min, score_max = PREFERRED_SCORE_MIN, PREFERRED_SCORE_MAX
    profitable_bands = []
    for row in report.get("by_score_band", []) or []:
        try:
            band = str(row.get("score_band", ""))
            pf = float(row.get("profit_factor", 0))
            trades = int(row.get("trades", 0))
            if pf > 1.0 and trades >= 30 and "-" in band:
                low, high = band.split("-", 1)
                profitable_bands.append((pf, float(low), float(high)))
        except (TypeError, ValueError):
            continue
    if profitable_bands:
        _, score_min, score_max = max(profitable_bands)

    return SwingPolicy(
        score_min=score_min,
        score_max=score_max,
        preferred_tickers=tuple(preferred or ("JPM", "MSFT", "GOOGL")),
    )


def _num(value, default: float = 0.0) -> float:
    try:
        number = float(value)
        return default if math.isnan(number) or math.isinf(number) else number
    except (TypeError, ValueError):
        return default


def build_swing_desk(
    scan: pd.DataFrame | None,
    plans: pd.DataFrame | None,
    regime: dict | None,
    *,
    proof_report: dict | None = None,
    policy: SwingPolicy | None = None,
) -> pd.DataFrame:
    """Rank fewer, higher-quality swing candidates for the one-button routine."""
    frame = scan.copy() if isinstance(scan, pd.DataFrame) else pd.DataFrame()
    plan_frame = plans.copy() if isinstance(plans, pd.DataFrame) else pd.DataFrame()
    if frame.empty or "ticker" not in frame.columns:
        return pd.DataFrame()

    policy = policy or policy_from_proof(proof_report)
    selected = frame[frame.get("signal", pd.Series(index=frame.index, dtype=str)).astype(str).isin(["BUY", "WATCH"])].copy()
    if selected.empty:
        return pd.DataFrame()

    if not plan_frame.empty and "ticker" in plan_frame.columns:
        merge_cols = [c for c in ["ticker", "entry_price", "target_price", "stop_loss", "risk_reward", "position_quality"] if c in plan_frame.columns]
        selected = selected.merge(plan_frame[merge_cols].drop_duplicates("ticker"), on="ticker", how="left", suffixes=("", "_plan"))

    selected["score"] = pd.to_numeric(selected.get("score"), errors="coerce").fillna(0.0)
    selected["risk_reward"] = pd.to_numeric(selected.get("risk_reward", 0.0), errors="coerce").fillna(0.0)
    selected["change_20d_pct"] = pd.to_numeric(selected.get("change_20d_pct", 0.0), errors="coerce").fillna(0.0)
    selected["change_60d_pct"] = pd.to_numeric(selected.get("change_60d_pct", 0.0), errors="coerce").fillna(0.0)
    selected["ticker"] = selected["ticker"].astype(str).str.upper()

    selected["validated_ticker"] = selected["ticker"].isin(policy.preferred_tickers)
    selected["validated_score_band"] = selected["score"].between(policy.score_min, policy.score_max, inclusive="both")
    selected["trend_confirmed"] = selected.get("trend", "").astype(str).isin(["TREND", "RECOVERING"])
    selected["momentum_confirmed"] = (selected["change_20d_pct"] > 0) & (selected["change_60d_pct"] > 0)
    selected["risk_reward_pass"] = (selected["risk_reward"] >= policy.minimum_risk_reward) | selected["risk_reward"].eq(0)

    regime_name = str((regime or {}).get("regime", "UNKNOWN"))
    defensive = regime_name in {"RISK_OFF", "DEFENSIVE"}

    selected["swing_quality_score"] = (
        selected["score"]
        + selected["validated_ticker"].astype(int) * 8
        + selected["validated_score_band"].astype(int) * 10
        + selected["trend_confirmed"].astype(int) * 5
        + selected["momentum_confirmed"].astype(int) * 5
        + selected["risk_reward_pass"].astype(int) * 4
        + selected["signal"].astype(str).eq("BUY").astype(int) * 4
        - (8 if defensive else 0)
    )

    selected["swing_status"] = "WATCH"
    qualified = (
        selected["validated_score_band"]
        & selected["trend_confirmed"]
        & selected["momentum_confirmed"]
        & selected["risk_reward_pass"]
        & (not defensive)
    )
    selected.loc[qualified, "swing_status"] = "QUALIFIED"
    selected.loc[qualified & selected["validated_ticker"], "swing_status"] = "PRIORITY"
    selected["position_size_pct"] = 0.0
    selected.loc[selected["swing_status"].eq("QUALIFIED"), "position_size_pct"] = min(policy.position_cap_pct, 10.0)
    selected.loc[selected["swing_status"].eq("PRIORITY"), "position_size_pct"] = policy.position_cap_pct

    selected = selected.sort_values(["swing_quality_score", "score"], ascending=False).reset_index(drop=True)
    selected["daily_rank"] = range(1, len(selected) + 1)
    selected["action"] = selected["swing_status"].map({"PRIORITY": "REVIEW TO BUY", "QUALIFIED": "REVIEW", "WATCH": "WATCH"})

    columns = [
        "daily_rank", "ticker", "action", "swing_status", "signal", "score",
        "swing_quality_score", "position_size_pct", "entry_price", "target_price",
        "stop_loss", "risk_reward", "trend", "change_20d_pct", "change_60d_pct",
        "validated_ticker", "validated_score_band",
    ]
    return selected[[c for c in columns if c in selected.columns]].head(10)


def swing_desk_summary(desk: pd.DataFrame | None, policy: SwingPolicy) -> dict:
    frame = desk if isinstance(desk, pd.DataFrame) else pd.DataFrame()
    qualified = frame[frame.get("swing_status", pd.Series(index=frame.index, dtype=str)).isin(["PRIORITY", "QUALIFIED"])] if not frame.empty else pd.DataFrame()
    return {
        "qualified_swing_trades": int(len(qualified)),
        "priority_swing_trades": int((qualified.get("swing_status", pd.Series(dtype=str)) == "PRIORITY").sum()),
        "maximum_new_positions": policy.maximum_new_positions,
        "position_cap_pct": policy.position_cap_pct,
        "preferred_score_band": f"{policy.score_min:g}-{policy.score_max:g}",
        "preferred_tickers": list(policy.preferred_tickers),
    }

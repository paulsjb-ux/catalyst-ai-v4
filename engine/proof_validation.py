from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import time
from typing import Any

import pandas as pd

from engine.adaptive_confidence import holding_period_diagnostics, confidence_diagnostics
from engine.research_diagnostics import (
    confidence_calibration, decision_filter_diagnostics, feature_attribution, stress_decomposition,
)


@dataclass(frozen=True)
class ValidationThresholds:
    minimum_trades: int = 30
    minimum_profit_factor: float = 1.20
    minimum_expectancy_pct: float = 0.0
    maximum_drawdown_pct: float = -20.0
    minimum_profitable_year_ratio: float = 0.60
    minimum_stress_profit_factor: float = 1.00


def _series(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _return_column(frame: pd.DataFrame) -> str:
    for column in ("v14_portfolio_return_pct", "v92_portfolio_return_pct", "calibrated_portfolio_return_pct", "portfolio_return_pct", "return_pct"):
        if column in frame.columns:
            return column
    return "return_pct"


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1.0 + returns / 100.0).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min() * 100.0)


def performance_summary(frame: pd.DataFrame, return_column: str | None = None) -> dict[str, Any]:
    if frame is None or frame.empty:
        return {
            "trades": 0, "win_rate_pct": 0.0, "average_return_pct": 0.0,
            "median_return_pct": 0.0, "total_return_pct": 0.0,
            "profit_factor": 0.0, "max_drawdown_pct": 0.0,
        }
    column = return_column or _return_column(frame)
    returns = _series(frame, column)
    winners = returns[returns > 0]
    losers = returns[returns <= 0]
    gross_profit = float(winners.sum())
    gross_loss = abs(float(losers.sum()))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (math.inf if gross_profit > 0 else 0.0)
    equity = (1.0 + returns / 100.0).cumprod()
    return {
        "trades": int(len(returns)),
        "win_rate_pct": round(float((returns > 0).mean() * 100.0), 2),
        "average_return_pct": round(float(returns.mean()), 4),
        "median_return_pct": round(float(returns.median()), 4),
        "total_return_pct": round(float((equity.iloc[-1] - 1.0) * 100.0), 2),
        "profit_factor": round(profit_factor, 3) if math.isfinite(profit_factor) else "∞",
        "max_drawdown_pct": round(_max_drawdown(returns), 2),
    }


def _group_report(trades: pd.DataFrame, group_column: str) -> pd.DataFrame:
    if trades is None or trades.empty or group_column not in trades.columns:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for group, frame in trades.groupby(group_column, dropna=False, sort=True):
        row = {group_column: str(group)}
        row.update(performance_summary(frame))
        rows.append(row)
    return pd.DataFrame(rows)


def add_test_periods(trades: pd.DataFrame) -> pd.DataFrame:
    output = trades.copy()
    date_col = "exit_date" if "exit_date" in output.columns else "entry_date"
    dates = pd.to_datetime(output.get(date_col), errors="coerce")
    output["test_year"] = dates.dt.year.astype("Int64")
    if "score_band" not in output.columns and "score" in output.columns:
        scores = _series(output, "score")
        output["score_band"] = pd.cut(scores, [-math.inf, 79, 84, 89, 94, math.inf], labels=["<80", "80-84", "85-89", "90-94", "95+"])
    if "confidence_regime" not in output.columns:
        output["confidence_regime"] = "UNKNOWN"
    return output


def stress_test(trades: pd.DataFrame, additional_cost_pct: float = 0.20, entry_delay_penalty_pct: float = 0.15) -> dict[str, Any]:
    if trades is None or trades.empty:
        return performance_summary(pd.DataFrame())
    stressed = trades.copy()
    source = _return_column(stressed)
    stressed["stress_return_pct"] = _series(stressed, source) - abs(float(additional_cost_pct)) - abs(float(entry_delay_penalty_pct))
    return performance_summary(stressed, "stress_return_pct")


def configuration_hash(configuration: dict[str, Any]) -> str:
    payload = json.dumps(configuration, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def trades_hash(trades: pd.DataFrame) -> str:
    if trades is None or trades.empty:
        return hashlib.sha256(b"empty").hexdigest()[:16]
    stable = trades.copy()
    stable = stable.sort_values([c for c in ("exit_date", "ticker", "entry_date") if c in stable.columns]).reset_index(drop=True)
    payload = stable.to_csv(index=False, date_format="%Y-%m-%dT%H:%M:%S")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_proof_report(
    trades: pd.DataFrame,
    *,
    build_version: str,
    configuration: dict[str, Any] | None = None,
    runtime_seconds: float | None = None,
    thresholds: ValidationThresholds | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    thresholds = thresholds or ValidationThresholds()
    configuration = configuration or {}
    prepared = add_test_periods(trades if trades is not None else pd.DataFrame())
    overall = performance_summary(prepared)
    by_year = _group_report(prepared.dropna(subset=["test_year"]), "test_year")
    by_ticker = _group_report(prepared, "ticker")
    by_score_band = _group_report(prepared, "score_band")
    by_regime = _group_report(prepared, "confidence_regime")
    stressed = stress_test(prepared)
    return_basis = _return_column(prepared) if not prepared.empty else "none"
    stress_breakdown = stress_decomposition(prepared, return_column=return_basis) if return_basis != "none" else pd.DataFrame()

    profitable_year_ratio = 0.0
    if not by_year.empty:
        profitable_year_ratio = float((pd.to_numeric(by_year["total_return_pct"], errors="coerce") > 0).mean())
    pf = overall["profit_factor"] if isinstance(overall["profit_factor"], (int, float)) else 999.0
    stress_pf = stressed["profit_factor"] if isinstance(stressed["profit_factor"], (int, float)) else 999.0
    checks = {
        "enough_trades": overall["trades"] >= thresholds.minimum_trades,
        "positive_expectancy": overall["average_return_pct"] > thresholds.minimum_expectancy_pct,
        "profit_factor": pf >= thresholds.minimum_profit_factor,
        "drawdown": overall["max_drawdown_pct"] >= thresholds.maximum_drawdown_pct,
        "year_consistency": profitable_year_ratio >= thresholds.minimum_profitable_year_ratio,
        "stress_survival": stress_pf >= thresholds.minimum_stress_profit_factor,
    }
    passed = sum(bool(v) for v in checks.values())
    verdict = "PASS" if passed == len(checks) else ("CONDITIONAL PASS" if passed >= 4 else "FAIL")

    elapsed = runtime_seconds if runtime_seconds is not None else time.perf_counter() - started
    return {
        "metadata": {
            "build": build_version,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "configuration_hash": configuration_hash(configuration),
            "trades_hash": trades_hash(prepared),
            "analysis_runtime_seconds": round(float(elapsed), 4),
            "return_basis": return_basis,
        },
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "thresholds": asdict(thresholds),
        "overall": overall,
        "stress": stressed,
        "profitable_year_ratio": round(profitable_year_ratio, 3),
        "by_year": by_year.to_dict(orient="records"),
        "by_ticker": by_ticker.sort_values("total_return_pct", ascending=False).to_dict(orient="records") if not by_ticker.empty else [],
        "by_score_band": by_score_band.to_dict(orient="records"),
        "by_regime": by_regime.to_dict(orient="records"),
        "by_holding_period": holding_period_diagnostics(prepared).to_dict(orient="records"),
        "by_adaptive_confidence": confidence_diagnostics(prepared).to_dict(orient="records"),
        "decision_filter_diagnostics": decision_filter_diagnostics(prepared).to_dict(orient="records"),
        "stress_decomposition": stress_breakdown.to_dict(orient="records"),
        "feature_attribution": feature_attribution(prepared).to_dict(orient="records"),
        "confidence_calibration": confidence_calibration(prepared).to_dict(orient="records"),
        "disclosures": [
            "Historical performance is not a guarantee of future results.",
            "Validation uses completed trades supplied by the backtest engine.",
            "Stress results subtract an additional 0.20% cost and 0.15% delayed-entry penalty per trade.",
            "v14.1 diagnostics are descriptive and do not alter trade selection or historical returns.",
            "Survivorship bias and data-provider adjustments must be reviewed before live deployment.",
        ],
    }

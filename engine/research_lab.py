from __future__ import annotations

"""Catalyst AI v14.2 quantitative research lab.

The lab runs controlled, reproducible A/B experiments on the same completed
trade set. It does not alter production trading logic. Experiments are promoted
only when they improve agreed evidence gates relative to a locked benchmark.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
import hashlib
import json

import pandas as pd

from engine.proof_validation import performance_summary, stress_test, trades_hash

DEFAULT_BENCHMARK_PATH = Path("storage/research/locked_benchmark.json")
DEFAULT_HISTORY_DIR = Path("storage/research/experiments")


@dataclass(frozen=True)
class PromotionRules:
    minimum_profit_factor_improvement: float = 0.01
    minimum_expectancy_improvement_pct: float = 0.0
    maximum_drawdown_deterioration_pct: float = 0.50
    minimum_stress_pf_improvement: float = 0.0
    minimum_trades: int = 30


def _return_column(frame: pd.DataFrame) -> str:
    for column in ("v14_portfolio_return_pct", "v92_portfolio_return_pct", "calibrated_portfolio_return_pct", "portfolio_return_pct", "return_pct"):
        if column in frame.columns:
            return column
    return "return_pct"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _experiment_id(name: str, params: dict[str, Any], source_hash: str) -> str:
    payload = json.dumps({"name": name, "params": params, "source_hash": source_hash}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def apply_experiment(trades: pd.DataFrame, experiment_type: str, params: dict[str, Any]) -> pd.DataFrame:
    """Apply a transparent research-only filter to completed trades."""
    if trades is None or trades.empty:
        return pd.DataFrame(columns=getattr(trades, "columns", []))
    result = trades.copy()
    kind = str(experiment_type).strip().lower()

    if kind == "ticker_subset":
        tickers = {str(x).upper() for x in params.get("tickers", [])}
        if tickers and "ticker" in result.columns:
            result = result[result["ticker"].astype(str).str.upper().isin(tickers)]
    elif kind == "exclude_tickers":
        tickers = {str(x).upper() for x in params.get("tickers", [])}
        if tickers and "ticker" in result.columns:
            result = result[~result["ticker"].astype(str).str.upper().isin(tickers)]
    elif kind == "score_range":
        if "score" in result.columns:
            score = pd.to_numeric(result["score"], errors="coerce")
            lower = _number(params.get("minimum"), float("-inf"))
            upper = _number(params.get("maximum"), float("inf"))
            result = result[score.between(lower, upper, inclusive="both")]
        elif "score_band" in result.columns and params.get("bands"):
            bands = {str(x) for x in params.get("bands", [])}
            result = result[result["score_band"].astype(str).isin(bands)]
    elif kind == "confidence_floor":
        column = "v14_confidence_score" if "v14_confidence_score" in result.columns else "confidence"
        if column in result.columns:
            confidence = pd.to_numeric(result[column], errors="coerce")
            result = result[confidence >= _number(params.get("minimum"), 0.0)]
    elif kind == "holding_period":
        column = "holding_days" if "holding_days" in result.columns else None
        if column:
            days = pd.to_numeric(result[column], errors="coerce")
            lower = _number(params.get("minimum_days"), 0.0)
            upper = _number(params.get("maximum_days"), float("inf"))
            result = result[days.between(lower, upper, inclusive="both")]
    elif kind == "regime_subset":
        column = "market_regime" if "market_regime" in result.columns else "confidence_regime"
        regimes = {str(x).upper() for x in params.get("regimes", [])}
        if regimes and column in result.columns:
            result = result[result[column].astype(str).str.upper().isin(regimes)]
    elif kind == "combined":
        for step in params.get("steps", []):
            result = apply_experiment(result, str(step.get("type", "")), dict(step.get("params", {})))
    elif kind not in ("baseline", "none", ""):
        raise ValueError(f"Unsupported experiment type: {experiment_type}")

    return result.copy().reset_index(drop=True)


def evaluate_experiment(
    trades: pd.DataFrame,
    *,
    name: str,
    experiment_type: str,
    params: dict[str, Any] | None = None,
    rules: PromotionRules | None = None,
) -> dict[str, Any]:
    """Run baseline and candidate on identical source trades and score promotion."""
    params = params or {}
    rules = rules or PromotionRules()
    source = trades.copy() if trades is not None else pd.DataFrame()
    candidate = apply_experiment(source, experiment_type, params)
    return_column = _return_column(source)

    baseline = performance_summary(source, return_column)
    baseline_stress = stress_test(source)
    candidate_summary = performance_summary(candidate, _return_column(candidate))
    candidate_stress = stress_test(candidate)

    pf_delta = _number(candidate_summary.get("profit_factor")) - _number(baseline.get("profit_factor"))
    expectancy_delta = _number(candidate_summary.get("average_return_pct")) - _number(baseline.get("average_return_pct"))
    drawdown_delta = _number(candidate_summary.get("max_drawdown_pct")) - _number(baseline.get("max_drawdown_pct"))
    stress_pf_delta = _number(candidate_stress.get("profit_factor")) - _number(baseline_stress.get("profit_factor"))

    checks = {
        "enough_candidate_trades": int(candidate_summary.get("trades", 0)) >= rules.minimum_trades,
        "profit_factor_improved": pf_delta >= rules.minimum_profit_factor_improvement,
        "expectancy_not_worse": expectancy_delta >= rules.minimum_expectancy_improvement_pct,
        "drawdown_not_materially_worse": drawdown_delta >= -abs(rules.maximum_drawdown_deterioration_pct),
        "stress_pf_not_worse": stress_pf_delta >= rules.minimum_stress_pf_improvement,
    }
    promoted = all(checks.values())
    source_hash = trades_hash(source)
    return {
        "experiment_id": _experiment_id(name, params, source_hash),
        "name": name,
        "experiment_type": experiment_type,
        "params": params,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_trades_hash": source_hash,
        "source_trade_count": int(len(source)),
        "candidate_trade_count": int(len(candidate)),
        "baseline": {"overall": baseline, "stress": baseline_stress},
        "candidate": {"overall": candidate_summary, "stress": candidate_stress},
        "changes": {
            "profit_factor": round(pf_delta, 4),
            "average_return_pct": round(expectancy_delta, 4),
            "max_drawdown_pct": round(drawdown_delta, 4),
            "stress_profit_factor": round(stress_pf_delta, 4),
            "trade_count": int(candidate_summary.get("trades", 0)) - int(baseline.get("trades", 0)),
        },
        "promotion_rules": asdict(rules),
        "promotion_checks": checks,
        "verdict": "PROMOTE" if promoted else "REJECT",
        "disclosure": "Research-only A/B test on completed historical trades; this does not prove future performance.",
    }


def lock_benchmark(report: dict[str, Any], path: str | Path = DEFAULT_BENCHMARK_PATH) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "locked_utc": datetime.now(timezone.utc).isoformat(),
        "metadata": report.get("metadata", {}),
        "overall": report.get("overall", {}),
        "stress": report.get("stress", {}),
        "checks": report.get("checks", {}),
        "verdict": report.get("verdict"),
    }
    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return target


def load_locked_benchmark(path: str | Path = DEFAULT_BENCHMARK_PATH) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def save_experiment(result: dict[str, Any], history_dir: str | Path = DEFAULT_HISTORY_DIR) -> Path:
    directory = Path(history_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"experiment_{result.get('experiment_id', 'unknown')}_{stamp}.json"
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return path


def list_experiments(history_dir: str | Path = DEFAULT_HISTORY_DIR) -> pd.DataFrame:
    directory = Path(history_dir)
    columns = ["experiment_id", "name", "type", "verdict", "candidate_trades", "pf_change", "stress_pf_change", "generated_utc", "path"]
    if not directory.exists():
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("experiment_*.json"), reverse=True):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append({
            "experiment_id": result.get("experiment_id"),
            "name": result.get("name"),
            "type": result.get("experiment_type"),
            "verdict": result.get("verdict"),
            "candidate_trades": result.get("candidate_trade_count"),
            "pf_change": (result.get("changes") or {}).get("profit_factor"),
            "stress_pf_change": (result.get("changes") or {}).get("stress_profit_factor"),
            "generated_utc": result.get("generated_utc"),
            "path": str(path),
        })
    return pd.DataFrame(rows, columns=columns)


def experiment_comparison_frame(result: dict[str, Any]) -> pd.DataFrame:
    baseline = (result.get("baseline") or {}).get("overall", {})
    candidate = (result.get("candidate") or {}).get("overall", {})
    baseline_stress = (result.get("baseline") or {}).get("stress", {})
    candidate_stress = (result.get("candidate") or {}).get("stress", {})
    rows = [
        ("Trades", baseline.get("trades"), candidate.get("trades")),
        ("Win rate %", baseline.get("win_rate_pct"), candidate.get("win_rate_pct")),
        ("Average trade %", baseline.get("average_return_pct"), candidate.get("average_return_pct")),
        ("Total return %", baseline.get("total_return_pct"), candidate.get("total_return_pct")),
        ("Profit factor", baseline.get("profit_factor"), candidate.get("profit_factor")),
        ("Max drawdown %", baseline.get("max_drawdown_pct"), candidate.get("max_drawdown_pct")),
        ("Stress profit factor", baseline_stress.get("profit_factor"), candidate_stress.get("profit_factor")),
        ("Stress return %", baseline_stress.get("total_return_pct"), candidate_stress.get("total_return_pct")),
    ]
    output = []
    for metric, base, cand in rows:
        try:
            change = round(float(cand) - float(base), 4)
        except (TypeError, ValueError):
            change = None
        output.append({"metric": metric, "baseline": base, "candidate": cand, "change": change})
    return pd.DataFrame(output)

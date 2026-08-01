from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable
import json
import logging

import pandas as pd

from engine.daily_brief import build_daily_brief, daily_brief_to_markdown

ProgressCallback = Callable[[str, int, str], None]
LOGGER = logging.getLogger(__name__)
DEFAULT_EXPORT_RETENTION_DAYS = 30
DEFAULT_EXPORT_RETENTION_FILES = 120


@dataclass
class RoutineResult:
    started_at: str
    finished_at: str = ""
    duration_seconds: float = 0.0
    success: bool = False
    stages: list[dict] = field(default_factory=list)
    scan_results: pd.DataFrame = field(default_factory=pd.DataFrame)
    trade_plans: pd.DataFrame = field(default_factory=pd.DataFrame)
    comparison: pd.DataFrame = field(default_factory=pd.DataFrame)
    regime: dict = field(default_factory=dict)
    market_errors: dict = field(default_factory=dict)
    brief: dict = field(default_factory=dict)
    alert_result: dict = field(default_factory=dict)
    exports: list[str] = field(default_factory=list)
    scan_id: str = ""
    universe_health: dict = field(default_factory=dict)
    swing_desk: pd.DataFrame = field(default_factory=pd.DataFrame)
    swing_summary: dict = field(default_factory=dict)
    proof_health: dict = field(default_factory=dict)

    def summary(self) -> dict:
        scan = self.scan_results if self.scan_results is not None else pd.DataFrame()
        return {
            "success": self.success,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "symbols_scanned": int(len(scan)),
            "buy_count": int((scan.get("signal", pd.Series(dtype=str)) == "BUY").sum()),
            "watch_count": int((scan.get("signal", pd.Series(dtype=str)) == "WATCH").sum()),
            "confidence_a_count": int((scan.get("confidence_band", pd.Series(dtype=str)) == "A").sum()),
            "confidence_b_count": int((scan.get("confidence_band", pd.Series(dtype=str)) == "B").sum()),
            "trade_plan_count": int(len(self.trade_plans)),
            "data_error_count": int(len(self.market_errors)),
            "universe_health": self.universe_health,
            "market_success_rate_pct": self.universe_health.get("success_rate_pct", 0),
            "quarantined_count": self.universe_health.get("quarantined", 0),
            "alerts_generated": int(self.alert_result.get("generated", self.alert_result.get("alert_count", 0)) or 0),
            "exports_created": int(len(self.exports)),
            "scan_id": self.scan_id,
            "qualified_swing_trades": int(self.swing_summary.get("qualified_swing_trades", 0)),
            "priority_swing_trades": int(self.swing_summary.get("priority_swing_trades", 0)),
            "maximum_new_positions": int(self.swing_summary.get("maximum_new_positions", 2)),
            "position_cap_pct": float(self.swing_summary.get("position_cap_pct", 15.0)),
            "preferred_score_band": self.swing_summary.get("preferred_score_band", "80-85"),
            "preferred_tickers": self.swing_summary.get("preferred_tickers", []),
            "proof_verdict": self.proof_health.get("verdict", "NOT RUN"),
            "stages": self.stages,
        }


def _notify(callback: ProgressCallback | None, stage: str, percent: int, message: str) -> None:
    if callback:
        callback(stage, percent, message)


def _record(result: RoutineResult, stage: str, status: str, detail: str) -> None:
    result.stages.append({"stage": stage, "status": status, "detail": detail})



def _cleanup_exports(export_dir: Path, max_age_days: int = DEFAULT_EXPORT_RETENTION_DAYS, max_files: int = DEFAULT_EXPORT_RETENTION_FILES) -> int:
    if not export_dir.exists():
        return 0
    files = sorted((p for p in export_dir.iterdir() if p.is_file() and p.name.startswith("catalyst_")), key=lambda p: p.stat().st_mtime, reverse=True)
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_days * 86400
    removed = 0
    for index, path in enumerate(files):
        if index >= max_files or path.stat().st_mtime < cutoff:
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def _write_exports(result: RoutineResult, export_dir: Path) -> list[str]:
    export_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_exports(export_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    paths: list[Path] = []
    for name, frame in (("scan", result.scan_results), ("trade_plans", result.trade_plans), ("swing_desk", result.swing_desk), ("comparison", result.comparison)):
        if frame is not None and not frame.empty:
            path = export_dir / f"catalyst_{name}_{stamp}.csv"
            frame.to_csv(path, index=False)
            paths.append(path)
    if result.brief:
        brief_path = export_dir / f"catalyst_daily_brief_{stamp}.md"
        brief_path.write_text(daily_brief_to_markdown(result.brief), encoding="utf-8")
        paths.append(brief_path)
    summary_path = export_dir / f"catalyst_daily_routine_{stamp}.json"
    summary_path.write_text(json.dumps(result.summary(), indent=2, default=str), encoding="utf-8")
    paths.append(summary_path)
    return [str(path) for path in paths]


def run_daily_routine(
    *,
    period: str = "1y",
    max_tickers: int = 750,
    include_regime: bool = True,
    export_dir: str | Path = "storage/exports",
    progress: ProgressCallback | None = None,
    send_alerts: bool = True,
    scan_workers: int | None = None,
) -> RoutineResult:
    started = datetime.now(timezone.utc)
    timer = perf_counter()
    result = RoutineResult(started_at=started.isoformat())

    try:
        # Lazy imports keep the result/export helpers testable even when optional
        # live-market dependencies are not installed in the test environment.
        from alerts.runner import run_alert_job
        from data.history_store import compare_scans, load_previous_scan, save_scan
        from data.market_data import download_history
        from data.universe_health import quarantined_tickers, update_universe_health
        from engine.market_regime import REGIME_TICKERS, build_market_regime
        from engine.scanner import run_scan
        from engine.trade_plans import build_trade_plans, filter_trade_plan_candidates
        from engine.swing_focus import build_swing_desk, load_proof_report, policy_from_proof, swing_desk_summary
        from engine.universe_builder import build_scan_universe

        _notify(progress, "universe", 5, "Building the quality-controlled market universe")
        quarantine = quarantined_tickers()
        tickers = build_scan_universe(
            include_sp500=True,
            include_nasdaq100=True,
            include_global_liquid=True,
            include_watchlist=True,
            include_starter_large_universe=True,
            include_broad_us=True,
            excluded_tickers=quarantine,
            max_tickers=max_tickers,
        )
        if not tickers:
            raise RuntimeError("The scan universe is empty.")
        _record(result, "Universe", "complete", f"{len(tickers)} symbols selected; {len(quarantine)} quarantined")

        download_tickers = list(tickers)
        for ticker in REGIME_TICKERS:
            if ticker not in download_tickers:
                download_tickers.append(ticker)
        _notify(progress, "market_data", 20, f"Downloading market data for {len(download_tickers)} symbols ({len(tickers)} scan symbols plus {len(download_tickers) - len(tickers)} regime symbols)")
        market = download_history(download_tickers, period=period)
        result.market_errors = market.errors
        result.universe_health = update_universe_health(tickers, market.prices.keys(), market.errors)
        if not market.prices:
            raise RuntimeError("No market data was downloaded.")
        _record(result, "Market data", "complete", f"{len(market.prices)} symbols loaded; {len(market.errors)} errors; "f"{result.universe_health.get('success_rate_pct', 0)}% success")

        _notify(progress, "regime", 35, "Detecting SPY/QQQ market regime")
        result.regime = build_market_regime(market.prices) if include_regime else {}
        _record(result, "Market regime", "complete", result.regime.get("regime", "Disabled"))

        _notify(progress, "scan", 52, "Scoring the universe")
        scan_kwargs = {"workers": scan_workers} if scan_workers else {}
        result.scan_results = run_scan(
            market.prices,
            market_regime=result.regime or None,
            **scan_kwargs,
        )
        if result.scan_results.empty:
            raise RuntimeError("The market scan returned no results.")
        saved = save_scan(result.scan_results)
        result.scan_id = saved.scan_id if saved else ""
        previous = load_previous_scan(result.scan_id) if saved else pd.DataFrame()
        result.comparison = compare_scans(result.scan_results, previous)
        _record(result, "Universe scan", "complete", f"{len(result.scan_results)} symbols scored")

        _notify(progress, "plans", 68, "Generating target, stop and risk/reward plans")
        result.trade_plans = build_trade_plans(filter_trade_plan_candidates(result.scan_results), market.prices)
        _record(result, "Trade plans", "complete", f"{len(result.trade_plans)} plans generated")

        _notify(progress, "swing_desk", 74, "Selecting fewer, higher-quality swing opportunities")
        proof_report = load_proof_report()
        policy = policy_from_proof(proof_report)
        result.proof_health = {
            "verdict": proof_report.get("verdict", "NOT RUN"),
            "profit_factor": (proof_report.get("overall") or {}).get("profit_factor"),
            "checks_passed": proof_report.get("checks_passed"),
            "checks_total": proof_report.get("checks_total"),
        }
        result.swing_desk = build_swing_desk(
            result.scan_results, result.trade_plans, result.regime,
            proof_report=proof_report, policy=policy,
        )
        result.swing_summary = swing_desk_summary(result.swing_desk, policy)
        _record(result, "Swing desk", "complete", f"{result.swing_summary.get('qualified_swing_trades', 0)} qualified; maximum {policy.maximum_new_positions} new positions")

        _notify(progress, "brief", 79, "Generating the Daily Intelligence Brief")
        result.brief = build_daily_brief(
            result.regime,
            result.scan_results,
            pd.DataFrame(),
            pd.DataFrame(),
            result.comparison,
            pd.DataFrame(),
        )
        _record(result, "Daily Brief", "complete", "Brief generated")

        _notify(progress, "alerts", 88, "Refreshing alerts")
        if send_alerts:
            try:
                result.alert_result = run_alert_job(
                    comparison=result.comparison,
                    monitor=pd.DataFrame(),
                    regime=result.regime,
                    trigger="daily_routine",
                )
                _record(result, "Alerts", "complete", "Alert cycle refreshed")
            except Exception as exc:
                result.alert_result = {"error": str(exc), "generated": 0}
                _record(result, "Alerts", "warning", f"Alert refresh failed: {exc}")
        else:
            _record(result, "Alerts", "skipped", "Alert delivery disabled")

        _notify(progress, "exports", 95, "Writing CSV, Markdown and JSON exports")
        result.exports = _write_exports(result, Path(export_dir))
        _record(result, "Exports", "complete", f"{len(result.exports)} files created")
        result.success = True
    except Exception as exc:
        LOGGER.exception("Daily Routine failed")
        _record(result, "Routine", "failed", str(exc))
        result.success = False
    finally:
        result.finished_at = datetime.now(timezone.utc).isoformat()
        result.duration_seconds = round(perf_counter() - timer, 2)
        _notify(progress, "complete", 100, "Daily Routine complete" if result.success else "Daily Routine stopped")
    return result

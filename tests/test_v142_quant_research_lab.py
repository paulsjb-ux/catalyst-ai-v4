import json
import pandas as pd

from engine.research_lab import (
    apply_experiment, evaluate_experiment, experiment_comparison_frame,
    list_experiments, load_locked_benchmark, lock_benchmark, save_experiment,
)


def _trades():
    return pd.DataFrame({
        "ticker": ["JPM", "MSFT", "NVDA", "JPM", "GOOGL", "AVGO"] * 8,
        "score": [82, 84, 88, 81, 85, 87] * 8,
        "score_band": ["80-85", "80-85", "86-91", "80-85", "80-85", "86-91"] * 8,
        "holding_days": [8, 12, 4, 15, 18, 5] * 8,
        "entry_date": pd.date_range("2023-01-01", periods=48, freq="7D"),
        "exit_date": pd.date_range("2023-01-08", periods=48, freq="7D"),
        "return_pct": [1.2, .8, -1.1, .7, .5, -.9] * 8,
        "v14_portfolio_return_pct": [.18, .12, -.165, .105, .075, -.135] * 8,
        "v14_confidence_score": [72, 68, 46, 66, 61, 44] * 8,
    })


def test_presets_filter_same_source_without_mutation():
    source = _trades()
    original = source.copy(deep=True)
    candidate = apply_experiment(source, "score_range", {"minimum": 80, "maximum": 85})
    assert len(candidate) == 32
    pd.testing.assert_frame_equal(source, original)


def test_ab_experiment_has_reproducible_id_and_promotion_gates():
    one = evaluate_experiment(_trades(), name="Core", experiment_type="exclude_tickers", params={"tickers": ["NVDA", "AVGO"]})
    two = evaluate_experiment(_trades(), name="Core", experiment_type="exclude_tickers", params={"tickers": ["NVDA", "AVGO"]})
    assert one["experiment_id"] == two["experiment_id"]
    assert one["candidate_trade_count"] < one["source_trade_count"]
    assert set(one["promotion_checks"]) == {
        "enough_candidate_trades", "profit_factor_improved", "expectancy_not_worse",
        "drawdown_not_materially_worse", "stress_pf_not_worse",
    }
    assert not experiment_comparison_frame(one).empty


def test_benchmark_and_history_round_trip(tmp_path):
    report = {"metadata": {"build": "14.2"}, "overall": {"profit_factor": 1.2}, "stress": {"profit_factor": .5}, "checks": {}, "verdict": "FAIL"}
    benchmark = tmp_path / "benchmark.json"
    lock_benchmark(report, benchmark)
    assert load_locked_benchmark(benchmark)["metadata"]["build"] == "14.2"

    result = evaluate_experiment(_trades(), name="Core", experiment_type="ticker_subset", params={"tickers": ["JPM", "MSFT", "GOOGL"]})
    path = save_experiment(result, tmp_path / "history")
    assert path.exists()
    history = list_experiments(tmp_path / "history")
    assert len(history) == 1
    assert history.iloc[0]["experiment_id"] == result["experiment_id"]

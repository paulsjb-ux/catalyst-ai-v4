from __future__ import annotations

import pandas as pd


FORWARD_WINDOWS = [1, 5, 10, 20]


def calculate_forward_returns(
    scan_frame: pd.DataFrame,
    price_map: dict[str, pd.DataFrame],
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Calculate forward returns for a saved scan using downloaded price history.

    The scan close is treated as the entry price. The latest available prices
    from yfinance are used to estimate the forward result for each window.
    If enough forward data is unavailable, that window is left blank.
    """
    if scan_frame is None or scan_frame.empty:
        return pd.DataFrame()

    windows = windows or FORWARD_WINDOWS
    rows: list[dict] = []

    for _, signal_row in scan_frame.iterrows():
        ticker = str(signal_row.get("ticker", "")).upper().strip()
        if not ticker:
            continue

        prices = price_map.get(ticker)
        if prices is None or prices.empty or "Close" not in prices.columns:
            continue

        entry = float(signal_row.get("close", 0) or 0)
        if entry <= 0:
            continue

        closes = prices["Close"].dropna().reset_index(drop=True)
        if closes.empty:
            continue

        # Use the first close after the scan as the earliest forward point.
        output = signal_row.to_dict()
        output["entry_price"] = round(entry, 2)
        output["latest_price"] = round(float(closes.iloc[-1]), 2)

        valid_returns = []

        for window in windows:
            col_return = f"return_{window}d_pct"
            col_win = f"win_{window}d"

            if len(closes) > window:
                future_price = float(closes.iloc[min(window, len(closes) - 1)])
                forward_return = ((future_price / entry) - 1) * 100
                output[col_return] = round(forward_return, 2)
                output[col_win] = bool(forward_return > 0)
                valid_returns.append(forward_return)
            else:
                output[col_return] = None
                output[col_win] = None

        if valid_returns:
            output["avg_forward_return_pct"] = round(sum(valid_returns) / len(valid_returns), 2)
        else:
            output["avg_forward_return_pct"] = None

        rows.append(output)

    return pd.DataFrame(rows)


def summarise_validation(validation_frame: pd.DataFrame) -> pd.DataFrame:
    """Summarise validation performance by signal."""
    if validation_frame is None or validation_frame.empty:
        return pd.DataFrame(
            columns=[
                "signal",
                "count",
                "avg_score",
                "avg_1d_return",
                "win_rate_1d",
                "avg_5d_return",
                "win_rate_5d",
                "avg_10d_return",
                "win_rate_10d",
                "avg_20d_return",
                "win_rate_20d",
            ]
        )

    rows = []
    for signal, group in validation_frame.groupby("signal"):
        row = {
            "signal": signal,
            "count": len(group),
            "avg_score": round(float(group["score"].mean()), 1) if "score" in group else None,
        }

        for window in FORWARD_WINDOWS:
            return_col = f"return_{window}d_pct"
            win_col = f"win_{window}d"
            avg_col = f"avg_{window}d_return"
            rate_col = f"win_rate_{window}d"

            if return_col in group:
                returns = pd.to_numeric(group[return_col], errors="coerce").dropna()
                row[avg_col] = round(float(returns.mean()), 2) if not returns.empty else None
            else:
                row[avg_col] = None

            if win_col in group:
                wins = group[win_col].dropna()
                row[rate_col] = round(float(wins.mean() * 100), 1) if not wins.empty else None
            else:
                row[rate_col] = None

        rows.append(row)

    return pd.DataFrame(rows).sort_values("signal").reset_index(drop=True)


def validation_quality_label(row: pd.Series) -> str:
    """Assign a simple quality label based on forward validation."""
    avg_5d = row.get("avg_5d_return")
    win_5d = row.get("win_rate_5d")

    if pd.isna(avg_5d) or pd.isna(win_5d):
        return "INSUFFICIENT DATA"

    if avg_5d > 2 and win_5d >= 60:
        return "STRONG"
    if avg_5d > 0 and win_5d >= 50:
        return "POSITIVE"
    if avg_5d < -2:
        return "WEAK"
    return "NEUTRAL"


def add_quality_labels(summary_frame: pd.DataFrame) -> pd.DataFrame:
    if summary_frame is None or summary_frame.empty:
        return pd.DataFrame()
    output = summary_frame.copy()
    output["quality"] = output.apply(validation_quality_label, axis=1)
    return output

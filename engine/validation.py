from __future__ import annotations

import pandas as pd


FORWARD_WINDOWS = [1, 5, 10, 20]


def _parse_saved_at(value) -> pd.Timestamp | None:
    """Parse saved_at into a timezone-normalised pandas timestamp."""
    if value is None or pd.isna(value):
        return None

    try:
        ts = pd.to_datetime(value, utc=True)
    except Exception:
        return None

    if pd.isna(ts):
        return None

    return ts


def _normalise_price_index(prices: pd.DataFrame) -> pd.DataFrame:
    """Return prices with a timezone-aware UTC DatetimeIndex where possible."""
    if prices is None or prices.empty:
        return pd.DataFrame()

    frame = prices.copy()

    if not isinstance(frame.index, pd.DatetimeIndex):
        try:
            frame.index = pd.to_datetime(frame.index, utc=True)
        except Exception:
            return frame

    if frame.index.tz is None:
        frame.index = frame.index.tz_localize("UTC")
    else:
        frame.index = frame.index.tz_convert("UTC")

    return frame.sort_index()


def _find_entry_position(prices: pd.DataFrame, saved_at: pd.Timestamp | None) -> int | None:
    """Find the first daily market bar on or after the saved scan date.

    Daily Yahoo bars are stored at midnight. Saved scans usually happen during
    the day. Comparing exact timestamps would incorrectly skip the same-day bar,
    so this anchors by calendar date.
    """
    if prices is None or prices.empty:
        return None

    if saved_at is None:
        return len(prices) - 1

    saved_date = saved_at.normalize()
    price_dates = prices.index.normalize()

    matches = price_dates >= saved_date

    if not matches.any():
        # The scan is newer than the latest available daily bar.
        return len(prices) - 1

    return int(matches.argmax())


def calculate_forward_returns(
    scan_frame: pd.DataFrame,
    price_map: dict[str, pd.DataFrame],
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Calculate forward returns from the saved scan date.

    Anchors to the saved scan calendar date, finds the first available daily bar
    on or after that date, then calculates forward returns from that anchor.

    Incomplete windows are marked as PENDING.
    """
    if scan_frame is None or scan_frame.empty:
        return pd.DataFrame()

    windows = windows or FORWARD_WINDOWS
    rows: list[dict] = []

    for _, signal_row in scan_frame.iterrows():
        ticker = str(signal_row.get("ticker", "")).upper().strip()
        if not ticker:
            continue

        prices = _normalise_price_index(price_map.get(ticker, pd.DataFrame()))

        if prices.empty or "Close" not in prices.columns:
            continue

        saved_at = _parse_saved_at(signal_row.get("saved_at"))
        entry_pos = _find_entry_position(prices, saved_at)

        if entry_pos is None:
            continue

        saved_entry_price = float(signal_row.get("close", 0) or 0)
        anchored_entry_price = float(prices["Close"].iloc[entry_pos])

        if anchored_entry_price <= 0:
            continue

        output = signal_row.to_dict()
        output["saved_entry_price"] = round(saved_entry_price, 2)
        output["entry_price"] = round(anchored_entry_price, 2)
        output["entry_date"] = prices.index[entry_pos].isoformat()
        output["latest_price"] = round(float(prices["Close"].iloc[-1]), 2)
        output["validation_status"] = "READY"

        valid_returns = []

        for window in windows:
            return_col = f"return_{window}d_pct"
            win_col = f"win_{window}d"
            status_col = f"status_{window}d"

            future_pos = entry_pos + window

            if future_pos >= len(prices):
                output[return_col] = None
                output[win_col] = None
                output[status_col] = "PENDING"
                continue

            future_price = float(prices["Close"].iloc[future_pos])
            forward_return = ((future_price / anchored_entry_price) - 1) * 100

            output[return_col] = round(forward_return, 2)
            output[win_col] = bool(forward_return > 0)
            output[status_col] = "COMPLETE"
            valid_returns.append(forward_return)

        if valid_returns:
            output["avg_forward_return_pct"] = round(sum(valid_returns) / len(valid_returns), 2)
        else:
            output["avg_forward_return_pct"] = None
            output["validation_status"] = "PENDING"

        rows.append(output)

    return pd.DataFrame(rows)


def summarise_validation(validation_frame: pd.DataFrame) -> pd.DataFrame:
    """Summarise validation performance by signal."""
    if validation_frame is None or validation_frame.empty:
        return pd.DataFrame(
            columns=[
                "signal",
                "count",
                "complete_1d",
                "avg_1d_return",
                "win_rate_1d",
                "complete_5d",
                "avg_5d_return",
                "win_rate_5d",
                "complete_10d",
                "avg_10d_return",
                "win_rate_10d",
                "complete_20d",
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
            status_col = f"status_{window}d"
            complete_col = f"complete_{window}d"
            avg_col = f"avg_{window}d_return"
            rate_col = f"win_rate_{window}d"

            if status_col in group:
                complete = group[group[status_col] == "COMPLETE"]
            else:
                complete = group

            row[complete_col] = len(complete)

            if return_col in complete:
                returns = pd.to_numeric(complete[return_col], errors="coerce").dropna()
                row[avg_col] = round(float(returns.mean()), 2) if not returns.empty else None
            else:
                row[avg_col] = None

            if win_col in complete:
                wins = complete[win_col].dropna()
                row[rate_col] = round(float(wins.mean() * 100), 1) if not wins.empty else None
            else:
                row[rate_col] = None

        rows.append(row)

    return pd.DataFrame(rows).sort_values("signal").reset_index(drop=True)


def validation_quality_label(row: pd.Series) -> str:
    """Assign a simple quality label based on completed 5D validation."""
    complete_5d = row.get("complete_5d", 0)
    avg_5d = row.get("avg_5d_return")
    win_5d = row.get("win_rate_5d")

    if complete_5d is None or complete_5d == 0 or pd.isna(avg_5d) or pd.isna(win_5d):
        return "PENDING"

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

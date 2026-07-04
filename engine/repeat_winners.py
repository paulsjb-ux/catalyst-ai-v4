from __future__ import annotations

import pandas as pd


def build_repeat_winners(scan_frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Find symbols repeatedly appearing as BUY or WATCH across saved scans."""
    rows: list[dict] = []

    for frame in scan_frames:
        if frame is None or frame.empty:
            continue

        required = {"ticker", "signal", "score"}
        if not required.issubset(set(frame.columns)):
            continue

        usable = frame[frame["signal"].isin(["BUY", "WATCH"])].copy()
        for _, row in usable.iterrows():
            rows.append(
                {
                    "ticker": row["ticker"],
                    "signal": row["signal"],
                    "score": float(row["score"]),
                    "close": float(row.get("close", 0) or 0),
                    "scan_id": row.get("scan_id", ""),
                    "saved_at": row.get("saved_at", ""),
                }
            )

    if not rows:
        return pd.DataFrame(columns=["ticker", "appearances", "buy_count", "watch_count", "avg_score", "latest_signal", "latest_close", "status"])

    history = pd.DataFrame(rows)

    grouped = history.groupby("ticker").agg(
        appearances=("ticker", "count"),
        buy_count=("signal", lambda values: int((values == "BUY").sum())),
        watch_count=("signal", lambda values: int((values == "WATCH").sum())),
        avg_score=("score", "mean"),
        latest_signal=("signal", "last"),
        latest_close=("close", "last"),
    ).reset_index()

    grouped["avg_score"] = grouped["avg_score"].round(1)
    grouped["latest_close"] = grouped["latest_close"].round(2)

    def classify(row: pd.Series) -> str:
        if row["buy_count"] >= 3 and row["avg_score"] >= 75:
            return "PRIORITY"
        if row["appearances"] >= 3:
            return "PROVEN"
        if row["appearances"] >= 2:
            return "EMERGING"
        return "NEW"

    grouped["status"] = grouped.apply(classify, axis=1)

    order = {"PRIORITY": 0, "PROVEN": 1, "EMERGING": 2, "NEW": 3}
    grouped["_order"] = grouped["status"].map(order).fillna(9)
    grouped = grouped.sort_values(["_order", "appearances", "avg_score"], ascending=[True, False, False])
    return grouped.drop(columns=["_order"]).reset_index(drop=True)

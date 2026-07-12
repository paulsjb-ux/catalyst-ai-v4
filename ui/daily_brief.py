import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_scan, compare_scans
from engine.daily_brief import build_daily_brief, daily_brief_to_markdown
from engine.repeat_winners import build_repeat_winners
from ui.components import empty_state, section_header, status_card


def _recent_scans(limit: int = 20) -> list[pd.DataFrame]:
    index = list_saved_scans()
    if index is None or index.empty:
        return []
    frames = []
    for scan_id in index["scan_id"].astype(str).head(limit):
        frame = load_scan(scan_id)
        if not frame.empty:
            frames.append(frame)
    return frames


def _latest_scan() -> pd.DataFrame:
    session = st.session_state.get("scan_results", pd.DataFrame())
    if session is not None and not session.empty:
        return session
    index = list_saved_scans()
    return pd.DataFrame() if index is None or index.empty else load_scan(str(index.iloc[0]["scan_id"]))


def _comparison(latest: pd.DataFrame) -> pd.DataFrame:
    session = st.session_state.get("scan_comparison", pd.DataFrame())
    if session is not None and not session.empty:
        return session
    index = list_saved_scans()
    if index is None or len(index) < 2:
        return pd.DataFrame()
    return compare_scans(latest, load_scan(str(index.iloc[1]["scan_id"])))


def render_daily_brief() -> None:
    section_header("Daily Intelligence Brief", "One morning decision page covering market, candidates, portfolio risk and validation.")

    scan = _latest_scan()
    brief = build_daily_brief(
        regime=st.session_state.get("market_regime"),
        scan_frame=scan,
        repeat_frame=build_repeat_winners(_recent_scans()),
        monitor_frame=st.session_state.get("portfolio_monitor", pd.DataFrame()),
        comparison_frame=_comparison(scan),
        validation_frame=st.session_state.get("validation_results", pd.DataFrame()),
    )
    st.session_state["daily_brief"] = brief

    regime = brief["regime"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Regime", regime.get("regime", "UNKNOWN"))
    c2.metric("Market Score", regime.get("market_score", 0))
    c3.metric("Adjustment", regime.get("regime_adjustment", 0))
    c4.metric("Risk Label", regime.get("risk_label", "UNKNOWN"))
    status_card(regime.get("reason", "Run Market Scan to refresh context."), "warning" if regime.get("regime") in {"RISK_OFF", "DEFENSIVE"} else "info")

    st.markdown("### What Matters Today")
    for item in brief["priorities"]:
        message = f"**{item['title']}** — {item['detail']}"
        st.error(message) if item["level"] == "HIGH" else st.warning(message) if item["level"] == "MEDIUM" else st.info(message)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BUY Candidates", len(brief["top_buys"]))
    c2.metric("Repeat Winners", len(brief["repeat_winners"]))
    c3.metric("Portfolio Alerts", len(brief["portfolio_alerts"]))
    c4.metric("Signal Changes", len(brief["signal_changes"]))

    sections = [
        ("Top BUY Candidates", "top_buys", "No BUY candidates found."),
        ("Strongest Repeat Winners", "repeat_winners", "No repeat-winner evidence yet."),
        ("Portfolio Alerts", "portfolio_alerts", "No portfolio alerts."),
        ("Near Target", "near_target", "No positions within 5% of target."),
        ("Near Stop", "near_stop", "No positions within 5% of stop."),
        ("Signal Changes", "signal_changes", "No signal changes."),
        ("Validation Updates", "validation_updates", "No completed validation updates."),
    ]
    for title, key, empty in sections:
        st.markdown(f"### {title}")
        frame = brief[key]
        st.caption(empty) if frame is None or frame.empty else st.dataframe(frame, width="stretch", hide_index=True)

    st.download_button("Download daily intelligence brief", daily_brief_to_markdown(brief).encode("utf-8"), file_name="catalyst_daily_intelligence_brief.md", mime="text/markdown", width="stretch")

    if scan.empty:
        empty_state("No saved scan available", "Run Market Scan to populate the daily brief.", "🗞️")

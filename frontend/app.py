import streamlit as st
import pandas as pd
import traceback
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.stock_data import EURO_STOCKS
from backend.daily_predictor import (
    run_morning_predictions,
    update_actual_results,
    get_todays_predictions,
    get_prediction_history,
)
from backend.backtest import run_learning_backtest
from backend.db import load_predictions, get_accuracy_stats, get_all_mistakes

# ──────────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────────
st.set_page_config(page_title="EuroStock AI Predictor", layout="wide", page_icon="🇪🇺")

# ──────────────────────────────────────────────
# Global Styling
# ──────────────────────────────────────────────
st.markdown("""
<style>
    .bullish-badge {
        background-color: #4CAF50;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .bearish-badge {
        background-color: #F44336;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .correct-badge {
        background-color: #388E3C;
        color: white;
        padding: 3px 10px;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .wrong-badge {
        background-color: #C62828;
        color: white;
        padding: 3px 10px;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.82rem;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
st.markdown("# 🇪🇺 EuroStock AI Predictor")
st.caption(f"AI-powered daily stock predictions for Europe's top 20 blue-chip companies  •  {datetime.now().strftime('%A, %B %d, %Y')}")
st.divider()

# ──────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────
tab_user, tab_admin, tab_telemetry = st.tabs(["👤 User Dashboard", "🔧 Admin Dashboard", "🔮 Predictive Telemetry UI"])


# ══════════════════════════════════════════════
# TAB 1: USER DASHBOARD
# ══════════════════════════════════════════════
with tab_user:

    # ──────────────────────────────────────────
    # Section 1: Today's AI Predictions
    # ──────────────────────────────────────────
    st.header("🔮 Today's AI Predictions")

    if st.button("🔮 Get Today's Predictions", type="primary", use_container_width=True):
        try:
            with st.spinner("Running AI predictions for all 20 European stocks… this may take a few minutes ⏳"):
                stocks_list = list(EURO_STOCKS.items())
                results = run_morning_predictions(stocks_list)
                st.session_state["today_predictions"] = results
            st.success(f"✅ Predictions generated for {len(results)} stocks!")
        except Exception as e:
            st.error(f"❌ Error running predictions: {e}")
            st.code(traceback.format_exc())

    # Display predictions if available
    if "today_predictions" in st.session_state and st.session_state["today_predictions"]:
        predictions = st.session_state["today_predictions"]

        # Split into bullish and bearish
        bullish = []
        bearish = []
        for p in predictions:
            sentiment = str(p.get("sentiment", "")).lower()
            prediction = str(p.get("prediction", "")).lower()
            if sentiment == "bullish" or prediction == "up":
                bullish.append(p)
            else:
                bearish.append(p)

        # Sort each group by confidence (descending)
        def _get_confidence(item):
            try:
                return float(item.get("confidence", 50))
            except (ValueError, TypeError):
                return 50.0

        bullish.sort(key=_get_confidence, reverse=True)
        bearish.sort(key=_get_confidence, reverse=True)

        col_bull, col_bear = st.columns(2)

        with col_bull:
            st.subheader("🟢 Top Bullish Picks")
            if not bullish:
                st.info("No bullish predictions today.")
            for rank, item in enumerate(bullish, 1):
                with st.container(border=True):
                    company = item.get("company", "Unknown")
                    ticker = item.get("ticker", "")
                    confidence = _get_confidence(item)
                    reasoning = item.get("reasoning", "No reasoning provided.")

                    st.markdown(
                        f"**#{rank}** &nbsp; **{company}** ({ticker}) &nbsp; "
                        f"<span class='bullish-badge'>🟢 BULLISH</span>",
                        unsafe_allow_html=True,
                    )
                    st.progress(min(confidence / 100.0, 1.0), text=f"Confidence: {confidence:.0f}%")
                    st.caption(reasoning[:200] if len(reasoning) > 200 else reasoning)

        with col_bear:
            st.subheader("🔴 Bearish Warnings")
            if not bearish:
                st.info("No bearish predictions today.")
            for rank, item in enumerate(bearish, 1):
                with st.container(border=True):
                    company = item.get("company", "Unknown")
                    ticker = item.get("ticker", "")
                    confidence = _get_confidence(item)
                    reasoning = item.get("reasoning", "No reasoning provided.")

                    st.markdown(
                        f"**#{rank}** &nbsp; **{company}** ({ticker}) &nbsp; "
                        f"<span class='bearish-badge'>🔴 BEARISH</span>",
                        unsafe_allow_html=True,
                    )
                    st.progress(min(confidence / 100.0, 1.0), text=f"Confidence: {confidence:.0f}%")
                    st.caption(reasoning[:200] if len(reasoning) > 200 else reasoning)

    st.divider()

    # ──────────────────────────────────────────
    # Section 2: Prediction History
    # ──────────────────────────────────────────
    st.header("📅 Prediction History")

    if st.button("🔄 Update Today's Actual Results", use_container_width=True):
        try:
            with st.spinner("Fetching actual market results and comparing to predictions…"):
                update_actual_results()
            st.success("✅ Actual results updated! Scroll down to see accuracy.")
        except Exception as e:
            st.error(f"❌ Error updating results: {e}")
            st.code(traceback.format_exc())

    try:
        history = get_prediction_history(30)

        if history and len(history) > 0:
            # Group predictions by date
            date_groups = {}
            for entry in history:
                date_key = str(entry.get("date", "Unknown"))
                if date_key not in date_groups:
                    date_groups[date_key] = []
                date_groups[date_key].append(entry)

            for date_key in sorted(date_groups.keys(), reverse=True):
                entries = date_groups[date_key]

                # Calculate accuracy for the day
                total = len(entries)
                correct = sum(1 for e in entries if e.get("correct", False))
                accuracy = (correct / total * 100) if total > 0 else 0
                icon = "🟢" if accuracy >= 60 else ("🟡" if accuracy >= 40 else "🔴")

                with st.expander(f"{icon} **{date_key}** — Accuracy: {accuracy:.0f}% ({correct}/{total} correct)"):
                    for entry in entries:
                        company = entry.get("company", "Unknown")
                        predicted = entry.get("prediction", "N/A")
                        actual = entry.get("actual", "N/A")
                        is_correct = entry.get("correct", False)
                        news = entry.get("news", "")

                        result_icon = "✅" if is_correct else "❌"
                        pred_color = "🟢" if predicted == "Up" else "🔴"
                        act_color = "🟢" if actual == "Up" else "🔴"

                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.markdown(
                                f"{result_icon} **{company}** — "
                                f"Predicted: {pred_color} {predicted} vs Actual: {act_color} {actual}"
                            )
                        with col_b:
                            if news:
                                with st.popover("📰 News Context"):
                                    st.markdown(news[:500] if len(str(news)) > 500 else str(news))
        else:
            st.info("📭 No prediction history available yet. Run predictions and update results to build history.")
    except Exception as e:
        st.error(f"❌ Error loading prediction history: {e}")
        st.code(traceback.format_exc())


# ══════════════════════════════════════════════
# TAB 2: ADMIN DASHBOARD
# ══════════════════════════════════════════════
with tab_admin:

    # ──────────────────────────────────────────
    # Section 1: Phase 1 Backtesting
    # ──────────────────────────────────────────
    st.header("🧪 Phase 1: Self-Learning Backtest")

    bt_col1, bt_col2, bt_col3 = st.columns(3)
    with bt_col1:
        stock_a = st.selectbox("📈 Stock A", list(EURO_STOCKS.keys()), index=0, key="bt_stock_a")
    with bt_col2:
        stock_b = st.selectbox("📈 Stock B", list(EURO_STOCKS.keys()), index=1, key="bt_stock_b")
    with bt_col3:
        backtest_days = st.slider("📅 Backtest Days", min_value=5, max_value=30, value=10, key="bt_days")

    if st.button("🚀 Run Backtest Engine", type="primary", use_container_width=True):
        stocks_to_test = [
            (stock_a, EURO_STOCKS[stock_a]),
            (stock_b, EURO_STOCKS[stock_b]),
        ]
        progress_bar = st.progress(0)
        status_text = st.empty()

        def _progress_cb(current, total, msg):
            progress_bar.progress(current / total)
            status_text.info(f"[{current}/{total}] {msg}")

        try:
            with st.spinner("Running self-learning backtest…"):
                bt_df, bt_mistakes = run_learning_backtest(
                    stocks_to_test, days=backtest_days, progress_callback=_progress_cb
                )
                progress_bar.progress(1.0)
                status_text.success("✅ Backtest complete!")
                st.session_state["bt_results_df"] = bt_df
                st.session_state["bt_mistake_log"] = bt_mistakes
        except Exception as e:
            st.error(f"❌ Backtest failed: {e}")
            st.code(traceback.format_exc())

    # Display backtest results
    if "bt_results_df" in st.session_state and not st.session_state["bt_results_df"].empty:
        bt_df = st.session_state["bt_results_df"]

        st.subheader("📊 Full Results Table")
        st.dataframe(bt_df, use_container_width=True, height=400)

        # Accuracy over time chart (matplotlib)
        st.subheader("📈 Cumulative Accuracy Over Time")
        try:
            bt_df_valid = bt_df[bt_df["AI Prediction"].isin(["Up", "Down"])].copy()
            bt_df_valid["Correct_Int"] = bt_df_valid["Correct?"].astype(int)

            daily_agg = (
                bt_df_valid.groupby("Date")
                .agg(Correct=("Correct_Int", "sum"), Total=("Correct_Int", "count"))
                .reset_index()
            )
            daily_agg["Cumulative Correct"] = daily_agg["Correct"].cumsum()
            daily_agg["Cumulative Total"] = daily_agg["Total"].cumsum()
            daily_agg["Cumulative Accuracy %"] = (
                daily_agg["Cumulative Correct"] / daily_agg["Cumulative Total"] * 100
            )

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(
                daily_agg["Date"],
                daily_agg["Cumulative Accuracy %"],
                marker="o",
                linewidth=2,
                color="#4CAF50",
                label="Cumulative Accuracy",
            )
            ax.axhline(y=50, color="#F44336", linestyle="--", linewidth=1.5, label="50% Baseline (Random)")
            ax.set_xlabel("Date")
            ax.set_ylabel("Accuracy (%)")
            ax.set_title("Self-Learning Backtest: Cumulative Accuracy Trajectory")
            ax.set_ylim(0, 105)
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        except Exception as e:
            st.error(f"❌ Error generating accuracy chart: {e}")
            st.code(traceback.format_exc())

    st.divider()

    # ──────────────────────────────────────────
    # Section 2: Overall Analytics
    # ──────────────────────────────────────────
    st.header("📊 Overall Analytics")

    try:
        stats = get_accuracy_stats()

        if stats:
            total = stats.get("total", 0)
            correct = stats.get("correct", 0)
            wrong = stats.get("wrong", total - correct)
            accuracy = stats.get("accuracy_pct", (correct / total * 100) if total > 0 else 0)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📋 Total Predictions", total)
            m2.metric("✅ Correct", correct)
            m3.metric("❌ Wrong", wrong)
            m4.metric("🎯 Accuracy", f"{accuracy:.1f}%")

            # Per-stock accuracy bar chart
            per_stock = stats.get("by_stock", {})
            if per_stock:
                st.subheader("📊 Per-Stock Accuracy")
                companies = list(per_stock.keys())
                accuracies = [per_stock[c].get("accuracy_pct", 0) for c in companies]

                fig, ax = plt.subplots(figsize=(10, max(5, len(companies) * 0.4)))
                colors = ["#4CAF50" if a >= 50 else "#F44336" for a in accuracies]
                bars = ax.barh(companies, accuracies, color=colors, edgecolor="white", linewidth=0.5)
                ax.axvline(x=50, color="#FFC107", linestyle="--", linewidth=1.5, label="50% Baseline")
                ax.set_xlabel("Accuracy (%)")
                ax.set_title("Prediction Accuracy by Stock")
                ax.set_xlim(0, 105)
                ax.legend()
                ax.grid(True, axis="x", alpha=0.3)

                # Add percentage labels on bars
                for bar, acc in zip(bars, accuracies):
                    ax.text(
                        bar.get_width() + 1,
                        bar.get_y() + bar.get_height() / 2,
                        f"{acc:.0f}%",
                        va="center",
                        fontsize=9,
                        fontweight="bold",
                    )

                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)
        else:
            st.info("📭 No accuracy stats available yet. Run predictions first to generate data.")
    except Exception as e:
        st.error(f"❌ Error loading analytics: {e}")
        st.code(traceback.format_exc())

    st.divider()

    # ──────────────────────────────────────────
    # Section 3: Mistake Log
    # ──────────────────────────────────────────
    st.header("📝 Mistake Log")

    try:
        mistakes = get_all_mistakes()

        if mistakes and len(mistakes) > 0:
            st.markdown(f"**{len(mistakes)} mistakes** recorded — each one feeds back into future AI prompts for self-correction.")
            for idx, m in enumerate(mistakes, 1):
                date = m.get("date", "Unknown")
                company = m.get("company", "Unknown")
                predicted = m.get("predicted", "N/A")
                actual = m.get("actual", "N/A")
                reasoning = m.get("reasoning", "N/A")
                news_summary = m.get("news_summary", "")

                pred_icon = "🟢" if predicted == "Up" else "🔴"
                act_icon = "🟢" if actual == "Up" else "🔴"

                with st.expander(f"⚠️ Mistake #{idx}: {date} — {company}"):
                    col_left, col_right = st.columns(2)
                    with col_left:
                        st.markdown(f"**📅 Date:** {date}")
                        st.markdown(f"**🏢 Company:** {company}")
                    with col_right:
                        st.markdown(f"**Predicted:** {pred_icon} {predicted}")
                        st.markdown(f"**Actual:** {act_icon} {actual}")

                    st.markdown("---")
                    st.markdown("**🤖 AI Reasoning (which was wrong):**")
                    st.warning(reasoning)

                    if news_summary:
                        st.markdown("**📰 News Summary:**")
                        st.caption(news_summary[:500] if len(str(news_summary)) > 500 else str(news_summary))
        else:
            st.success("🎉 No prediction mistakes recorded yet!")
    except Exception as e:
        st.error(f"❌ Error loading mistake log: {e}")
        st.code(traceback.format_exc())

    st.divider()

    # ──────────────────────────────────────────
    # Section 4: Self-Correction Timeline
    # ──────────────────────────────────────────
    st.header("🧠 Self-Correction Timeline")

    try:
        if "bt_results_df" in st.session_state and not st.session_state["bt_results_df"].empty:
            bt_df = st.session_state["bt_results_df"]

            # Filter entries where a lesson was applied
            lesson_rows = bt_df[
                (bt_df["Lesson Applied"].notna())
                & (bt_df["Lesson Applied"] != "N/A")
                & (bt_df["Lesson Applied"] != "None")
                & (bt_df["Lesson Applied"] != "")
            ]

            if not lesson_rows.empty:
                st.markdown(
                    f"**{len(lesson_rows)} predictions** where the AI applied a lesson from past mistakes:"
                )
                for _, row in lesson_rows.iterrows():
                    result_icon = "✅" if row.get("Correct?", False) else "❌"
                    with st.container(border=True):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(
                                f"**{row.get('Date', '')}** — **{row.get('Company', '')}** ({row.get('Ticker', '')})"
                            )
                            st.markdown(f"🧠 **Lesson Applied:** {row['Lesson Applied']}")
                        with c2:
                            pred = row.get("AI Prediction", "N/A")
                            actual = row.get("Actual Trend", "N/A")
                            st.markdown(
                                f"{result_icon} Predicted: {'🟢' if pred == 'Up' else '🔴'} {pred} "
                                f"→ Actual: {'🟢' if actual == 'Up' else '🔴'} {actual}"
                            )
            else:
                st.info("📭 No self-correction entries found in the current backtest results. Lessons are applied when the AI encounters similar patterns to past mistakes.")
        else:
            st.info("📭 Run a backtest first (above) to see the self-correction timeline.")
    except Exception as e:
        st.error(f"❌ Error loading self-correction timeline: {e}")
        st.code(traceback.format_exc())

# ══════════════════════════════════════════════
# TAB 3: TELEMETRY DASHBOARD
# ══════════════════════════════════════════════
with tab_telemetry:
    st.header("🔮 Predictive Telemetry UI")
    st.caption("A high-fidelity mockup dashboard generated for advanced understanding of the predictive engine telemetry and model factors.")
    
    html_file = os.path.join(os.path.dirname(__file__), "stitch_dashboard.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        import streamlit.components.v2 as components
        # Wrap the dashboard in a component to isolate its Tailwind CSS from the rest of the app.
        _dashboard_comp = components.component("stitch_dashboard", html=html_content)
        _dashboard_comp()
    else:
        st.warning("Telemetry HTML not found.")


# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.divider()
st.caption("🇪🇺 EuroStock AI Predictor  •  Powered by Streamlit, Yahoo Finance, Serper News, & OpenRouter AI")

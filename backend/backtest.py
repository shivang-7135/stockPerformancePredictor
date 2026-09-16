import time
import pandas as pd
from backend.stock_data import EURO_STOCKS, get_historical_data, get_performance_summary
from backend.news_fetcher import get_recent_news, get_news_for_date
from backend.ai_analyzer import analyze_stock_sentiment, analyze_with_learning


def _safe_date(date_obj):
    """Extract a clean date object and string from a potentially wrapped pandas value."""
    if isinstance(date_obj, pd.Series):
        date_obj = date_obj.iloc[0]
    if hasattr(date_obj, 'strftime'):
        return date_obj, date_obj.strftime('%Y-%m-%d')
    return date_obj, str(date_obj).split(' ')[0]


def _safe_float(val):
    """Extract a float from a potentially wrapped pandas value."""
    if isinstance(val, pd.Series):
        return float(val.iloc[0])
    return float(val)


# ─────────────────────────────────────────────────
# SELF-LEARNING BACKTEST (The new core engine)
# ─────────────────────────────────────────────────
def run_learning_backtest(stocks: list, days: int = 30, progress_callback=None):
    """
    Runs a day-by-day self-learning backtest across multiple stocks.
    
    For each trading day (oldest to newest):
      1. Fetch news for that day for each stock.
      2. Feed the AI the news + its accumulated mistake log.
      3. Compare prediction to actual open→close movement.
      4. If wrong, add the mistake to the log so the next day's prompt is smarter.
    
    Args:
        stocks: list of (company_name, ticker) tuples (e.g. 2 stocks)
        days: how many calendar days of history to fetch
        progress_callback: optional callable(current_step, total_steps, message)
    
    Returns:
        results_df: DataFrame with every day × every stock
        mistake_log: the accumulated mistake log (for inspection)
    """
    # Gather stock data for all tickers
    all_data = {}
    for company, ticker in stocks:
        df = get_historical_data(ticker, days=days)
        if not df.empty:
            all_data[company] = {"ticker": ticker, "df": df}

    if not all_data:
        return pd.DataFrame(), []

    # Determine the date column
    sample_df = list(all_data.values())[0]["df"]
    date_col = 'Date' if 'Date' in sample_df.columns else 'Datetime'

    # Get the union of all trading dates (sorted oldest → newest)
    all_dates = set()
    for info in all_data.values():
        for i in range(len(info["df"])):
            _, ds = _safe_date(info["df"].iloc[i][date_col])
            all_dates.add(ds)
    all_dates = sorted(all_dates)

    total_steps = len(all_dates) * len(all_data)
    current_step = 0

    # The self-correcting mistake log (shared across all stocks)
    mistake_log = []
    results = []

    for date_str in all_dates:
        for company, info in all_data.items():
            ticker = info["ticker"]
            df = info["df"]

            # Find the row for this date
            matching_rows = []
            for i in range(len(df)):
                _, ds = _safe_date(df.iloc[i][date_col])
                if ds == date_str:
                    matching_rows.append(df.iloc[i])
                    break

            if not matching_rows:
                continue  # this stock didn't trade on this day

            row = matching_rows[0]
            date_obj, date_str_clean = _safe_date(row[date_col])

            open_price = _safe_float(row['Open'])
            close_price = _safe_float(row['Close'])
            high_price = _safe_float(row['High'])
            low_price = _safe_float(row['Low'])
            pct_change = ((close_price - open_price) / open_price) * 100
            actual_trend = "Up" if pct_change > 0 else "Down"

            # 1. Fetch news for this specific day
            news = get_news_for_date(company, date_obj)

            # 2. AI prediction WITH learning from past mistakes
            ai_result = analyze_with_learning(company, date_str_clean, news, mistake_log)
            ai_prediction = ai_result.get("prediction", "Unknown")
            is_correct = (ai_prediction == actual_trend)

            # 3. If wrong, add to mistake log so next prediction is smarter
            if not is_correct and ai_prediction in ("Up", "Down"):
                mistake_log.append({
                    "date": date_str_clean,
                    "company": company,
                    "predicted": ai_prediction,
                    "actual": actual_trend,
                    "news_summary": news[:300],
                    "reasoning": ai_result.get("reasoning", "N/A")
                })

            current_step += 1
            if progress_callback:
                progress_callback(
                    current_step, total_steps,
                    f"Day {date_str_clean} | {company}: Predicted {ai_prediction}, Actual {actual_trend}"
                )

            results.append({
                "Date": date_str_clean,
                "Company": company,
                "Ticker": ticker,
                "Open": round(open_price, 2),
                "Close": round(close_price, 2),
                "High": round(high_price, 2),
                "Low": round(low_price, 2),
                "% Change": round(pct_change, 2),
                "Actual Trend": actual_trend,
                "AI Sentiment": ai_result.get("sentiment", "N/A"),
                "AI Prediction": ai_prediction,
                "Confidence": ai_result.get("confidence", "N/A"),
                "Correct?": is_correct,
                "AI Reasoning": ai_result.get("reasoning", "N/A"),
                "Lesson Applied": ai_result.get("lesson_applied", "N/A"),
                "News": news,
                "Mistakes So Far": len(mistake_log)
            })
            time.sleep(1)  # rate limit

    return pd.DataFrame(results), mistake_log


# ─────────────────────────────────────────────────
# LEGACY: Quick overview backtest (kept for the top section)
# ─────────────────────────────────────────────────
def run_backtest_for_stock(company_name: str, ticker: str):
    stock_df = get_historical_data(ticker, days=30)
    actual_perf = get_performance_summary(stock_df)
    if not actual_perf:
        return {"Company": company_name, "Error": "Failed to fetch stock data."}
    actual_trend = "Up" if actual_perf["percent_change"] > 0 else "Down"
    news = get_recent_news(company_name)
    ai_result = analyze_stock_sentiment(company_name, news)
    ai_prediction = ai_result.get("prediction", "Unknown")
    is_correct = (ai_prediction == actual_trend)
    return {
        "Company": company_name,
        "Ticker": ticker,
        "Period": f"{actual_perf.get('start_date', 'Unknown')} to {actual_perf.get('end_date', 'Unknown')}",
        "Start Price": round(actual_perf["start_price"], 2),
        "End Price": round(actual_perf["end_price"], 2),
        "% Change": round(actual_perf["percent_change"], 2),
        "Actual Trend": actual_trend,
        "AI Sentiment": ai_result.get("sentiment", "N/A"),
        "AI Prediction": ai_prediction,
        "Prediction Correct?": is_correct,
        "AI Reasoning": ai_result.get("reasoning", "N/A")
    }


def run_full_backtest(limit=5):
    results = []
    stocks_to_test = list(EURO_STOCKS.items())[:limit]
    for company, ticker in stocks_to_test:
        print(f"Processing {company} ({ticker})...")
        res = run_backtest_for_stock(company, ticker)
        results.append(res)
        time.sleep(1)
    return pd.DataFrame(results)


if __name__ == "__main__":
    # Quick test: 2 stocks, 7 days
    stocks = [("SAP", "SAP"), ("ASML Holding", "ASML")]
    df, mistakes = run_learning_backtest(stocks, days=7)
    print(df.to_string())
    print(f"\nTotal mistakes: {len(mistakes)}")

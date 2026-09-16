"""
Phase 2 live prediction engine for EuroStock AI Predictor.
Handles morning predictions, end-of-day result updates, and prediction history.
"""

import json
from datetime import datetime, timedelta

from backend.stock_data import EURO_STOCKS, get_historical_data
from backend.news_fetcher import get_recent_news
from backend.ai_analyzer import analyze_with_learning
from backend.db import (
    load_predictions,
    save_predictions,
    add_prediction,
    get_predictions_by_date,
    get_all_mistakes,
)


def run_morning_predictions(stocks: list = None) -> list:
    """
    Runs the morning prediction for all 20 stocks (or a subset).

    1. Fetches today's morning news for each stock via get_recent_news()
    2. Loads past mistakes from db
    3. Calls analyze_with_learning() for each stock
    4. Ranks them by confidence (highest first)
    5. Saves predictions to db
    6. Returns the list of prediction dicts sorted by confidence desc

    Args:
        stocks: Optional list of company names to predict. Defaults to all
                stocks in EURO_STOCKS.

    Returns:
        List of prediction dicts sorted by confidence descending.
    """
    today_str = datetime.today().strftime("%Y-%m-%d")

    if stocks is None:
        stocks_to_predict = list(EURO_STOCKS.keys())
    else:
        # Accept both list of strings and list of (name, ticker) tuples
        stocks_to_predict = []
        for s in stocks:
            if isinstance(s, (list, tuple)):
                stocks_to_predict.append(s[0])  # take the company name
            else:
                stocks_to_predict.append(s)

    # Load past mistakes for the learning model
    mistakes = get_all_mistakes()

    predictions = []

    for company_name in stocks_to_predict:
        ticker = EURO_STOCKS.get(company_name)
        if ticker is None:
            continue

        # Fetch today's morning news
        try:
            news_text = get_recent_news(company_name)
        except Exception:
            news_text = "No news available."

        if not news_text:
            news_text = "No news available."

        # Run AI analysis with learning from past mistakes
        try:
            result = analyze_with_learning(
                company_name, today_str, news_text, mistakes
            )
            if isinstance(result, str):
                result = json.loads(result)
        except Exception:
            result = {
                "sentiment": "Neutral",
                "prediction": "Up",
                "confidence": 50,
                "reasoning": "Analysis unavailable.",
                "lesson_applied": "None",
            }

        entry = {
            "date": today_str,
            "company": company_name,
            "ticker": ticker,
            "sentiment": result.get("sentiment", "Neutral"),
            "prediction": result.get("prediction", "Up"),
            "confidence": result.get("confidence", 50),
            "reasoning": result.get("reasoning", ""),
            "lesson_applied": result.get("lesson_applied", ""),
            "news": news_text[:2000],  # Truncate to keep db manageable
            "open_price": None,
            "close_price": None,
            "actual_trend": None,
            "pct_change": None,
            "correct": None,
            "phase": "live",
        }

        add_prediction(entry)
        predictions.append(entry)

    # Sort by confidence descending
    predictions.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return predictions


def update_actual_results(date_str: str = None):
    """
    Called at end of day. For each prediction on date_str (defaults to today):

    1. Fetches actual stock data from yfinance for that day
    2. Calculates open->close change
    3. Updates the prediction entry with actual_trend, pct_change, correct
    4. Saves back to db

    Args:
        date_str: Date string in 'YYYY-MM-DD' format. Defaults to today.
    """
    if date_str is None:
        date_str = datetime.today().strftime("%Y-%m-%d")

    all_predictions = load_predictions()
    updated = False

    for entry in all_predictions:
        if entry.get("date") != date_str:
            continue
        if entry.get("correct") is not None:
            # Already evaluated
            continue

        ticker = entry.get("ticker")
        if not ticker:
            continue

        # Fetch 5 days of data to ensure we capture the target date
        try:
            data = get_historical_data(ticker, days=5)
        except Exception:
            continue

        if data is None or data.empty:
            continue

        # Find the row for the target date
        # get_historical_data calls reset_index, so Date is a column
        import pandas as pd
        target_row = None
        date_col = 'Date' if 'Date' in data.columns else 'Datetime'
        
        for i in range(len(data)):
            row = data.iloc[i]
            date_val = row[date_col]
            if isinstance(date_val, pd.Series):
                date_val = date_val.iloc[0]
            if hasattr(date_val, 'strftime'):
                row_date = date_val.strftime("%Y-%m-%d")
            else:
                row_date = str(date_val)[:10]
            if row_date == date_str:
                target_row = row
                break

        if target_row is None:
            continue

        try:
            open_val = target_row["Open"]
            close_val = target_row["Close"]
            if isinstance(open_val, pd.Series):
                open_val = open_val.iloc[0]
            if isinstance(close_val, pd.Series):
                close_val = close_val.iloc[0]
            open_price = float(open_val)
            close_price = float(close_val)
        except (KeyError, TypeError, ValueError):
            continue

        pct_change = round(((close_price - open_price) / open_price) * 100, 4)
        actual_trend = "Up" if close_price >= open_price else "Down"
        correct = entry.get("prediction") == actual_trend

        entry["open_price"] = round(open_price, 4)
        entry["close_price"] = round(close_price, 4)
        entry["actual_trend"] = actual_trend
        entry["pct_change"] = pct_change
        entry["correct"] = correct
        updated = True

    if updated:
        save_predictions(all_predictions)


def get_todays_predictions() -> list:
    """Returns today's predictions from db, sorted by confidence desc."""
    today_str = datetime.today().strftime("%Y-%m-%d")
    predictions = get_predictions_by_date(today_str)
    predictions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return predictions


def get_prediction_history(days: int = 30) -> list:
    """
    Returns all predictions from the last N days.

    Args:
        days: Number of days to look back. Defaults to 30.

    Returns:
        List of prediction dicts from the last N days, newest first.
    """
    cutoff = datetime.today() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    all_predictions = load_predictions()
    recent = [p for p in all_predictions if p.get("date", "") >= cutoff_str]
    recent.sort(key=lambda x: x.get("date", ""), reverse=True)
    return recent

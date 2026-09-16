"""
Simple JSON-file-based database for storing daily predictions and results.
Uses a single JSON file at backend/data/predictions.json.
"""

import json
import os


def _get_db_path() -> str:
    """Returns path to predictions.json, creates data/ dir if needed."""
    db_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "predictions.json")


def load_predictions() -> list:
    """Loads the full list of prediction entries from JSON file."""
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        return []
    with open(db_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []
    return data


def save_predictions(predictions: list):
    """Saves the full list of prediction entries to JSON file."""
    db_path = _get_db_path()
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=2, ensure_ascii=False)


def add_prediction(entry: dict):
    """Appends a single prediction entry and saves."""
    predictions = load_predictions()
    predictions.append(entry)
    save_predictions(predictions)


def get_predictions_by_date(date_str: str) -> list:
    """Filter predictions by date string (e.g. '2026-09-14')."""
    predictions = load_predictions()
    return [p for p in predictions if p.get("date") == date_str]


def get_all_mistakes() -> list:
    """Returns entries where correct == False."""
    predictions = load_predictions()
    return [p for p in predictions if p.get("correct") is False]


def get_accuracy_stats() -> dict:
    """
    Returns accuracy statistics across all evaluated predictions.

    Returns:
        {
            "total": int,
            "correct": int,
            "wrong": int,
            "accuracy_pct": float,
            "by_stock": {
                company_name: {
                    "total": int,
                    "correct": int,
                    "accuracy_pct": float
                }
            }
        }
    """
    predictions = load_predictions()

    # Only consider predictions that have been evaluated
    evaluated = [p for p in predictions if p.get("correct") is not None]

    total = len(evaluated)
    correct = sum(1 for p in evaluated if p["correct"] is True)
    wrong = total - correct
    accuracy_pct = round((correct / total) * 100, 2) if total > 0 else 0.0

    by_stock = {}
    for p in evaluated:
        company = p.get("company", "Unknown")
        if company not in by_stock:
            by_stock[company] = {"total": 0, "correct": 0, "accuracy_pct": 0.0}
        by_stock[company]["total"] += 1
        if p["correct"] is True:
            by_stock[company]["correct"] += 1

    for company, stats in by_stock.items():
        if stats["total"] > 0:
            stats["accuracy_pct"] = round(
                (stats["correct"] / stats["total"]) * 100, 2
            )

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "accuracy_pct": accuracy_pct,
        "by_stock": by_stock,
    }

import json
import os
from datetime import datetime

HISTORY_FILE = "meal_history.json"


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_meal(nutrition_result, recommendation_result, health_condition, score):
    history = load_history()

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "health_condition": health_condition,
        "nutrition_summary": nutrition_result[:300] if nutrition_result else "",
        "recommendation_summary": recommendation_result[:300] if recommendation_result else "",
        "score": score
    }

    history.append(entry)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def extract_score_from_result(recommendation_result):
    import re
    if not recommendation_result:
        return None
    match = re.search(r"(\d{1,3})\s*/\s*100", recommendation_result)
    if match:
        score = int(match.group(1))
        if 0 <= score <= 100:
            return score
    return None


def clear_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
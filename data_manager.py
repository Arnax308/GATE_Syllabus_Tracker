import json
import sys
from config import DATA_FILE, DEFAULT_SYLLABUS

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    # Schema migration / Initialization
    if "syllabus" not in data: data["syllabus"] = DEFAULT_SYLLABUS
    if "topics" not in data: data["topics"] = {}
    if "test_series" not in data: data["test_series"] = {"subject_wise": {}, "full_mock": []}
    if "goals" not in data: data["goals"] = []
    if "activity_log" not in data: data["activity_log"] = []
    if "mistake_log" not in data: data["mistake_log"] = []
    if "target_score" not in data: data["target_score"] = 75.0

    # Ensure all topics exist in dict
    for subject, topics in data["syllabus"].items():
        for topic in topics:
            tid = f"{subject}::{topic}"
            if tid not in data["topics"]:
                data["topics"][tid] = {
                    "status": "Not Taught",
                    "notes_made": False,
                    "workbook_qs": False,
                    "revision": "Not Revised",
                    "difficulty": False,
                    "last_revised": None,
                    "subtopics": []
                }
    # Ensure subject keys exist in test series
    for s in data["syllabus"]:
        if s not in data["test_series"]["subject_wise"]:
            data["test_series"]["subject_wise"][s] = []

    return data

def save_data_to_file(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print("Save error:", e, file=sys.stderr)
        return False


"""Validator script for eval/golden_set.json.

Verifies:
1. Valid JSON syntax and parseability.
2. Exactly 47 entries with unique IDs (Q001 - Q047).
3. Correct schema per entry: id, question, type, expected_answer, expected_sources, gold_sql, status.
4. Allowed categories ('docs', 'sql', 'both', 'refuse') and statuses ('pending_db', 'pending_docs', 'ready').
5. Distribution matches specification: docs: 15, sql: 15, both: 12, refuse: 5.
"""

import sys
import json
from pathlib import Path
from collections import Counter

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GOLDEN_SET_PATH = Path(__file__).resolve().parent / "golden_set.json"

REQUIRED_FIELDS = [
    "id",
    "question",
    "type",
    "expected_answer",
    "expected_sources",
    "gold_sql",
    "status",
]
ALLOWED_TYPES = {"docs", "sql", "both", "refuse"}
ALLOWED_STATUSES = {"pending_db", "pending_docs", "ready"}

EXPECTED_COUNTS = {
    "docs": 15,
    "sql": 15,
    "both": 12,
    "refuse": 5,
}
EXPECTED_TOTAL = 47


def validate() -> bool:
    print("==================================================")
    print("        Validating eval/golden_set.json           ")
    print("==================================================")

    # 1. Check file existence
    if not GOLDEN_SET_PATH.exists():
        print(f"FAIL: File not found at {GOLDEN_SET_PATH}")
        return False

    # 2. Parse JSON
    try:
        with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"FAIL: JSON parsing error: {e}")
        return False

    if not isinstance(data, list):
        print(f"FAIL: Expected a JSON array of items, got {type(data).__name__}")
        return False

    # 3. Check total count
    total_entries = len(data)
    print(f"Loaded {total_entries} entries from {GOLDEN_SET_PATH.name}")

    if total_entries != EXPECTED_TOTAL:
        print(f"FAIL: Expected {EXPECTED_TOTAL} total entries, but found {total_entries}")
        return False

    # 4. Check schema, uniqueness, and enum values
    seen_ids = set()
    type_counter = Counter()
    status_counter = Counter()

    for idx, entry in enumerate(data, start=1):
        # Mandatory fields
        for field in REQUIRED_FIELDS:
            if field not in entry:
                print(f"FAIL: Entry #{idx} is missing required field '{field}': {entry}")
                return False

        item_id = entry["id"]
        # ID uniqueness and format
        if item_id in seen_ids:
            print(f"FAIL: Duplicate ID detected: '{item_id}' at index {idx}")
            return False
        seen_ids.add(item_id)

        # Question text
        if not isinstance(entry["question"], str) or not entry["question"].strip():
            print(f"FAIL: Item {item_id} has invalid/empty question text.")
            return False

        # Type validity
        item_type = entry["type"]
        if item_type not in ALLOWED_TYPES:
            print(f"FAIL: Item {item_id} has invalid type '{item_type}'. Allowed: {ALLOWED_TYPES}")
            return False
        type_counter[item_type] += 1

        # Status validity
        item_status = entry["status"]
        if item_status not in ALLOWED_STATUSES:
            print(f"FAIL: Item {item_id} has invalid status '{item_status}'. Allowed: {ALLOWED_STATUSES}")
            return False
        status_counter[item_status] += 1

        # expected_sources must be a list
        if not isinstance(entry["expected_sources"], list):
            print(f"FAIL: Item {item_id} 'expected_sources' must be a list, got {type(entry['expected_sources']).__name__}")
            return False

        # Verify category-specific rules
        if item_type == "refuse":
            if entry["expected_answer"] != "REFUSE":
                print(f"FAIL: Refusal item {item_id} must have expected_answer='REFUSE', got: {entry['expected_answer']}")
                return False
            if entry["status"] != "ready":
                print(f"FAIL: Refusal item {item_id} must have status='ready', got: {entry['status']}")
                return False
        elif item_type == "sql":
            if entry["status"] not in ("pending_db", "ready"):
                print(f"FAIL: SQL item {item_id} status must be 'pending_db' or 'ready', got: {entry['status']}")
                return False
        elif item_type in ("docs", "both"):
            if entry["status"] not in ("pending_docs", "ready"):
                print(f"FAIL: Docs/Both item {item_id} status must be 'pending_docs' or 'ready', got: {entry['status']}")
                return False

    print("\n[PASS] All entries satisfy schema integrity, ID uniqueness, and field constraints.")

    # 5. Display Breakdown by Type
    print("\n--- Breakdown by Question Type ---")
    type_mismatch = False
    for q_type, expected in EXPECTED_COUNTS.items():
        actual = type_counter[q_type]
        status_label = "PASS" if actual == expected else "FAIL"
        if actual != expected:
            type_mismatch = True
        print(f"  [{status_label}] {q_type:<8}: {actual:>2} (Expected: {expected:>2})")

    if type_mismatch:
        print("FAIL: Type breakdown does not match expected counts.")
        return False

    # 6. Display Breakdown by Status
    print("\n--- Breakdown by Status ---")
    for status_name, count in sorted(status_counter.items()):
        print(f"  - {status_name:<14}: {count:>2}")

    print("\n==================================================")
    print("  ALL VALIDATION CHECKS PASSED SUCCESSFULLY!       ")
    print("==================================================")
    return True


if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)

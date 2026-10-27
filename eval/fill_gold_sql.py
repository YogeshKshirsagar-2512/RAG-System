"""Gold SQL runner and benchmark dataset updater.

Executes ground-truth SQL queries for questions Q016 to Q030 against sales.db.
Modes:
- Default: Dry run (prints queries and raw results for review).
- --commit: Updates eval/golden_set.json with gold_sql, expected_answer, and sets status to 'ready'.
"""

import sys
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure root directory is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import SQLITE_DB_PATH, GOLDEN_SET_PATH

# 15 Gold SQL queries for Q016-Q030
GOLD_SQL_QUERIES: Dict[str, str] = {
    "Q016": "SELECT ROUND(SUM(sales),2) FROM orders WHERE order_year=2017;",
    "Q017": (
        "SELECT product_name, ROUND(SUM(sales),2) AS revenue FROM orders "
        "WHERE order_year=2017 AND order_quarter=3 "
        "GROUP BY product_name ORDER BY revenue DESC LIMIT 5;"
    ),
    "Q018": (
        "SELECT region, ROUND(SUM(profit),2) AS p FROM orders "
        "WHERE order_year=2016 GROUP BY region ORDER BY p DESC LIMIT 1;"
    ),
    "Q019": "SELECT segment, ROUND(AVG(discount),4) FROM orders GROUP BY segment;",
    "Q020": "SELECT COUNT(DISTINCT customer_id) FROM orders WHERE order_year=2017;",
    "Q021": (
        "SELECT sub_category, ROUND(SUM(profit)*100.0/SUM(sales),2) AS margin_pct "
        "FROM orders GROUP BY sub_category ORDER BY margin_pct ASC LIMIT 1;"
    ),
    "Q022": (
        "SELECT order_month, ROUND(SUM(sales),2) FROM orders "
        "WHERE order_year=2017 GROUP BY order_month ORDER BY order_month;"
    ),
    "Q023": "SELECT state, COUNT(DISTINCT order_id) AS n FROM orders GROUP BY state ORDER BY n DESC LIMIT 1;",
    "Q024": (
        "SELECT ROUND((SUM(CASE WHEN order_year=2017 THEN sales END) / "
        "SUM(CASE WHEN order_year=2016 THEN sales END) - 1) * 100, 2) FROM orders;"
    ),
    "Q025": "SELECT ship_mode, COUNT(DISTINCT order_id) AS n FROM orders GROUP BY ship_mode ORDER BY n DESC LIMIT 1;",
    "Q026": (
        "SELECT customer_name, ROUND(SUM(sales),2) AS t FROM orders "
        "GROUP BY customer_id, customer_name ORDER BY t DESC LIMIT 10;"
    ),
    "Q027": "SELECT ROUND(100.0*SUM(CASE WHEN discount>0.2 THEN 1 ELSE 0 END)/COUNT(*),2) FROM orders;",
    "Q028": (
        "SELECT category, region, ROUND(SUM(profit),2) AS p FROM orders "
        "GROUP BY category, region HAVING p < 0;"
    ),
    "Q029": (
        "SELECT segment, ROUND(AVG(order_total),2) FROM "
        "(SELECT order_id, segment, SUM(sales) AS order_total FROM orders GROUP BY order_id, segment) "
        "GROUP BY segment;"
    ),
    "Q030": "SELECT COUNT(DISTINCT order_id) FROM orders WHERE order_year=2016 AND order_quarter=4;",
}


def format_result_to_string(rows: List[Any]) -> str:
    """Format raw SQL rows into a clean, human-readable string answer."""
    if not rows:
        return "No results found."

    # Single scalar value (1 row, 1 col)
    if len(rows) == 1 and len(rows[0]) == 1:
        val = rows[0][0]
        return str(val)

    # Single row with 2 columns (e.g. region + max profit)
    if len(rows) == 1 and len(rows[0]) == 2:
        return f"{rows[0][0]}: {rows[0][1]}"

    # Multiple rows
    formatted_items = []
    for r in rows:
        if len(r) == 2:
            formatted_items.append(f"{r[0]}: {r[1]}")
        else:
            formatted_items.append(" | ".join(str(c) for c in r))
    return "; ".join(formatted_items)


def run_gold_queries(commit: bool = False):
    print("==================================================")
    print(f"  Executing 15 Gold SQL Queries (Commit: {commit})  ")
    print("==================================================")

    db_uri = f"file:{SQLITE_DB_PATH.as_posix()}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    cursor = conn.cursor()

    results_map = {}

    for q_id, sql in sorted(GOLD_SQL_QUERIES.items()):
        cursor.execute(sql)
        rows = cursor.fetchall()
        formatted_answer = format_result_to_string(rows)
        results_map[q_id] = {
            "sql": sql,
            "raw_rows": rows,
            "answer_str": formatted_answer,
        }

        print(f"\n[{q_id}]")
        print(f"  SQL   : {sql}")
        print(f"  Answer: {formatted_answer}")

    conn.close()

    if commit:
        print("\n--- Committing SQL answers to eval/golden_set.json ---")
        with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
            golden_data = json.load(f)

        updated_count = 0
        for entry in golden_data:
            eid = entry["id"]
            if eid in results_map:
                entry["gold_sql"] = results_map[eid]["sql"]
                entry["expected_answer"] = results_map[eid]["answer_str"]
                entry["status"] = "ready"
                updated_count += 1

        with open(GOLDEN_SET_PATH, "w", encoding="utf-8") as f:
            json.dump(golden_data, f, indent=2, ensure_ascii=False)

        print(f"Successfully committed {updated_count} SQL questions to {GOLDEN_SET_PATH.name}!")
    else:
        print("\n[NOTE] Dry-run only. Re-run with '--commit' to update eval/golden_set.json.")


def main():
    parser = argparse.ArgumentParser(description="Run gold SQL queries against sales.db")
    parser.add_argument("--commit", action="store_true", help="Commit results into eval/golden_set.json")
    args = parser.parse_args()

    run_gold_queries(commit=args.commit)


if __name__ == "__main__":
    main()

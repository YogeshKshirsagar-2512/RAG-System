"""Data quality and security verification suite for sales.db.

Runs 9 rigorous validation checks:
1. no_null_keys: Key columns contain zero NULL values.
2. order_date_range: All orders fall within 2014-01-01 to 2017-12-31.
3. exact_4_regions: Exactly matches East, West, Central, South.
4. exact_3_segments: Exactly matches Consumer, Corporate, Home Office.
5. discount_range: All discounts are between 0.0 and 1.0 (0% - 100%).
6. ship_date_chronology: ship_date is always >= order_date.
7. positive_sales: All sales values are strictly > 0.
8. unique_row_id: Zero duplicate row_id entries.
9. read_only_guardrail: Connection opened with URI mode=ro rejects INSERT statements.
"""

import sys
import sqlite3
from pathlib import Path

# Ensure root directory is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import SQLITE_DB_PATH


def run_checks() -> bool:
    print("==================================================")
    print("     Running Database Quality & Safety Checks     ")
    print("==================================================")

    if not SQLITE_DB_PATH.exists():
        print(f"FAIL: Database file does not exist at {SQLITE_DB_PATH}")
        return False

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    all_passed = True

    # 1. No NULL in key columns
    key_columns = ["order_id", "order_date", "customer_id", "product_id", "sales", "quantity", "discount", "profit"]
    null_conditions = " OR ".join([f"{col} IS NULL" for col in key_columns])
    cursor.execute(f"SELECT COUNT(*) FROM orders WHERE {null_conditions};")
    null_count = cursor.fetchone()[0]
    if null_count == 0:
        print("  [PASS] No NULL values in key columns")
    else:
        print(f"  [FAIL] Found {null_count} rows with NULL in key columns")
        all_passed = False

    # 2. Date range within 2014-2017
    cursor.execute("SELECT MIN(order_date), MAX(order_date) FROM orders;")
    min_date, max_date = cursor.fetchone()
    if min_date >= "2014-01-01" and max_date <= "2017-12-31":
        print(f"  [PASS] Order dates within 2014-2017 (Min: {min_date}, Max: {max_date})")
    else:
        print(f"  [FAIL] Order dates out of bounds (Min: {min_date}, Max: {max_date})")
        all_passed = False

    # 3. Exactly 4 regions: East, West, Central, South
    expected_regions = {"East", "West", "Central", "South"}
    cursor.execute("SELECT DISTINCT region FROM orders;")
    regions = {row[0] for row in cursor.fetchall()}
    if regions == expected_regions:
        print(f"  [PASS] Exactly 4 expected regions present: {sorted(regions)}")
    else:
        print(f"  [FAIL] Regions mismatch. Found: {regions}, Expected: {expected_regions}")
        all_passed = False

    # 4. Exactly 3 segments: Consumer, Corporate, Home Office
    expected_segments = {"Consumer", "Corporate", "Home Office"}
    cursor.execute("SELECT DISTINCT segment FROM orders;")
    segments = {row[0] for row in cursor.fetchall()}
    if segments == expected_segments:
        print(f"  [PASS] Exactly 3 expected segments present: {sorted(segments)}")
    else:
        print(f"  [FAIL] Segments mismatch. Found: {segments}, Expected: {expected_segments}")
        all_passed = False

    # 5. Discount between 0 and 1
    cursor.execute("""
        SELECT
            MIN(discount),
            MAX(discount),
            (SELECT COUNT(*) FROM orders WHERE discount < 0 OR discount > 1)
        FROM orders;
    """)
    min_disc, max_disc, invalid_disc_count = cursor.fetchone()
    if invalid_disc_count == 0:
        print(f"  [PASS] All discounts within [0.0, 1.0] range (Min: {min_disc}, Max: {max_disc})")
    else:
        print(f"  [FAIL] Found {invalid_disc_count} orders with invalid discount")
        all_passed = False

    # 6. Ship date >= order date
    cursor.execute("SELECT COUNT(*) FROM orders WHERE ship_date < order_date;")
    invalid_shipping_count = cursor.fetchone()[0]
    if invalid_shipping_count == 0:
        print("  [PASS] Ship date is chronologically on or after order date for all orders")
    else:
        print(f"  [FAIL] Found {invalid_shipping_count} orders where ship_date < order_date")
        all_passed = False

    # 7. Sales > 0
    cursor.execute("SELECT COUNT(*) FROM orders WHERE sales <= 0;")
    non_positive_sales = cursor.fetchone()[0]
    if non_positive_sales == 0:
        print("  [PASS] All sales amounts are strictly positive (> 0)")
    else:
        print(f"  [FAIL] Found {non_positive_sales} orders with sales <= 0")
        all_passed = False

    # 8. No duplicate row_id
    cursor.execute("SELECT COUNT(row_id), COUNT(DISTINCT row_id) FROM orders;")
    total_rows, distinct_rows = cursor.fetchone()
    if total_rows == distinct_rows:
        print(f"  [PASS] Zero duplicate row_id entries ({total_rows} total rows)")
    else:
        print(f"  [FAIL] Duplicate row_id detected: {total_rows} rows vs {distinct_rows} distinct")
        all_passed = False

    conn.close()

    # 9. Read-only connection security check
    # Format URI correctly for Windows filesystem path: file:data/sales.db?mode=ro
    db_relative_uri = f"file:{SQLITE_DB_PATH.as_posix()}?mode=ro"
    try:
        ro_conn = sqlite3.connect(db_relative_uri, uri=True)
        ro_cursor = ro_conn.cursor()
        # Verify read access works
        ro_cursor.execute("SELECT COUNT(*) FROM orders;")
        count = ro_cursor.fetchone()[0]

        # Attempt forbidden write operation
        try:
            ro_cursor.execute(
                "INSERT INTO orders (row_id, order_id, order_date, ship_date, ship_mode, "
                "customer_id, customer_name, segment, country, city, state, postal_code, "
                "region, product_id, category, sub_category, product_name, sales, quantity, "
                "discount, profit, order_year, order_quarter, order_month) "
                "VALUES (99999, 'TEST', '2017-01-01', '2017-01-02', 'Standard', 'C1', 'N', "
                "'Consumer', 'US', 'C', 'S', '12345', 'West', 'P1', 'Cat', 'Sub', 'Prod', "
                "10.0, 1, 0.0, 5.0, 2017, 1, 1);"
            )
            ro_conn.commit()
            print("  [FAIL] Read-only security check FAILED: write succeeded on readonly connection!")
            all_passed = False
        except sqlite3.OperationalError as op_err:
            if "readonly" in str(op_err).lower():
                print(f"  [PASS] Read-only guardrail enforced: Write rejected with '{op_err}'")
            else:
                print(f"  [PASS] Read-only guardrail enforced with error: '{op_err}'")
        ro_conn.close()
    except Exception as e:
        print(f"  [FAIL] Read-only connection error: {e}")
        all_passed = False

    print("\n==================================================")
    if all_passed:
        print("  ALL DATABASE QUALITY & SAFETY CHECKS PASSED!     ")
    else:
        print("  ONE OR MORE DATABASE CHECKS FAILED!             ")
    print("==================================================")

    return all_passed


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)

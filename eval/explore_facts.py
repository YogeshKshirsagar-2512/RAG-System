"""Exploratory SQL analytics script on sales.db.

Extracts real financial metrics to ground synthetic documents:
1. Revenue and profit by region by quarter with QoQ and YoY % change.
2. Sub-category profit and profit margin %.
3. Average discount by segment and sub-category.
4. Share of order lines with discount > 10% and > 20%.
5. Technology revenue and profit by quarter in 2017.
"""

import sys
import sqlite3
import pandas as pd
from pathlib import Path

# Ensure root directory is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import SQLITE_DB_PATH


def explore():
    conn = sqlite3.connect(SQLITE_DB_PATH)

    print("==================================================")
    print("      Superstore Database Fact Exploration        ")
    print("==================================================")

    # 1. Revenue/Profit by Region by Quarter with QoQ and YoY %
    print("\n--- 1. Regional Quarterly Performance (with QoQ and YoY %) ---")
    query_regional = """
        SELECT region, order_year, order_quarter, revenue, profit, margin_pct
        FROM v_region_quarterly
        ORDER BY region, order_year, order_quarter;
    """
    df_reg = pd.read_sql_query(query_regional, conn)

    # Calculate QoQ within region
    df_reg["qoq_revenue_pct"] = df_reg.groupby("region")["revenue"].pct_change() * 100.0

    # Calculate YoY within region (lag 4 quarters)
    df_reg["yoy_revenue_pct"] = df_reg.groupby("region")["revenue"].pct_change(periods=4) * 100.0

    # Filter to 2016-2017 for readable inspection
    df_reg_recent = df_reg[df_reg["order_year"] >= 2016].copy()
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1000)
    print(df_reg_recent.to_string(index=False))

    # 2. Sub-category Profit and Margin
    print("\n--- 2. Sub-Category Profit and Margin (Ascending Margin) ---")
    query_subcat = """
        SELECT
            category,
            sub_category,
            ROUND(SUM(sales), 2) AS total_sales,
            ROUND(SUM(profit), 2) AS total_profit,
            ROUND(SUM(profit) * 100.0 / SUM(sales), 2) AS margin_pct
        FROM orders
        GROUP BY category, sub_category
        ORDER BY margin_pct ASC;
    """
    df_subcat = pd.read_sql_query(query_subcat, conn)
    print(df_subcat.to_string(index=False))

    # 3. Average Discount by Segment and Sub-Category
    print("\n--- 3A. Average Discount by Segment ---")
    query_seg_disc = """
        SELECT
            segment,
            ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
            COUNT(*) AS order_lines
        FROM orders
        GROUP BY segment
        ORDER BY avg_discount_pct DESC;
    """
    df_seg_disc = pd.read_sql_query(query_seg_disc, conn)
    print(df_seg_disc.to_string(index=False))

    print("\n--- 3B. Top 5 Most Discounted Sub-Categories ---")
    query_subcat_disc = """
        SELECT
            sub_category,
            ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
            ROUND(SUM(profit), 2) AS total_profit
        FROM orders
        GROUP BY sub_category
        ORDER BY avg_discount_pct DESC
        LIMIT 5;
    """
    df_subcat_disc = pd.read_sql_query(query_subcat_disc, conn)
    print(df_subcat_disc.to_string(index=False))

    # 4. Share of lines with discount >10% and >20%
    print("\n--- 4. Share of Order Lines with High Discounts ---")
    query_high_disc = """
        SELECT
            COUNT(*) AS total_lines,
            SUM(CASE WHEN discount > 0.10 THEN 1 ELSE 0 END) AS lines_gt_10,
            ROUND(100.0 * SUM(CASE WHEN discount > 0.10 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_gt_10,
            SUM(CASE WHEN discount > 0.20 THEN 1 ELSE 0 END) AS lines_gt_20,
            ROUND(100.0 * SUM(CASE WHEN discount > 0.20 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_gt_20
        FROM orders;
    """
    df_high_disc = pd.read_sql_query(query_high_disc, conn)
    print(df_high_disc.to_string(index=False))

    # 5. Technology Revenue by Quarter in 2017
    print("\n--- 5. Technology Category Performance by Quarter in 2017 ---")
    query_tech_2017 = """
        SELECT
            order_year,
            order_quarter,
            ROUND(SUM(sales), 2) AS tech_revenue,
            ROUND(SUM(profit), 2) AS tech_profit,
            ROUND(SUM(profit) * 100.0 / SUM(sales), 2) AS margin_pct
        FROM orders
        WHERE category = 'Technology' AND order_year = 2017
        GROUP BY order_year, order_quarter
        ORDER BY order_quarter;
    """
    df_tech_2017 = pd.read_sql_query(query_tech_2017, conn)
    print(df_tech_2017.to_string(index=False))

    conn.close()
    print("\n==================================================")
    print("        Fact Exploration Run Finished             ")
    print("==================================================")


if __name__ == "__main__":
    explore()

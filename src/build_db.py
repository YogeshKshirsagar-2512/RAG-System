"""Database build script for the Hybrid RAG system.

ETL pipeline that:
1. Ingests raw Superstore CSV.
2. Cleans text, standardizes dates into ISO YYYY-MM-DD format.
3. Adds derived temporal columns (order_year, order_quarter, order_month).
4. Normalizes tables into SQLite: 'orders', 'customers', and 'products'.
5. Creates analytical view 'v_region_quarterly'.
6. Builds B-tree indexes for fast analytical query execution.
7. Is 100% idempotent and re-runnable (safely deletes and recreates data/sales.db).
"""

import sys
import sqlite3
import pandas as pd
from pathlib import Path

# Ensure root directory is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, RAW_DATA_DIR, SQLITE_DB_PATH

CSV_PATH = RAW_DATA_DIR / "Sample - Superstore.csv"


def clean_and_prepare_data(csv_path: Path) -> pd.DataFrame:
    """Read and clean Superstore CSV data."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Source CSV not found at: {csv_path}")

    # Read with windows-1252/latin-1 encoding
    df = pd.read_csv(csv_path, encoding="windows-1252")

    # Rename columns to lowercase_with_underscores
    column_mapping = {
        "Row ID": "row_id",
        "Order ID": "order_id",
        "Order Date": "order_date",
        "Ship Date": "ship_date",
        "Ship Mode": "ship_mode",
        "Customer ID": "customer_id",
        "Customer Name": "customer_name",
        "Segment": "segment",
        "Country": "country",
        "City": "city",
        "State": "state",
        "Postal Code": "postal_code",
        "Region": "region",
        "Product ID": "product_id",
        "Category": "category",
        "Sub-Category": "sub_category",
        "Product Name": "product_name",
        "Sales": "sales",
        "Quantity": "quantity",
        "Discount": "discount",
        "Profit": "profit",
    }
    df = df.rename(columns=column_mapping)

    # Strip whitespace from string/object columns
    str_cols = df.select_dtypes(include=["object", "string", "str"]).columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()

    # Drop exact duplicates if any
    initial_count = len(df)
    df = df.drop_duplicates()
    dropped_count = initial_count - len(df)
    print(f"Loaded {initial_count} rows. Dropped exact duplicates: {dropped_count}")

    # Parse dates to datetime and format as ISO YYYY-MM-DD text
    order_dt = pd.to_datetime(df["order_date"], format="%m/%d/%Y", errors="coerce")
    ship_dt = pd.to_datetime(df["ship_date"], format="%m/%d/%Y", errors="coerce")

    # Fallback to general parsing if format mismatch occurs
    if order_dt.isna().any():
        order_dt = pd.to_datetime(df["order_date"])
    if ship_dt.isna().any():
        ship_dt = pd.to_datetime(df["ship_date"])

    # Derived temporal columns
    df["order_year"] = order_dt.dt.year.astype(int)
    df["order_quarter"] = order_dt.dt.quarter.astype(int)
    df["order_month"] = order_dt.dt.month.astype(int)

    # Convert date columns to ISO string
    df["order_date"] = order_dt.dt.strftime("%Y-%m-%d")
    df["ship_date"] = ship_dt.dt.strftime("%Y-%m-%d")

    # Convert numeric fields
    df["sales"] = df["sales"].astype(float)
    df["quantity"] = df["quantity"].astype(int)
    df["discount"] = df["discount"].astype(float)
    df["profit"] = df["profit"].astype(float)

    # Handle postal_code: convert to string, fill NaN/missing with None (SQL NULL)
    df["postal_code"] = df["postal_code"].apply(
        lambda x: None if pd.isna(x) or str(x).strip() in ("", "nan", "None") else str(int(x) if isinstance(x, (int, float)) else x).zfill(5)
    )

    return df


def build_sqlite_db(df: pd.DataFrame, db_path: Path):
    """Build normalized tables, views, and indexes in SQLite."""
    # If DB exists, remove it for clean re-runnability
    if db_path.exists():
        try:
            db_path.unlink()
            print(f"Removed existing database at {db_path.name} for fresh build.")
        except Exception as e:
            print(f"Warning removing {db_path.name}: {e}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Master Table: orders
    cursor.execute("""
        CREATE TABLE orders (
            row_id INTEGER PRIMARY KEY,
            order_id TEXT NOT NULL,
            order_date TEXT NOT NULL,
            ship_date TEXT NOT NULL,
            ship_mode TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            segment TEXT NOT NULL,
            country TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            postal_code TEXT,
            region TEXT NOT NULL,
            product_id TEXT NOT NULL,
            category TEXT NOT NULL,
            sub_category TEXT NOT NULL,
            product_name TEXT NOT NULL,
            sales REAL NOT NULL,
            quantity INTEGER NOT NULL,
            discount REAL NOT NULL,
            profit REAL NOT NULL,
            order_year INTEGER NOT NULL,
            order_quarter INTEGER NOT NULL,
            order_month INTEGER NOT NULL
        );
    """)

    # Insert orders data
    df.to_sql("orders", conn, if_exists="append", index=False)

    # 2. Lookup Table: customers (distinct customer_id)
    cursor.execute("""
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            segment TEXT NOT NULL
        );
    """)
    # Deduplicate customers by customer_id (keeping first observed customer_name and segment)
    customers_df = df[["customer_id", "customer_name", "segment"]].drop_duplicates(subset=["customer_id"])
    customers_df.to_sql("customers", conn, if_exists="append", index=False)

    # 3. Lookup Table: products (distinct product_id, most frequent name)
    cursor.execute("""
        CREATE TABLE products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            sub_category TEXT NOT NULL
        );
    """)

    # Find the most frequent product_name per product_id
    name_counts = (
        df.groupby(["product_id", "category", "sub_category", "product_name"])
        .size()
        .reset_index(name="count")
    )
    # Sort by count desc and pick top 1 per product_id
    products_dedup = (
        name_counts.sort_values(["product_id", "count"], ascending=[True, False])
        .drop_duplicates(subset=["product_id"])[["product_id", "product_name", "category", "sub_category"]]
    )
    products_dedup.to_sql("products", conn, if_exists="append", index=False)

    # 4. View: v_region_quarterly
    cursor.execute("""
        CREATE VIEW v_region_quarterly AS
        SELECT
            region,
            order_year,
            order_quarter,
            ROUND(SUM(sales), 2) AS revenue,
            ROUND(SUM(profit), 2) AS profit,
            ROUND(SUM(profit) * 100.0 / SUM(sales), 2) AS margin_pct,
            COUNT(DISTINCT order_id) AS order_count
        FROM orders
        GROUP BY region, order_year, order_quarter;
    """)

    # 5. Performance Indexes
    cursor.execute("CREATE INDEX idx_orders_order_date ON orders(order_date);")
    cursor.execute("CREATE INDEX idx_orders_region ON orders(region);")
    cursor.execute("CREATE INDEX idx_orders_category ON orders(category);")
    cursor.execute("CREATE INDEX idx_orders_sub_category ON orders(sub_category);")
    cursor.execute("CREATE INDEX idx_orders_customer_id ON orders(customer_id);")

    conn.commit()

    # 6. Report table row counts
    print("\n--- Database Build Complete: Table Statistics ---")
    tables = ["orders", "customers", "products"]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print(f"  Table '{table:<10}': {count:>6} rows")

    cursor.execute("SELECT COUNT(*) FROM v_region_quarterly;")
    view_count = cursor.fetchone()[0]
    print(f"  View  'v_region_quarterly': {view_count:>6} rows")

    conn.close()


def main():
    print("==================================================")
    print("        Building SQLite Database (sales.db)       ")
    print("==================================================")
    df = clean_and_prepare_data(CSV_PATH)
    build_sqlite_db(df, SQLITE_DB_PATH)
    print(f"\nDatabase successfully written to: {SQLITE_DB_PATH}")


if __name__ == "__main__":
    main()

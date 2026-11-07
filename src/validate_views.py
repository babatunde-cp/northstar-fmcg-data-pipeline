"""Check the analytics views by re-calculating their numbers independently with pandas.

Run from the project root:  python src/validate_views.py

For each view, the expected figures are worked out from the STAGING tables (not from the curated
tables the views read), so a mistake in the model or in a view shows up as a difference.
The script prints one line per check and exits with an error if any check fails.
"""
import sys

import numpy as np
import pandas as pd
from sqlalchemy import text

from check_connection import build_engine, load_config

STATUS_GROUP = {"Delivered": "Completed", "Returned": "Returned", "Pending": "Open", "Cancelled": "Cancelled"}
MONEY_TOLERANCE = 0.01
RATE_TOLERANCE = 0.0001


def read(conn, sql: str) -> pd.DataFrame:
    return pd.read_sql(text(sql), conn)


def compare(name, view, expected, key, columns, tolerance=MONEY_TOLERANCE):
    """Join the view and the independent calculation on key, and compare the listed columns."""
    merged = view.merge(expected, on=key, how="outer", suffixes=("_view", "_check"), indicator=True)
    one_sided = int((merged["_merge"] != "both").sum())
    if one_sided:
        return name, False, f"{one_sided} keys appear on one side only"
    for col in columns:
        diff = (merged[f"{col}_view"].astype(float) - merged[f"{col}_check"].astype(float)).abs().max()
        if diff > tolerance:
            return name, False, f"{col} differs by up to {diff:,.4f}"
    return name, True, f"{len(merged)} rows compared"


def sales_frame(conn) -> pd.DataFrame:
    s = read(
        conn,
        "SELECT transaction_datetime, customer_id, product_id, quantity, discount_pct, gross_sales_ngn, "
        "discount_amount_ngn, net_sales_ngn, order_status FROM staging.sales_transactions",
    )
    s["month"] = pd.to_datetime(s["transaction_datetime"]).dt.strftime("%Y-%m")
    s["group"] = s["order_status"].map(STATUS_GROUP)
    return s


def check_monthly_sales(conn, s):
    view = read(conn, "SELECT * FROM analytics.vw_monthly_sales")
    done = s[s["group"] == "Completed"].groupby("month").agg(
        completed_transactions=("net_sales_ngn", "size"),
        gross_sales_ngn=("gross_sales_ngn", "sum"),
        discount_ngn=("discount_amount_ngn", "sum"),
        revenue_ngn=("net_sales_ngn", "sum"),
    )
    for group, column in [("Returned", "returned_value_ngn"), ("Open", "open_orders_value_ngn"), ("Cancelled", "lost_sales_value_ngn")]:
        done[column] = s[s["group"] == group].groupby("month")["net_sales_ngn"].sum()
    exp = done.fillna(0).reset_index().rename(columns={"month": "sales_month"})
    exp["discount_rate"] = exp["discount_ngn"] / exp["gross_sales_ngn"]
    exp["avg_transaction_value_ngn"] = exp["revenue_ngn"] / exp["completed_transactions"]
    exp["return_rate"] = exp["returned_value_ngn"] / (exp["revenue_ngn"] + exp["returned_value_ngn"])
    money = ["completed_transactions", "gross_sales_ngn", "discount_ngn", "revenue_ngn",
             "returned_value_ngn", "open_orders_value_ngn", "lost_sales_value_ngn", "avg_transaction_value_ngn"]
    yield compare("vw_monthly_sales amounts", view, exp, "sales_month", money)
    yield compare("vw_monthly_sales rates", view, exp, "sales_month", ["discount_rate", "return_rate"], RATE_TOLERANCE)


def check_sales_by_status(conn, s):
    view = read(conn, "SELECT order_status, transactions, units, net_sales_ngn FROM analytics.vw_sales_by_status")
    exp = s.groupby("order_status").agg(transactions=("quantity", "size"), units=("quantity", "sum"),
                                        net_sales_ngn=("net_sales_ngn", "sum")).reset_index()
    yield compare("vw_sales_by_status", view, exp, "order_status", ["transactions", "units", "net_sales_ngn"])


def check_product_performance(conn, s):
    view = read(conn, "SELECT * FROM analytics.vw_product_performance")
    products = read(conn, "SELECT product_id FROM staging.product_master")
    done = s[s["group"] == "Completed"].groupby("product_id").agg(units_sold=("quantity", "sum"), revenue_ngn=("net_sales_ngn", "sum"))
    done["returned_value_ngn"] = s[s["group"] == "Returned"].groupby("product_id")["net_sales_ngn"].sum()
    exp = products.set_index("product_id").join(done).fillna(0).reset_index()
    yield compare("vw_product_performance amounts", view, exp, "product_id", ["units_sold", "revenue_ngn", "returned_value_ngn"])
    top_view = view.loc[view["revenue_rank"] == 1, "product_id"].tolist()
    top_check = exp.loc[exp["revenue_ngn"] == exp["revenue_ngn"].max(), "product_id"].tolist()
    yield "vw_product_performance top product", top_view == top_check, f"{top_view} vs {top_check}"


def check_customer_performance(conn, s):
    view = read(conn, "SELECT * FROM analytics.vw_customer_performance")
    customers = read(conn, "SELECT customer_id FROM staging.customer_master")
    ids = pd.DataFrame({"customer_id": list(customers["customer_id"]) + ["UNKNOWN"]})
    revenue = s[s["group"] == "Completed"].groupby("customer_id")["net_sales_ngn"].sum().rename("revenue_ngn")
    exp = ids.set_index("customer_id").join(revenue).fillna(0).reset_index()
    yield compare("vw_customer_performance revenue", view, exp, "customer_id", ["revenue_ngn"])
    known = view[view["is_unknown"] == 0]
    ok = abs(known["cumulative_revenue_share"].max() - 1.0) < 0.0001 and known["revenue_rank"].min() == 1
    yield "vw_customer_performance cumulative share reaches 100%", bool(ok), f"max {known['cumulative_revenue_share'].max():.6f}"
    yield "vw_customer_performance unknown member has no rank", bool(view.loc[view["is_unknown"] == 1, "revenue_rank"].isna().all()), "UNKNOWN left out of ranking"


def check_discount_analysis(conn, s):
    view = read(conn, "SELECT band_order, transactions, units_sold, revenue_ngn FROM analytics.vw_discount_analysis")
    done = s[s["group"] == "Completed"].copy()
    d = done["discount_pct"].astype(float)
    done["band_order"] = np.select([d == 0, d < 0.05, d < 0.10, d < 0.15], [1, 2, 3, 4], default=5)
    exp = done.groupby("band_order").agg(transactions=("quantity", "size"), units_sold=("quantity", "sum"),
                                         revenue_ngn=("net_sales_ngn", "sum")).reset_index()
    yield compare("vw_discount_analysis", view, exp, "band_order", ["transactions", "units_sold", "revenue_ngn"])


def check_stock(conn):
    snap = read(conn, "SELECT warehouse_id, product_id, on_hand_units, reserved_units, available_units, reorder_level_units "
                      "FROM staging.inventory_snapshot")
    products = read(conn, "SELECT product_id, category FROM staging.product_master")
    snap = snap.merge(products, on="product_id")

    view = read(conn, "SELECT warehouse_id, product_id FROM analytics.vw_stock_below_reorder")
    expected = snap[snap["available_units"] < snap["reorder_level_units"]]
    same = set(map(tuple, view.values)) == set(map(tuple, expected[["warehouse_id", "product_id"]].values))
    yield "vw_stock_below_reorder same product/warehouse pairs", same, f"{len(view)} in view, {len(expected)} expected"

    view = read(conn, "SELECT * FROM analytics.vw_inventory_by_warehouse_category")
    exp = snap.groupby(["warehouse_id", "category"]).agg(
        on_hand_units=("on_hand_units", "sum"), reserved_units=("reserved_units", "sum"),
        available_units=("available_units", "sum")).reset_index()
    yield compare("vw_inventory_by_warehouse_category", view, exp, ["warehouse_id", "category"],
                  ["on_hand_units", "reserved_units", "available_units"])

    mov = read(conn, "SELECT product_id, warehouse_id, movement_type, approval_status, quantity_change "
                     "FROM staging.inventory_movements")
    view = read(conn, "SELECT movement_type, approval_status, movements, units_in, units_out FROM analytics.vw_movement_summary")
    view = view.groupby(["movement_type", "approval_status"], as_index=False).sum()
    mov["units_in"] = mov["quantity_change"].clip(lower=0)
    mov["units_out"] = (-mov["quantity_change"]).clip(lower=0)
    exp = mov.groupby(["movement_type", "approval_status"]).agg(
        movements=("quantity_change", "size"), units_in=("units_in", "sum"), units_out=("units_out", "sum")).reset_index()
    yield compare("vw_movement_summary", view, exp, ["movement_type", "approval_status"], ["movements", "units_in", "units_out"])

    view = read(conn, "SELECT is_implied_opening_negative FROM analytics.vw_stock_reconciliation")
    approved = mov[mov["approval_status"] == "Approved"].groupby(["warehouse_id", "product_id"])["quantity_change"].sum().rename("net")
    joined = snap.set_index(["warehouse_id", "product_id"]).join(approved).fillna({"net": 0})
    expected_negative = int((joined["on_hand_units"] - joined["net"] < 0).sum())
    yield ("vw_stock_reconciliation negative opening count", int(view["is_implied_opening_negative"].sum()) == expected_negative,
           f"{expected_negative} expected")


def check_data_quality(conn):
    view = read(conn, "SELECT table_name, raw_rows, clean_rows, quarantined_rows FROM analytics.vw_dq_table_summary")
    stored = []
    for table in ["sales_transactions", "inventory_snapshot", "inventory_movements"]:
        clean = read(conn, f"SELECT COUNT(*) AS n FROM staging.{table}")["n"][0]
        held = read(conn, f"SELECT COUNT(*) AS n FROM quarantine.{table}")["n"][0]
        stored.append({"table_name": table, "clean_rows": clean, "quarantined_rows": held, "raw_rows": clean + held})
    for table in ["customer_master", "product_master"]:
        n = read(conn, f"SELECT COUNT(*) AS n FROM staging.{table}")["n"][0]
        stored.append({"table_name": table, "clean_rows": n, "quarantined_rows": 0, "raw_rows": n})
    yield compare("vw_dq_table_summary vs tables", view, pd.DataFrame(stored), "table_name",
                  ["raw_rows", "clean_rows", "quarantined_rows"])

    raw_sales = read(conn, "SELECT transaction_id, product_id FROM raw.sales_transactions")
    raw_products = read(conn, "SELECT product_id FROM raw.product_master")
    rules = read(conn, "SELECT rule_code, rows_affected FROM analytics.vw_dq_rule_results").set_index("rule_code")["rows_affected"]
    dup = int(raw_sales["transaction_id"].duplicated(keep=False).sum())
    unknown = int((~raw_sales["product_id"].isin(raw_products["product_id"])).sum())
    yield "vw_dq_rule_results reused transaction IDs", int(rules["S03_DUPLICATE_TRANSACTION_ID"]) == dup, f"{dup} expected"
    yield "vw_dq_rule_results unknown products in sales", int(rules["S04_UNKNOWN_PRODUCT"]) == unknown, f"{unknown} expected"


def check_pipeline(conn):
    runs = read(conn, "SELECT stage, status, is_latest_success FROM analytics.vw_pipeline_runs")
    ok = all(group["is_latest_success"].sum() == 1 for _, group in runs[runs["status"] == "SUCCESS"].groupby("stage"))
    yield "vw_pipeline_runs one latest success per stage", ok, f"{runs['stage'].nunique()} stages"
    recon = read(conn, "SELECT result FROM analytics.vw_load_reconciliation WHERE is_latest_success = 1")
    yield "vw_load_reconciliation latest runs all OK", bool((recon["result"] == "OK").all()) and len(recon) > 0, f"{len(recon)} loads"


def main() -> None:
    engine = build_engine(load_config())
    failures = 0
    with engine.connect() as conn:
        s = sales_frame(conn)
        checks = [
            check_monthly_sales(conn, s), check_sales_by_status(conn, s), check_product_performance(conn, s),
            check_customer_performance(conn, s), check_discount_analysis(conn, s), check_stock(conn),
            check_data_quality(conn), check_pipeline(conn),
        ]
        for group in checks:
            for name, passed, detail in group:
                print(f"{'PASS' if passed else 'FAIL'}  {name}: {detail}")
                failures += 0 if passed else 1
    print(f"\n{failures} check(s) failed" if failures else "\nAll checks passed")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()

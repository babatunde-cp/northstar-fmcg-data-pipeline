"""Build the curated star schema from the staging tables.

Run from the project root:  python src/build_curated.py

- Staging is only read, never changed.
- Re-running is safe: the curated tables are emptied and rebuilt.
- Everything happens in ONE transaction. If anything fails, nothing changes.
- Row counts and totals are checked against staging and logged in audit.load_log.
"""
import logging
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from calendar_dim import build_dim_date
from check_connection import build_engine, load_config
from load_raw import finish_run

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
LOAD_SQL = PROJECT_ROOT / "sql" / "05_load_curated.sql"

# Facts are emptied first, because they point at the dimensions
CLEAR_ORDER = [
    "fact_sales", "fact_inventory_snapshot", "fact_inventory_movement",
    "dim_date", "dim_customer", "dim_product", "dim_warehouse", "dim_sales_channel", "dim_order_status",
]

# (curated table, SQL giving the row count we expect)
COUNT_CHECKS = [
    ("fact_sales", "SELECT COUNT(*) FROM staging.sales_transactions"),
    ("fact_inventory_snapshot", "SELECT COUNT(*) FROM staging.inventory_snapshot"),
    ("fact_inventory_movement", "SELECT COUNT(*) FROM staging.inventory_movements"),
    ("dim_customer", "SELECT COUNT(*) + 1 FROM staging.customer_master"),  # +1 for the UNKNOWN member
    ("dim_product", "SELECT COUNT(*) FROM staging.product_master"),
]

log = logging.getLogger("build_curated")


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(LOG_DIR / "curated_build.log", encoding="utf-8")],
    )


def scalar(conn, sql: str):
    return conn.execute(text(sql)).scalar_one()


def start_run(conn) -> int:
    result = conn.execute(
        text("INSERT INTO audit.pipeline_run (stage) OUTPUT INSERTED.run_id VALUES (:stage)"),
        {"stage": "curated_build"},
    )
    return int(result.scalar_one())


def read_steps(path: Path) -> list:
    """Split the load script into (name, statement) pairs. Each statement ends with a semicolon."""
    steps, name, buffer = [], None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("-- step:"):
            name = stripped[len("-- step:"):].strip()
            continue
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            steps.append((name, "\n".join(buffer).rstrip().rstrip(";")))
            buffer = []
    if buffer:
        raise ValueError(f"{path.name}: the last statement is missing its closing semicolon")
    return steps


def date_range_from_staging(conn) -> tuple:
    """Whole calendar years that cover every date in the data."""
    queries = [
        "SELECT MIN(transaction_datetime), MAX(transaction_datetime) FROM staging.sales_transactions",
        "SELECT MIN(movement_datetime), MAX(movement_datetime) FROM staging.inventory_movements",
        "SELECT MIN(snapshot_date), MAX(snapshot_date) FROM staging.inventory_snapshot",
    ]
    lows, highs = [], []
    for query in queries:
        low, high = conn.execute(text(query)).one()
        lows.append(pd.Timestamp(low))
        highs.append(pd.Timestamp(high))
    return date(min(lows).year, 1, 1), date(max(highs).year, 12, 31)


def verify(conn, run_id: int) -> None:
    for table, expected_sql in COUNT_CHECKS:
        expected = scalar(conn, expected_sql)
        actual = scalar(conn, f"SELECT COUNT(*) FROM curated.{table}")
        conn.execute(
            text(
                "INSERT INTO audit.load_log (run_id, table_name, source_rows, loaded_rows) "
                "VALUES (:run_id, :table_name, :source_rows, :loaded_rows)"
            ),
            {"run_id": run_id, "table_name": f"curated.{table}", "source_rows": expected, "loaded_rows": actual},
        )
        if actual != expected:
            raise ValueError(f"curated.{table}: expected {expected} rows but found {actual}")
        log.info("curated.%s: %s rows (matches staging)", table, f"{actual:,}")

    staging_net = float(scalar(conn, "SELECT SUM(net_sales_ngn) FROM staging.sales_transactions"))
    fact_net = float(scalar(conn, "SELECT SUM(net_sales_ngn) FROM curated.fact_sales"))
    if abs(staging_net - fact_net) > 0.005:
        raise ValueError(f"Net sales differ: staging {staging_net:,.2f} vs curated {fact_net:,.2f}")
    log.info("Net sales reconcile: %s", f"{fact_net:,.2f}")

    expected_unknown = scalar(conn, "SELECT COUNT(*) FROM staging.sales_transactions WHERE is_missing_customer = 1")
    actual_unknown = scalar(conn, "SELECT COUNT(*) FROM curated.fact_sales WHERE customer_key = -1")
    if expected_unknown != actual_unknown:
        raise ValueError(f"Unknown-customer sales: expected {expected_unknown} but found {actual_unknown}")
    log.info("Sales linked to the UNKNOWN customer: %s (matches flagged rows)", f"{actual_unknown:,}")


def main() -> None:
    setup_logging()
    engine = build_engine(load_config())

    with engine.begin() as conn:
        run_id = start_run(conn)
    log.info("Run %s started", run_id)

    status = "SUCCESS"
    try:
        with engine.begin() as conn:  # one transaction: everything or nothing
            if scalar(conn, "SELECT COUNT(*) FROM staging.sales_transactions") == 0:
                raise ValueError("staging.sales_transactions is empty. Run python src/run_dq.py first.")

            for table in CLEAR_ORDER:
                conn.execute(text(f"DELETE FROM curated.{table}"))

            start, end = date_range_from_staging(conn)
            dim_date = build_dim_date(start, end)
            dim_date.to_sql("dim_date", conn, schema="curated", if_exists="append", index=False)
            log.info("dim_date: %s days (%s to %s)", len(dim_date), start, end)

            for name, statement in read_steps(LOAD_SQL):
                result = conn.execute(text(statement))
                log.info("%s: %s rows", name, f"{result.rowcount:,}")

            verify(conn, run_id)
    except Exception:
        status = "FAILED"
        log.exception("Curated build failed; the curated tables were left unchanged")

    with engine.begin() as conn:
        finish_run(conn, run_id, status)
    log.info("Run %s finished: %s", run_id, status)
    if status == "FAILED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

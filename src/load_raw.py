"""Load the five source sheets into the raw schema, unchanged.

Run from the project root:  python src/load_raw.py

- Re-running is safe: each raw table is emptied, then reloaded.
- All five tables load in ONE transaction. If anything fails, nothing changes.
- Every run is recorded in audit.pipeline_run and audit.load_log.
"""
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from check_connection import build_engine, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"

# (workbook file, sheet name, raw table name)
SOURCES = [
    ("01_sales_transactions.xlsx", "Sales_Transactions", "sales_transactions"),
    ("01_sales_transactions.xlsx", "Customer_Master", "customer_master"),
    ("02_product_inventory.xlsx", "Product_Master", "product_master"),
    ("02_product_inventory.xlsx", "Inventory_Snapshot", "inventory_snapshot"),
    ("03_inventory_movements.xlsx", "Inventory_Movements", "inventory_movements"),
]

log = logging.getLogger("load_raw")


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "raw_load.log", encoding="utf-8"),
        ],
    )


def read_sheet(data_dir: Path, workbook: str, sheet: str) -> pd.DataFrame:
    path = data_dir / workbook
    if not path.exists():
        raise FileNotFoundError(f"Input workbook not found: {path}")
    return pd.read_excel(path, sheet_name=sheet)


def start_run(conn) -> int:
    result = conn.execute(
        text("INSERT INTO audit.pipeline_run (stage) OUTPUT INSERTED.run_id VALUES (:stage)"),
        {"stage": "raw_load"},
    )
    return int(result.scalar_one())


def finish_run(conn, run_id: int, status: str) -> None:
    conn.execute(
        text("UPDATE audit.pipeline_run SET status = :status, finished_at = SYSUTCDATETIME() WHERE run_id = :run_id"),
        {"status": status, "run_id": run_id},
    )


def load_table(conn, df: pd.DataFrame, table: str, run_id: int, source_file: str) -> int:
    """Empty the raw table, load the DataFrame, and check the row count matches."""
    source_rows = len(df)
    df = df.assign(load_run_id=run_id, source_file=source_file)

    conn.execute(text(f"TRUNCATE TABLE raw.{table}"))
    df.to_sql(table, conn, schema="raw", if_exists="append", index=False, chunksize=5000)

    loaded_rows = conn.execute(
        text(f"SELECT COUNT(*) FROM raw.{table} WHERE load_run_id = :run_id"),
        {"run_id": run_id},
    ).scalar_one()

    conn.execute(
        text(
            "INSERT INTO audit.load_log (run_id, table_name, source_rows, loaded_rows) "
            "VALUES (:run_id, :table_name, :source_rows, :loaded_rows)"
        ),
        {"run_id": run_id, "table_name": table, "source_rows": source_rows, "loaded_rows": loaded_rows},
    )

    if loaded_rows != source_rows:
        raise ValueError(f"raw.{table}: read {source_rows} rows but loaded {loaded_rows}")
    log.info("raw.%s: %s rows loaded (matches source)", table, f"{loaded_rows:,}")
    return loaded_rows


def main() -> None:
    setup_logging()
    cfg = load_config()
    data_dir = PROJECT_ROOT / cfg["paths"]["data_dir"]
    engine = build_engine(cfg)

    with engine.begin() as conn:
        run_id = start_run(conn)
    log.info("Run %s started", run_id)

    status = "SUCCESS"
    try:
        with engine.begin() as conn:  # one transaction: all tables or none
            for workbook, sheet, table in SOURCES:
                df = read_sheet(data_dir, workbook, sheet)
                load_table(conn, df, table, run_id, workbook)
    except Exception:
        status = "FAILED"
        log.exception("Raw load failed; the raw tables were left unchanged")

    with engine.begin() as conn:
        finish_run(conn, run_id, status)
    log.info("Run %s finished: %s", run_id, status)
    if status == "FAILED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Apply the data-quality rules to the raw tables, then load staging and quarantine.

Run from the project root:  python src/run_dq.py

- Raw tables are only read, never changed.
- Re-running is safe: staging and quarantine are emptied and reloaded.
- Everything happens in ONE transaction. If anything fails, nothing changes.
- Results are written to audit.dq_result and audit.dq_summary, and to reports/dq_report.md.
"""
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from check_connection import build_engine, load_config
from dq_rules import check_unique_key, process_movements, process_sales, process_snapshot
from load_raw import finish_run

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"
REPORT_PATH = PROJECT_ROOT / "reports" / "dq_report.md"

# The business columns of each raw table (the load metadata columns are left out)
COLUMNS = {
    "sales_transactions": [
        "transaction_id", "transaction_datetime", "customer_id", "product_id", "quantity",
        "unit_price_ngn", "discount_pct", "gross_sales_ngn", "discount_amount_ngn",
        "net_sales_ngn", "sales_channel", "order_status",
    ],
    "customer_master": ["customer_id", "customer_name", "customer_type", "state", "city", "sales_territory"],
    "product_master": [
        "product_id", "product_name", "category", "brand", "list_price_ngn",
        "reorder_level_units", "unit_cost_ngn", "active_flag",
    ],
    "inventory_snapshot": [
        "inventory_record_id", "warehouse_id", "warehouse_name", "warehouse_state", "product_id",
        "on_hand_units", "reserved_units", "available_units", "reorder_level_units", "snapshot_date",
    ],
    "inventory_movements": [
        "movement_id", "movement_datetime", "warehouse_id", "product_id", "movement_type",
        "quantity_change", "reference_type", "reference_id", "approval_status",
    ],
}

log = logging.getLogger("run_dq")


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(LOG_DIR / "dq_run.log", encoding="utf-8")],
    )


def start_run(conn) -> int:
    result = conn.execute(
        text("INSERT INTO audit.pipeline_run (stage) OUTPUT INSERTED.run_id VALUES (:stage)"),
        {"stage": "data_quality"},
    )
    return int(result.scalar_one())


def read_raw(conn, table: str) -> pd.DataFrame:
    cols = ", ".join(COLUMNS[table])
    df = pd.read_sql(text(f"SELECT {cols} FROM raw.{table}"), conn)
    if df.empty:
        raise ValueError(f"raw.{table} is empty. Run python src/load_raw.py first.")
    return df


def strip_text(df: pd.DataFrame) -> pd.DataFrame:
    """Remove stray spaces from every text column (used for the reference tables)."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].str.strip()
    return out


def write_table(conn, schema: str, table: str, df: pd.DataFrame, run_id: int) -> None:
    """Empty the table, load the rows, and check the database holds the same number."""
    conn.execute(text(f"TRUNCATE TABLE {schema}.{table}"))
    df.assign(dq_run_id=run_id).to_sql(table, conn, schema=schema, if_exists="append", index=False, chunksize=5000)
    stored = conn.execute(
        text(f"SELECT COUNT(*) FROM {schema}.{table} WHERE dq_run_id = :run_id"), {"run_id": run_id}
    ).scalar_one()
    if stored != len(df):
        raise ValueError(f"{schema}.{table}: expected {len(df)} rows but found {stored}")


def log_results(conn, run_id: int, table: str, raw_rows: int, clean_rows: int, quarantined_rows: int, stats) -> None:
    if stats is not None:
        out = stats.assign(run_id=run_id, table_name=table)
        out = out[["run_id", "table_name", "rule_code", "outcome", "rows_affected", "net_sales_ngn_impact"]]
        out.to_sql("dq_result", conn, schema="audit", if_exists="append", index=False)
    conn.execute(
        text(
            "INSERT INTO audit.dq_summary (run_id, table_name, raw_rows, clean_rows, quarantined_rows) "
            "VALUES (:run_id, :table, :raw, :clean, :quarantined)"
        ),
        {"run_id": run_id, "table": table, "raw": raw_rows, "clean": clean_rows, "quarantined": quarantined_rows},
    )


def process_reference(conn, run_id: int, table: str, key: str, summary: list) -> pd.DataFrame:
    raw = read_raw(conn, table)
    check_unique_key(raw, key, table)
    clean = strip_text(raw)
    write_table(conn, "staging", table, clean, run_id)
    log_results(conn, run_id, table, len(raw), len(clean), 0, None)
    summary.append((table, len(raw), len(clean), 0, None))
    log.info("%s: %s rows -> staging (reference table, unique keys checked)", table, f"{len(raw):,}")
    return clean


def process_fact(conn, run_id: int, table: str, result, raw_rows: int, summary: list) -> None:
    write_table(conn, "staging", table, result.clean, run_id)
    write_table(conn, "quarantine", table, result.quarantined, run_id)
    log_results(conn, run_id, table, raw_rows, len(result.clean), len(result.quarantined), result.rule_stats)
    summary.append((table, raw_rows, len(result.clean), len(result.quarantined), result.rule_stats))
    log.info(
        "%s: %s raw = %s clean + %s quarantined",
        table, f"{raw_rows:,}", f"{len(result.clean):,}", f"{len(result.quarantined):,}",
    )


def write_report(run_id: int, summary: list) -> None:
    lines = [f"# Data-quality report (run {run_id})", ""]
    for table, raw_rows, clean_rows, quarantined_rows, stats in summary:
        lines += [f"## {table}", "", f"- Raw rows: {raw_rows:,}", f"- Clean (staging): {clean_rows:,}",
                  f"- Quarantined: {quarantined_rows:,}", f"- Reconciles: {raw_rows == clean_rows + quarantined_rows}", ""]
        if stats is not None:
            lines += ["```", stats.to_string(index=False), "```", ""]
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    log.info("Report written to %s", REPORT_PATH)


def main() -> None:
    setup_logging()
    cfg = load_config()
    try:
        valid_warehouses = set(cfg["reference"]["valid_warehouses"])
    except KeyError:
        raise SystemExit("config/config.yaml is missing reference -> valid_warehouses. Add it and retry.")
    engine = build_engine(cfg)

    with engine.begin() as conn:
        run_id = start_run(conn)
    log.info("Run %s started", run_id)

    status, summary = "SUCCESS", []
    try:
        with engine.begin() as conn:  # one transaction: everything or nothing
            process_reference(conn, run_id, "customer_master", "customer_id", summary)
            products = process_reference(conn, run_id, "product_master", "product_id", summary)
            valid_products = set(products["product_id"])

            raw = read_raw(conn, "sales_transactions")
            process_fact(conn, run_id, "sales_transactions", process_sales(raw, valid_products), len(raw), summary)

            raw = read_raw(conn, "inventory_snapshot")
            result = process_snapshot(raw, valid_products, valid_warehouses)
            process_fact(conn, run_id, "inventory_snapshot", result, len(raw), summary)

            raw = read_raw(conn, "inventory_movements")
            result = process_movements(raw, valid_products, valid_warehouses)
            process_fact(conn, run_id, "inventory_movements", result, len(raw), summary)
    except Exception:
        status = "FAILED"
        log.exception("Data-quality run failed; staging and quarantine were left unchanged")

    with engine.begin() as conn:
        finish_run(conn, run_id, status)
    log.info("Run %s finished: %s", run_id, status)
    if status == "FAILED":
        raise SystemExit(1)
    write_report(run_id, summary)


if __name__ == "__main__":
    main()

"""Checks on the source workbooks. They run before anything is loaded into SQL Server."""
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = {
    "Sales_Transactions": [
        "transaction_id", "transaction_datetime", "customer_id", "product_id", "quantity",
        "unit_price_ngn", "discount_pct", "gross_sales_ngn", "discount_amount_ngn",
        "net_sales_ngn", "sales_channel", "order_status",
    ],
    "Customer_Master": ["customer_id", "customer_name", "customer_type", "state", "city", "sales_territory"],
    "Product_Master": [
        "product_id", "product_name", "category", "brand", "list_price_ngn",
        "reorder_level_units", "unit_cost_ngn", "active_flag",
    ],
    "Inventory_Snapshot": [
        "inventory_record_id", "warehouse_id", "warehouse_name", "warehouse_state", "product_id",
        "on_hand_units", "reserved_units", "available_units", "reorder_level_units", "snapshot_date",
    ],
    "Inventory_Movements": [
        "movement_id", "movement_datetime", "warehouse_id", "product_id", "movement_type",
        "quantity_change", "reference_type", "reference_id", "approval_status",
    ],
}

NUMERIC_COLUMNS = {
    "Sales_Transactions": ["quantity", "unit_price_ngn", "discount_pct", "gross_sales_ngn", "discount_amount_ngn", "net_sales_ngn"],
    "Product_Master": ["list_price_ngn", "reorder_level_units", "unit_cost_ngn"],
    "Inventory_Snapshot": ["on_hand_units", "reserved_units", "available_units", "reorder_level_units"],
    "Inventory_Movements": ["quantity_change"],
}

DATETIME_COLUMNS = {
    "Sales_Transactions": ["transaction_datetime"],
    "Inventory_Movements": ["movement_datetime"],
}


class InputError(ValueError):
    """The source data is not in the shape the pipeline expects."""


def check_sheet(df: pd.DataFrame, sheet: str) -> None:
    """Raise InputError if the sheet is empty, has the wrong columns, or has the wrong data types."""
    expected = EXPECTED_COLUMNS[sheet]
    missing = [c for c in expected if c not in df.columns]
    unexpected = [c for c in df.columns if c not in expected]
    if missing:
        raise InputError(f"{sheet}: missing columns {missing}")
    if unexpected:
        raise InputError(f"{sheet}: unexpected columns {unexpected}")
    if df.empty:
        raise InputError(f"{sheet}: the sheet has no rows")
    for col in NUMERIC_COLUMNS.get(sheet, []):
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise InputError(f"{sheet}: column {col} should be numeric but contains text")
    for col in DATETIME_COLUMNS.get(sheet, []):
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            raise InputError(f"{sheet}: column {col} should hold dates and times")


def read_sheet(data_dir: Path, workbook: str, sheet: str) -> pd.DataFrame:
    """Read one sheet and check it. Every problem becomes a clear error message."""
    path = data_dir / workbook
    if not path.exists():
        raise FileNotFoundError(f"Input workbook not found: {path}")
    try:
        df = pd.read_excel(path, sheet_name=sheet)
    except Exception as exc:  # a missing sheet, a damaged file, a file that is not Excel
        raise InputError(f"{workbook}: cannot read sheet '{sheet}' ({exc})") from exc
    check_sheet(df, sheet)
    return df
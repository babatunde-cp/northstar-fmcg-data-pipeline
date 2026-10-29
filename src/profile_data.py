"""Profile the three source workbooks BEFORE any cleaning.

Run from the project root:  python src/profile_data.py
Writes a Markdown report to reports/profiling_report.md
"""
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
REPORT_PATH = PROJECT_ROOT / "reports" / "profiling_report.md"

WORKBOOKS = {
    "01_sales_transactions.xlsx": ["Sales_Transactions", "Customer_Master"],
    "02_product_inventory.xlsx": ["Product_Master", "Inventory_Snapshot"],
    "03_inventory_movements.xlsx": ["Inventory_Movements"],
}

# Column that should be unique in each sheet
KEYS = {
    "Sales_Transactions": "transaction_id",
    "Customer_Master": "customer_id",
    "Product_Master": "product_id",
    "Inventory_Snapshot": "inventory_record_id",
    "Inventory_Movements": "movement_id",
}

# Text columns whose distinct values we want to inspect
CATEGORICAL = {
    "Sales_Transactions": ["sales_channel", "order_status"],
    "Customer_Master": ["customer_type", "state", "sales_territory"],
    "Product_Master": ["category", "active_flag"],
    "Inventory_Snapshot": ["warehouse_id", "snapshot_date"],
    "Inventory_Movements": ["movement_type", "reference_type", "approval_status"],
}


def load_all() -> dict[str, pd.DataFrame]:
    """Read every sheet of every workbook into one dictionary."""
    frames = {}
    for filename, sheets in WORKBOOKS.items():
        path = DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Input workbook not found: {path}")
        for sheet in sheets:
            frames[sheet] = pd.read_excel(path, sheet_name=sheet)
    return frames


def profile_sheet(name: str, df: pd.DataFrame) -> list[str]:
    """Return Markdown lines describing one sheet."""
    lines = [f"## {name}", "", f"- Rows: {len(df):,}", f"- Columns: {df.shape[1]}", ""]

    lines += ["### Data types and nulls", "```"]
    summary = pd.DataFrame({"dtype": df.dtypes.astype(str), "nulls": df.isna().sum()})
    lines += [summary.to_string(), "```", ""]

    key = KEYS[name]
    dup_ids = int(df[key].duplicated().sum())
    lines += [f"### Key check: `{key}`", f"- Repeated key values: {dup_ids}", ""]

    for col in CATEGORICAL.get(name, []):
        counts = df[col].value_counts(dropna=False)
        lines += [f"### Distinct values: `{col}`", "```"]
        # repr() makes stray spaces and odd casing visible
        lines += [f"{v!r}: {n}" for v, n in counts.items()]
        lines += ["```", ""]

    numeric = df.select_dtypes("number")
    if not numeric.empty:
        lines += ["### Numeric ranges", "```", numeric.describe().T.to_string(), "```", ""]

    money_cols = [c for c in df.columns if c.endswith(("sales_ngn", "amount_ngn"))]
    if money_cols:
        lines += ["### Baseline totals (NGN, before any cleaning)", "```"]
        lines += [f"{c}: {df[c].sum():,.2f}" for c in money_cols]
        lines += ["```", ""]
    return lines


def orphan_count(child: pd.DataFrame, col: str, parent: pd.DataFrame, parent_col: str) -> int:
    """How many non-null child keys have no match in the parent table."""
    return int((~child[col].dropna().isin(parent[parent_col])).sum())


def relationship_checks(f: dict[str, pd.DataFrame]) -> list[str]:
    checks = [
        ("Sales_Transactions.customer_id -> Customer_Master", f["Sales_Transactions"], "customer_id", f["Customer_Master"], "customer_id"),
        ("Sales_Transactions.product_id -> Product_Master", f["Sales_Transactions"], "product_id", f["Product_Master"], "product_id"),
        ("Inventory_Snapshot.product_id -> Product_Master", f["Inventory_Snapshot"], "product_id", f["Product_Master"], "product_id"),
        ("Inventory_Movements.product_id -> Product_Master", f["Inventory_Movements"], "product_id", f["Product_Master"], "product_id"),
        ("Inventory_Movements.warehouse_id -> Inventory_Snapshot", f["Inventory_Movements"], "warehouse_id", f["Inventory_Snapshot"], "warehouse_id"),
    ]
    lines = ["## Relationship checks (keys with no match)", ""]
    for label, child, col, parent, pcol in checks:
        lines.append(f"- {label}: {orphan_count(child, col, parent, pcol)}")
    return lines + [""]


def main() -> None:
    frames = load_all()
    report = ["# Source data profiling report", ""]
    for name, df in frames.items():
        report += profile_sheet(name, df)
    report += relationship_checks(frames)

    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")
    print(f"Profiling report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()

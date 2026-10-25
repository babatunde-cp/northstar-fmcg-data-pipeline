"""Starter scaffold for the Northstar Consumer Goods data pipeline.

Start by implementing profile_workbooks(). Keep raw source data unchanged.
"""
from pathlib import Path
import logging
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "pipeline.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

WORKBOOKS = {
    "sales": DATA_DIR / "01_sales_transactions.xlsx",
    "inventory": DATA_DIR / "02_product_inventory.xlsx",
    "movements": DATA_DIR / "03_inventory_movements.xlsx",
}

def load_workbook_sheets(path: Path) -> dict[str, pd.DataFrame]:
    """Load all sheets from an Excel workbook. Add missing-file handling."""
    if not path.exists():
        raise FileNotFoundError(f"Input workbook not found: {path}")
    return pd.read_excel(path, sheet_name=None)

def profile_workbooks() -> None:
    """TODO: print/log sheet dimensions, dtypes, null counts and duplicate keys."""
    for name, path in WORKBOOKS.items():
        sheets = load_workbook_sheets(path)
        for sheet_name, df in sheets.items():
            print(f"\n{name} / {sheet_name}: {df.shape}")
            print(df.dtypes)
            print(df.isna().sum().sort_values(ascending=False).head(10))

if __name__ == "__main__":
    profile_workbooks()

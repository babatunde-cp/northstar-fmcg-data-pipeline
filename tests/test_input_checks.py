import pandas as pd
import pytest

from input_checks import (
    DATETIME_COLUMNS,
    EXPECTED_COLUMNS,
    NUMERIC_COLUMNS,
    InputError,
    check_sheet,
    read_sheet,
)

SHEET = "Sales_Transactions"


def valid_frame(sheet: str) -> pd.DataFrame:
    """One row of made-up data with the right columns and types."""
    row = {}
    for col in EXPECTED_COLUMNS[sheet]:
        if col in NUMERIC_COLUMNS.get(sheet, []):
            row[col] = 1
        elif col in DATETIME_COLUMNS.get(sheet, []):
            row[col] = pd.Timestamp("2025-01-01 10:00")
        else:
            row[col] = "x"
    return pd.DataFrame([row])


def write_workbook(path, sheet, df):
    df.to_excel(path, sheet_name=sheet, index=False)


# ---------------------------------------------------------------- the checks
@pytest.mark.parametrize("sheet", list(EXPECTED_COLUMNS))
def test_a_correct_sheet_passes(sheet):
    check_sheet(valid_frame(sheet), sheet)


def test_a_missing_column_is_rejected():
    df = valid_frame(SHEET).drop(columns=["quantity"])
    with pytest.raises(InputError, match="quantity"):
        check_sheet(df, SHEET)


def test_an_unexpected_column_is_rejected():
    df = valid_frame(SHEET).assign(notes="hello")
    with pytest.raises(InputError, match="notes"):
        check_sheet(df, SHEET)


def test_a_renamed_column_is_rejected():
    df = valid_frame(SHEET).rename(columns={"customer_id": "cust_id"})
    with pytest.raises(InputError, match="customer_id"):
        check_sheet(df, SHEET)


def test_an_empty_sheet_is_rejected():
    with pytest.raises(InputError, match="no rows"):
        check_sheet(valid_frame(SHEET).iloc[0:0], SHEET)


def test_text_in_a_numeric_column_is_rejected():
    df = valid_frame(SHEET).astype({"quantity": object})
    df.loc[0, "quantity"] = "ten"
    with pytest.raises(InputError, match="quantity"):
        check_sheet(df, SHEET)


def test_text_in_a_date_column_is_rejected():
    df = valid_frame(SHEET).astype({"transaction_datetime": object})
    df.loc[0, "transaction_datetime"] = "not a date"
    with pytest.raises(InputError, match="transaction_datetime"):
        check_sheet(df, SHEET)


# ------------------------------------------------------------ reading files
def test_a_good_workbook_is_read(tmp_path):
    write_workbook(tmp_path / "sales.xlsx", SHEET, valid_frame(SHEET))
    assert len(read_sheet(tmp_path, "sales.xlsx", SHEET)) == 1


def test_a_missing_workbook_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError, match="sales.xlsx"):
        read_sheet(tmp_path, "sales.xlsx", SHEET)


def test_a_missing_sheet_is_reported(tmp_path):
    write_workbook(tmp_path / "sales.xlsx", "Wrong_Name", valid_frame(SHEET))
    with pytest.raises(InputError, match="cannot read sheet"):
        read_sheet(tmp_path, "sales.xlsx", SHEET)


def test_a_file_that_is_not_excel_is_reported(tmp_path):
    (tmp_path / "sales.xlsx").write_text("this is not a spreadsheet")
    with pytest.raises(InputError, match="cannot read sheet"):
        read_sheet(tmp_path, "sales.xlsx", SHEET)


def test_a_workbook_with_the_wrong_columns_is_reported(tmp_path):
    write_workbook(tmp_path / "sales.xlsx", SHEET, valid_frame(SHEET).drop(columns=["order_status"]))
    with pytest.raises(InputError, match="order_status"):
        read_sheet(tmp_path, "sales.xlsx", SHEET)
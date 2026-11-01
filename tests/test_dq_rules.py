import pandas as pd
import pytest

from dq_rules import (
    check_unique_key,
    process_movements,
    process_sales,
    process_snapshot,
)

PRODUCTS = {"P001", "P002"}
WAREHOUSES = {"WH-LAG", "WH-ABJ"}


# ---------------------------------------------------------------- builders
def sale(**overrides):
    row = dict(
        transaction_id="S1",
        transaction_datetime=pd.Timestamp("2025-01-01 10:00"),
        customer_id="C001",
        product_id="P001",
        quantity=2,
        unit_price_ngn=100.0,
        discount_pct=0.1,
        gross_sales_ngn=200.0,
        discount_amount_ngn=20.0,
        net_sales_ngn=180.0,
        sales_channel="Online",
        order_status="Delivered",
    )
    row.update(overrides)
    return row


def snapshot(**overrides):
    row = dict(
        inventory_record_id="INV-1",
        warehouse_id="WH-LAG",
        product_id="P001",
        on_hand_units=100,
        reserved_units=10,
        available_units=90,
        snapshot_date="2025-12-31",
    )
    row.update(overrides)
    return row


def movement(**overrides):
    row = dict(
        movement_id="M1",
        warehouse_id="WH-LAG",
        product_id="P001",
        movement_type="RECEIPT",
        quantity_change=10,
        approval_status="Approved",
    )
    row.update(overrides)
    return row


def run_sales(*rows):
    return process_sales(pd.DataFrame(list(rows)), PRODUCTS)


def affected(result, code):
    stats = result.rule_stats.set_index("rule_code")
    return int(stats.loc[code, "rows_affected"])


# ------------------------------------------------------------------- sales
def test_good_sale_passes_untouched():
    r = run_sales(sale())
    assert len(r.clean) == 1 and len(r.quarantined) == 0
    assert (r.rule_stats["rows_affected"] == 0).all()


def test_labels_are_standardised():
    r = run_sales(sale(sales_channel=" field sales ", order_status="DELIVERED "))
    assert r.clean.iloc[0]["sales_channel"] == "Field Sales"
    assert r.clean.iloc[0]["order_status"] == "Delivered"
    assert affected(r, "S01_STANDARDISE_LABELS") == 1


def test_missing_customer_is_kept_and_flagged():
    r = run_sales(sale(customer_id=None))
    assert len(r.clean) == 1
    assert r.clean.iloc[0]["customer_id"] == "UNKNOWN"
    assert r.clean.iloc[0]["is_missing_customer"] == 1
    assert affected(r, "S02_MISSING_CUSTOMER") == 1


def test_reused_transaction_id_keeps_both_rows_and_flags_both():
    r = run_sales(sale(customer_id="C001"), sale(customer_id="C002"))
    assert len(r.clean) == 2 and len(r.quarantined) == 0
    assert r.clean["is_duplicate_transaction_id"].tolist() == [1, 1]
    assert affected(r, "S03_DUPLICATE_TRANSACTION_ID") == 2


def test_unknown_product_is_quarantined_with_original_values():
    r = run_sales(sale(product_id="P999", sales_channel=" online "))
    assert len(r.clean) == 0 and len(r.quarantined) == 1
    q = r.quarantined.iloc[0]
    assert q["reason_codes"] == "S04_UNKNOWN_PRODUCT"
    assert q["sales_channel"] == " online "  # raw value, not the fixed one


def test_negative_quantity_is_allowed_on_returned_orders():
    r = run_sales(sale(quantity=-2, order_status="RETURNED"))
    assert len(r.clean) == 1 and len(r.quarantined) == 0


def test_negative_quantity_on_other_orders_is_quarantined():
    r = run_sales(sale(quantity=-2, order_status="Delivered"))
    assert len(r.quarantined) == 1
    assert r.quarantined.iloc[0]["reason_codes"] == "S05_NEGATIVE_QTY_NOT_RETURN"


@pytest.mark.parametrize("discount, quarantined", [(1.0, 0), (0.0, 0), (1.25, 1), (-0.1, 1)])
def test_discount_range(discount, quarantined):
    r = run_sales(sale(discount_pct=discount))
    assert len(r.quarantined) == quarantined


def test_row_breaking_two_rules_lists_both_reasons():
    r = run_sales(sale(product_id="P999", discount_pct=1.5))
    assert r.quarantined.iloc[0]["reason_codes"] == "S04_UNKNOWN_PRODUCT;S06_DISCOUNT_OUT_OF_RANGE"
    assert len(r.quarantined) == 1  # one row, even though two rules failed


def test_sales_rows_reconcile_and_impact_is_reported():
    rows = [
        sale(transaction_id="S1"),
        sale(transaction_id="S2", product_id="P999", net_sales_ngn=500.0),
        sale(transaction_id="S3", discount_pct=2.0, net_sales_ngn=700.0),
    ]
    r = run_sales(*rows)
    assert len(r.clean) + len(r.quarantined) == 3
    stats = r.rule_stats.set_index("rule_code")
    assert stats.loc["S04_UNKNOWN_PRODUCT", "net_sales_ngn_impact"] == 500.0
    assert stats.loc["S06_DISCOUNT_OUT_OF_RANGE", "net_sales_ngn_impact"] == 700.0


# ---------------------------------------------------------------- snapshot
def run_snapshot(*rows):
    return process_snapshot(pd.DataFrame(list(rows)), PRODUCTS, WAREHOUSES)


def test_good_snapshot_row_gets_a_real_date():
    r = run_snapshot(snapshot())
    assert len(r.clean) == 1
    assert str(r.clean.iloc[0]["snapshot_date"]) == "2025-12-31"


@pytest.mark.parametrize(
    "overrides, code",
    [
        (dict(product_id="P999"), "I01_UNKNOWN_PRODUCT"),
        (dict(warehouse_id="WH-UNKNOWN"), "I02_UNKNOWN_WAREHOUSE"),
        (dict(on_hand_units=-5, reserved_units=0, available_units=-5), "I03_NEGATIVE_ON_HAND"),
        (dict(reserved_units=9999), "I04_AVAILABLE_MISMATCH"),
        (dict(snapshot_date=None), "I05_MISSING_SNAPSHOT_DATE"),
    ],
)
def test_bad_snapshot_rows_are_quarantined(overrides, code):
    r = run_snapshot(snapshot(**overrides))
    assert len(r.clean) == 0 and len(r.quarantined) == 1
    assert code in r.quarantined.iloc[0]["reason_codes"]


# --------------------------------------------------------------- movements
def run_movements(*rows):
    return process_movements(pd.DataFrame(list(rows)), PRODUCTS, WAREHOUSES)


def test_approval_status_is_standardised():
    r = run_movements(movement(approval_status="approved "))
    assert r.clean.iloc[0]["approval_status"] == "Approved"
    assert affected(r, "M01_STANDARDISE_LABELS") == 1


def test_unknown_product_movement_is_quarantined():
    r = run_movements(movement(product_id="P999"))
    assert len(r.quarantined) == 1


def test_reused_movement_id_is_kept_and_flagged():
    r = run_movements(movement(warehouse_id="WH-LAG"), movement(warehouse_id="WH-ABJ"))
    assert len(r.clean) == 2
    assert r.clean["is_duplicate_movement_id"].tolist() == [1, 1]


def test_zero_quantity_movement_is_kept_and_flagged():
    r = run_movements(movement(quantity_change=0))
    assert len(r.clean) == 1 and r.clean.iloc[0]["is_zero_quantity"] == 1


# ------------------------------------------------------- reference tables
def test_duplicate_reference_key_stops_the_pipeline():
    df = pd.DataFrame({"customer_id": ["C1", "C1", "C2"]})
    with pytest.raises(ValueError):
        check_unique_key(df, "customer_id", "customer_master")


def test_unique_reference_key_passes():
    check_unique_key(pd.DataFrame({"customer_id": ["C1", "C2"]}), "customer_id", "customer_master")

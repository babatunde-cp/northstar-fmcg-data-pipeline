"""Data-quality rules for the FMCG pipeline.

Every rule has one of three outcomes:
  FIX         correct the value automatically
  FLAG        keep the row and mark the problem with a 0/1 column
  QUARANTINE  hold the row back, with the reason(s) recorded

These functions use pandas only (no database), so they are easy to test.
Each process function returns a DQResult: clean rows, quarantined rows
(with their ORIGINAL raw values) and a table of how many rows each rule hit.
"""
from dataclasses import dataclass

import pandas as pd

FIX, FLAG, QUARANTINE = "FIX", "FLAG", "QUARANTINE"


@dataclass(frozen=True)
class Rule:
    code: str
    outcome: str
    description: str


SALES_RULES = [
    Rule("S01_STANDARDISE_LABELS", FIX, "Strip spaces and use Title Case in sales_channel and order_status"),
    Rule("S02_MISSING_CUSTOMER", FLAG, "No customer_id: keep the sale, set customer to UNKNOWN"),
    Rule("S03_DUPLICATE_TRANSACTION_ID", FLAG, "transaction_id used on more than one row: keep all, flag them"),
    Rule("S04_UNKNOWN_PRODUCT", QUARANTINE, "product_id not found in the product master"),
    Rule("S05_NEGATIVE_QTY_NOT_RETURN", QUARANTINE, "Negative quantity on an order that is not Returned"),
    Rule("S06_DISCOUNT_OUT_OF_RANGE", QUARANTINE, "discount_pct below 0 or above 1"),
]

SNAPSHOT_RULES = [
    Rule("I01_UNKNOWN_PRODUCT", QUARANTINE, "product_id not found in the product master"),
    Rule("I02_UNKNOWN_WAREHOUSE", QUARANTINE, "warehouse_id is not a known warehouse"),
    Rule("I03_NEGATIVE_ON_HAND", QUARANTINE, "on_hand_units is below zero"),
    Rule("I04_AVAILABLE_MISMATCH", QUARANTINE, "available_units does not equal on_hand_units minus reserved_units"),
    Rule("I05_MISSING_SNAPSHOT_DATE", QUARANTINE, "snapshot_date is missing or not a valid date"),
]

MOVEMENT_RULES = [
    Rule("M01_STANDARDISE_LABELS", FIX, "Strip spaces and use Title Case in approval_status"),
    Rule("M02_UNKNOWN_PRODUCT", QUARANTINE, "product_id not found in the product master"),
    Rule("M03_UNKNOWN_WAREHOUSE", QUARANTINE, "warehouse_id is not a known warehouse"),
    Rule("M04_DUPLICATE_MOVEMENT_ID", FLAG, "movement_id used on more than one row: keep all, flag them"),
    Rule("M05_ZERO_QUANTITY_MOVEMENT", FLAG, "quantity_change is zero: keep, flag for review"),
]


@dataclass
class DQResult:
    clean: pd.DataFrame
    quarantined: pd.DataFrame
    rule_stats: pd.DataFrame  # rule_code, outcome, rows_affected, net_sales_ngn_impact


# ---------------------------------------------------------------- helpers
def standardise_text(s: pd.Series) -> pd.Series:
    """Remove stray spaces and use Title Case ('  ONLINE ' -> 'Online')."""
    return s.str.strip().str.title()


def _changed(before: pd.Series, after: pd.Series) -> pd.Series:
    return before.notna() & before.ne(after)


def _stats(rules: list[Rule], masks: dict, impact: pd.Series | None = None) -> pd.DataFrame:
    rows = []
    for rule in rules:
        m = masks[rule.code]
        rows.append(
            {
                "rule_code": rule.code,
                "outcome": rule.outcome,
                "rows_affected": int(m.sum()),
                "net_sales_ngn_impact": None if impact is None else round(float(impact[m].sum()), 2),
            }
        )
    return pd.DataFrame(rows)


def _split(raw: pd.DataFrame, fixed: pd.DataFrame, rules: list[Rule], masks: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Send rows that broke any QUARANTINE rule to quarantine, the rest stay clean."""
    q_codes = [r.code for r in rules if r.outcome == QUARANTINE]
    q_frame = pd.DataFrame({c: masks[c] for c in q_codes})
    q_mask = q_frame.any(axis=1)

    quarantined = raw[q_mask].copy()  # original raw values, not the fixed ones
    if q_mask.any():
        reasons = q_frame[q_mask].apply(lambda r: ";".join(r.index[r.values]), axis=1)
    else:
        reasons = pd.Series([], dtype="object", index=quarantined.index)
    quarantined["reason_codes"] = reasons

    clean = fixed[~q_mask].copy()
    if len(clean) + len(quarantined) != len(raw):
        raise ValueError("Row counts do not reconcile: clean + quarantined != raw")
    return clean, quarantined


# ------------------------------------------------------------------ sales
def process_sales(raw: pd.DataFrame, valid_product_ids: set) -> DQResult:
    df = raw.copy()
    masks = {}

    # S01 FIX: labels. Done first, so later rules see clean labels.
    changed = pd.Series(False, index=df.index)
    for col in ("sales_channel", "order_status"):
        fixed = standardise_text(df[col])
        changed |= _changed(df[col], fixed)
        df[col] = fixed
    masks["S01_STANDARDISE_LABELS"] = changed

    # S02 FLAG: missing customer
    missing = df["customer_id"].isna() | df["customer_id"].fillna("").str.strip().eq("")
    masks["S02_MISSING_CUSTOMER"] = missing
    df["customer_id"] = df["customer_id"].where(~missing, "UNKNOWN")
    df["is_missing_customer"] = missing.astype(int)

    # S03 FLAG: reused transaction id (all rows that share it are flagged)
    dup = df["transaction_id"].duplicated(keep=False)
    masks["S03_DUPLICATE_TRANSACTION_ID"] = dup
    df["is_duplicate_transaction_id"] = dup.astype(int)

    # QUARANTINE rules
    masks["S04_UNKNOWN_PRODUCT"] = ~df["product_id"].isin(valid_product_ids)
    masks["S05_NEGATIVE_QTY_NOT_RETURN"] = (df["quantity"] < 0) & (df["order_status"] != "Returned")
    masks["S06_DISCOUNT_OUT_OF_RANGE"] = (df["discount_pct"] < 0) | (df["discount_pct"] > 1)

    clean, quarantined = _split(raw, df, SALES_RULES, masks)
    stats = _stats(SALES_RULES, masks, impact=raw["net_sales_ngn"])
    return DQResult(clean, quarantined, stats)


# -------------------------------------------------------------- snapshot
def process_snapshot(raw: pd.DataFrame, valid_product_ids: set, valid_warehouse_ids: set) -> DQResult:
    df = raw.copy()
    masks = {}

    masks["I01_UNKNOWN_PRODUCT"] = ~df["product_id"].isin(valid_product_ids)
    masks["I02_UNKNOWN_WAREHOUSE"] = ~df["warehouse_id"].isin(valid_warehouse_ids)
    masks["I03_NEGATIVE_ON_HAND"] = df["on_hand_units"] < 0
    masks["I04_AVAILABLE_MISMATCH"] = (df["on_hand_units"] - df["reserved_units"]) != df["available_units"]

    parsed = pd.to_datetime(df["snapshot_date"], errors="coerce")
    masks["I05_MISSING_SNAPSHOT_DATE"] = parsed.isna()
    df["snapshot_date"] = parsed.dt.date  # text -> real date for the clean table

    clean, quarantined = _split(raw, df, SNAPSHOT_RULES, masks)
    return DQResult(clean, quarantined, _stats(SNAPSHOT_RULES, masks))


# ------------------------------------------------------------- movements
def process_movements(raw: pd.DataFrame, valid_product_ids: set, valid_warehouse_ids: set) -> DQResult:
    df = raw.copy()
    masks = {}

    fixed = standardise_text(df["approval_status"])
    masks["M01_STANDARDISE_LABELS"] = _changed(df["approval_status"], fixed)
    df["approval_status"] = fixed

    masks["M02_UNKNOWN_PRODUCT"] = ~df["product_id"].isin(valid_product_ids)
    masks["M03_UNKNOWN_WAREHOUSE"] = ~df["warehouse_id"].isin(valid_warehouse_ids)

    dup = df["movement_id"].duplicated(keep=False)
    masks["M04_DUPLICATE_MOVEMENT_ID"] = dup
    df["is_duplicate_movement_id"] = dup.astype(int)

    zero = df["quantity_change"] == 0
    masks["M05_ZERO_QUANTITY_MOVEMENT"] = zero
    df["is_zero_quantity"] = zero.astype(int)

    clean, quarantined = _split(raw, df, MOVEMENT_RULES, masks)
    return DQResult(clean, quarantined, _stats(MOVEMENT_RULES, masks))


# ------------------------------------------------------- reference tables
def check_unique_key(df: pd.DataFrame, key: str, table: str) -> None:
    """Reference tables must have unique keys. If not, stop the pipeline."""
    repeated = int(df[key].duplicated().sum())
    if repeated:
        raise ValueError(f"{table}: {repeated} repeated values in {key}; reference data must be unique")

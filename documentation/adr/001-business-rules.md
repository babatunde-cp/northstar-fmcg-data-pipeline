# ADR 001: Data-quality rules and how problem rows are handled

- **Status:** Accepted
- **Date:** 2026-11-01

## Context

Profiling the five source sheets (see `06_Profiling_Findings.md`) showed problems in keys,
labels, ranges and statuses. We need a consistent, explainable way to deal with each one,
without silently deleting data or understating sales.

## Decision

Every rule has one of three outcomes:

| Outcome | Meaning |
|---|---|
| **FIX** | Correct the value automatically |
| **FLAG** | Keep the row and mark the problem with a 0/1 column |
| **QUARANTINE** | Hold the row back, stored with its original values and a reason code |

Raw tables are never changed. Rules read `raw`, then write `staging` (clean rows) and
`quarantine` (rejected rows). Raw rows = staging rows + quarantined rows, always.

### Sales (`raw.sales_transactions`)

| Rule | Outcome | Rows | Why |
|---|---|---|---|
| S01 Standardise `sales_channel` and `order_status` | FIX | 240 | Same value typed several ways (" online ", "RETURNED"). Done first so later rules see clean labels. |
| S02 Missing `customer_id` | FLAG | 110 | The sale is real revenue. Linked to customer `UNKNOWN`. |
| S03 Reused `transaction_id` | FLAG | 160 (80 IDs) | The two rows sharing an ID are different sales (different customer, date, product, price), so they are not copies. Removing them would understate sales. Both rows are kept, each gets its own `sales_key`. |
| S04 Product not in product master | QUARANTINE | 90 | Cannot be categorised or costed. |
| S05 Negative quantity on a non-Returned order | QUARANTINE | 557 | Negative quantities only make sense for returns. |
| S06 `discount_pct` outside 0 to 1 | QUARANTINE | 120 | A discount above 100% is impossible. |

767 distinct rows are quarantined (a row can break more than one rule).

### Inventory snapshot (`raw.inventory_snapshot`)

All QUARANTINE: unknown product (1), unknown warehouse (1), negative on-hand (1),
`available_units` not equal to on-hand minus reserved (2), missing snapshot date (1).
Five distinct rows.

### Inventory movements (`raw.inventory_movements`)

| Rule | Outcome | Rows |
|---|---|---|
| M01 Standardise `approval_status` | FIX | 40 |
| M02 Product not in product master | QUARANTINE | 30 |
| M03 Unknown warehouse | QUARANTINE | 0 |
| M04 Reused `movement_id` | FLAG | 50 (25 IDs) |
| M05 Zero `quantity_change` | FLAG | 35 |

### Reference tables

`customer_master` and `product_master` must have unique keys. If not, the pipeline stops.

## Consequences

- Quarantined rows leave reported totals. Every run records the naira value held in
  quarantine per rule (`audit.dq_result`) so the gap is visible. Quarantined negative-quantity
  rows carry negative values, so quarantining them raises reported net sales.
- Reused IDs stay visible through the flag columns, so the source owner can be told.
- Quarantined rows can be released after the rule or the source data is corrected.
- Known warehouses are a reference list in `config.yaml`, not hard-coded in the rules.

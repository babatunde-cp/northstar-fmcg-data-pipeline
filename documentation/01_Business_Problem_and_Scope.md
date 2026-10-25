# Business Problem, Objectives & Scope

## Business problem
Northstar Consumer Goods Ltd. uses separate spreadsheets for transactions, product/warehouse stock snapshots and inventory movements. Reporting is slow and unreliable because records may be duplicated, key fields may be missing, product IDs may not exist in the master data, status/channel labels are inconsistent, and some quantities or discount values are invalid. Leadership needs a consistent view of sales performance and inventory risk.

## Stakeholders
- Commercial Director: revenue, discounting, product and channel performance.
- Warehouse Manager: available stock, movements, replenishment and stock accuracy.
- Sales Operations Analyst: order status, customer segments, sales territory and trends.
- Finance Controller: net sales, discount cost, returns and reconciliation.

## Objectives
1. Ingest all three workbooks repeatably using Python.
2. Preserve source data in raw tables before transformation.
3. Profile data and produce a data-quality report.
4. Validate keys, types, domains, duplicates, nulls and business rules.
5. Build curated tables with clear grain and documented rules.
6. Load data into a relational database (SQLite first; PostgreSQL as an extension).
7. Build SQL views or reporting tables suitable for Power BI.
8. Reconcile totals and document rejected/quarantined records.
9. Make the pipeline rerunnable and idempotent.
10. Add logging, configuration, exception handling and tests.

## In scope
- Sales transactions, customer master, product master, inventory snapshot, inventory movements.
- Data cleaning, validation, transformation, database loading, SQL analytics and Power BI model.
- Pipeline documentation, testing and data-quality metrics.

## Out of scope
- Real-time streaming, live ERP integration, machine-learning forecasting, real business data, and production cloud deployment.

## Business rules to test (do not assume without documenting)
- Transaction IDs should be unique.
- Customer and product keys should match master tables.
- Discount percentage should be between 0 and 1 (0%–100%).
- Quantities may be negative only where a documented return/reversal rule allows it.
- Gross sales should reconcile to quantity × unit price, subject to agreed rounding.
- Net sales should reconcile to gross sales minus discount amount.
- Inventory quantities should not be negative unless the business explicitly permits backorders/adjustments.
- Available units should reconcile to on-hand minus reserved units.
- Inventory movements should use valid product and warehouse keys.
- Movement type and sign should agree with documented movement conventions.
- Approval status and order status should be standardized.

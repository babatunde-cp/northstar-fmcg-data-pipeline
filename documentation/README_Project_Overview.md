# FMCG Sales & Inventory Data Engineering Pipeline
## Project level
Professional portfolio level (C) with approximately 80,000 operational records (B).

## Fictional business
**Northstar Consumer Goods Ltd.** is a fictional Nigerian FMCG distributor serving retailers, wholesalers, distributors and supermarkets through field sales, phone orders, online orders and retail counter sales. It operates four warehouses and sells 30 products across multiple categories.

## Business problem
Sales, product master data, stock snapshots and inventory movements are maintained in separate spreadsheets. Management cannot consistently reconcile sales with inventory, identify stock-out risks, distinguish true demand from returns/cancellations, or trust revenue and stock reports. Manual consolidation creates duplicate IDs, missing keys, inconsistent labels and invalid values.

## Objective
Build a repeatable Python-based pipeline that ingests the three Excel workbooks, validates and cleans the data, loads raw and curated data into a relational database, applies business rules, and prepares reliable reporting tables for Power BI.

## Architecture
Excel workbooks -> Python ingestion -> raw database tables -> validation/cleaning/transformation -> curated relational tables/views -> Power BI dashboard.
Optional extension: Apache Airflow orchestrates scheduled pipeline tasks. Optional extension: PySpark is only introduced if scale/processing requirements justify distributed processing; pandas is appropriate for this dataset.

## Dataset inventory
- `01_sales_transactions.xlsx`: 65,000 sales transactions plus 500 customers in a lookup sheet.
- `02_product_inventory.xlsx`: 30 products plus 120 product/warehouse inventory snapshot rows.
- `03_inventory_movements.xlsx`: 15,000 inventory movement records.
- Total operational rows: approximately 80,650, excluding lookup/master data.
- Period: 1 Jan 2025 – 31 Dec 2025 (snapshot dated 31 Dec 2025).

## Important note
This is synthetic training data, not real company or customer data. Some issues are intentionally planted. Not every status/quantity combination is necessarily valid; identify and document assumptions rather than silently deleting records.

# Architecture & Technology Decisions

## Recommended first version
Excel files → Python (pandas) → SQLite → SQL views → Power BI

Why: pandas is approachable and sufficient for ~80,000 operational rows; SQLite removes setup friction while still teaching relational database concepts. PostgreSQL can replace SQLite once the first pipeline works.

## What each tool does
- Python: coordinates the workflow and applies validation/transformation rules.
- pandas: reads Excel, profiles data and transforms tabular data.
- SQL / database: stores raw and curated data, enforces relational structure and supports analytical queries.
- Power BI: visualizes curated outputs for business users.
- Apache Airflow (later): schedules and orchestrates pipeline tasks, retries failures and tracks task status.
- Apache Spark / PySpark (later): distributed processing for data volumes/operations that exceed practical single-machine processing.
- Git/GitHub: version control, collaboration and portfolio evidence.

## Suggested project layout
```
FMCG_Sales_Inventory_Data_Engineering_Project/
├── data/
│   ├── 01_sales_transactions.xlsx
│   ├── 02_product_inventory.xlsx
│   └── 03_inventory_movements.xlsx
├── documentation/
├── starter_code/
├── reports/
├── logs/
├── tests/
├── requirements.txt
└── README.md
```

## Non-negotiable engineering principles
- Preserve raw data; transform into separate curated tables.
- Make transformations deterministic and testable.
- Validate keys and numeric business rules.
- Keep a quarantine/reject reason for bad records.
- Never put credentials in source control.
- Log run ID, source counts, output counts, failures and duration.
- Reconcile row counts and metrics across stages.

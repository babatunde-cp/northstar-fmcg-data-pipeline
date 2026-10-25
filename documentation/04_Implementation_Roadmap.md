# Implementation Roadmap

Work through these phases in order. Commit your work to Git after each meaningful milestone.

## Phase 0 — Environment and repository
- Create a virtual environment.
- Install pandas, openpyxl, SQLAlchemy, pytest, and a database driver if using PostgreSQL.
- Keep raw data unchanged; use `.gitignore` for virtual environments, secrets, logs and generated local databases where appropriate.
- Create a configuration file for paths and database connection settings.

## Phase 1 — Explore and profile
- Read each workbook with pandas.
- Inspect sheet names, dimensions, data types, null counts, duplicate keys and distinct categorical values.
- Create a profiling report before cleaning.
- Record source row counts and initial financial totals.

## Phase 2 — Ingestion
- Build reusable functions to load each sheet.
- Add logging, exceptions for missing files/sheets, and source-file metadata.
- Load unmodified records into raw database tables. Include `ingested_at` and `source_file` metadata in the database layer.

## Phase 3 — Data quality
- Validate required fields, uniqueness, foreign keys, numeric ranges, allowed values and arithmetic.
- Standardize whitespace/case in categories, channels and statuses.
- Do not silently delete records. Send invalid records to quarantine tables/files with reason codes.
- Write a data-quality summary with counts by rule.

## Phase 4 — Transformation and modelling
- Define table grain explicitly.
- Suggested relational tables: `raw_sales_transactions`, `raw_customers`, `raw_products`, `raw_inventory_snapshot`, `raw_inventory_movements`; curated `fact_sales`, `dim_customer`, `dim_product`, `fact_inventory_snapshot`, `fact_inventory_movement`.
- Decide and document how cancelled, pending, returned and negative-quantity records contribute to sales metrics.
- Use primary keys, foreign keys, constraints and indexes where appropriate.

## Phase 5 — Database loading
- Start with SQLite for local development; PostgreSQL is a useful portfolio extension.
- Use transactions and controlled upserts/inserts.
- Make reruns idempotent: running the same input twice must not double-count data.
- Track a pipeline run ID, start/end timestamps, status and row counts.

## Phase 6 — SQL analysis
- Build views for monthly sales, product performance, customer performance, stock below reorder, movement summary and data-quality KPIs.
- Validate each view against hand-calculated sample records.

## Phase 7 — Power BI
- Connect Power BI to curated tables/views.
- Build a star-schema-style model with clear relationships and a proper date table.
- Add KPI cards, trend lines, category/brand breakdowns, warehouse inventory, reorder alerts and data-quality page.
- Clearly label metrics and document exclusions.

## Phase 8 — Tests and operational quality
- Unit-test transformations and validation rules.
- Test missing files, duplicate inputs, unexpected columns and malformed data.
- Add structured logging and a pipeline run report.
- Confirm idempotency by running the same batch twice.

## Phase 9 — Orchestration (optional Airflow)
- Introduce Airflow only after the Python pipeline works from the command line.
- Create tasks such as `check_inputs` → `ingest_raw` → `validate` → `transform` → `load_curated` → `quality_report`.
- Configure retries, dependencies and task logs.
- Airflow orchestrates tasks; it is not the database or transformation language.

## Phase 10 — Scale extension (optional PySpark)
- Do not start with Spark. This dataset is comfortably manageable with pandas on a typical laptop.
- Reimplement one transformation in PySpark only to learn distributed DataFrame operations and compare outputs/performance.
- Explain the scale at which distributed compute would become useful.

## Definition of done
- Three workbooks are processed through a reproducible pipeline.
- Raw source values remain auditable.
- Data-quality issues are measured and quarantined/documented.
- Curated database tables and SQL views exist.
- Power BI reports answer business questions.
- Tests pass; pipeline reruns without duplicate loading.
- README explains architecture, assumptions, results, limitations and future improvements.

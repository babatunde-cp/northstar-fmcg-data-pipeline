/* ------------------------------------------------------------
   04_create_curated_model.sql
   Curated layer: a star schema for reporting (Power BI reads this).
   Dimensions describe things (who, what, where, when).
   Facts record events (sales, stock counts, stock movements).
   Dimension keys are small surrogate integers; -1 is the "unknown" member.
   Safe to run more than once.
   ------------------------------------------------------------ */
USE FMCG_Pipeline;
GO

/* ---------- dimensions ---------- */
IF OBJECT_ID('curated.dim_date') IS NULL
CREATE TABLE curated.dim_date (
    date_key            INT          NOT NULL PRIMARY KEY,   -- 20250131
    full_date           DATE         NOT NULL UNIQUE,
    calendar_year       INT          NOT NULL,
    calendar_quarter    INT          NOT NULL,
    calendar_month      INT          NOT NULL,
    calendar_month_name VARCHAR(20)  NOT NULL,
    year_month          CHAR(7)      NOT NULL,               -- 2025-01
    day_of_month        INT          NOT NULL,
    day_of_week         INT          NOT NULL,               -- 1 = Monday ... 7 = Sunday
    day_name            VARCHAR(20)  NOT NULL,
    is_weekend          BIT          NOT NULL,
    iso_week            INT          NOT NULL
);
GO

IF OBJECT_ID('curated.dim_customer') IS NULL
CREATE TABLE curated.dim_customer (
    customer_key    INT          NOT NULL PRIMARY KEY,
    customer_id     VARCHAR(50)  NOT NULL UNIQUE,            -- business key from the source
    customer_name   VARCHAR(100) NOT NULL,
    customer_type   VARCHAR(50)  NOT NULL,
    state           VARCHAR(50)  NOT NULL,
    city            VARCHAR(100) NOT NULL,
    sales_territory VARCHAR(50)  NOT NULL,
    is_unknown      BIT          NOT NULL
);
GO

IF OBJECT_ID('curated.dim_product') IS NULL
CREATE TABLE curated.dim_product (
    product_key         INT           NOT NULL PRIMARY KEY,
    product_id          VARCHAR(50)   NOT NULL UNIQUE,
    product_name        VARCHAR(200)  NOT NULL,
    category            VARCHAR(100)  NOT NULL,
    brand               VARCHAR(100)  NOT NULL,
    list_price_ngn      DECIMAL(18,2) NOT NULL,
    unit_cost_ngn       DECIMAL(18,2) NOT NULL,
    reorder_level_units INT           NOT NULL,
    active_flag         BIT           NOT NULL
);
GO

IF OBJECT_ID('curated.dim_warehouse') IS NULL
CREATE TABLE curated.dim_warehouse (
    warehouse_key   INT          NOT NULL PRIMARY KEY,
    warehouse_id    VARCHAR(50)  NOT NULL UNIQUE,
    warehouse_name  VARCHAR(100) NOT NULL,
    warehouse_state VARCHAR(50)  NOT NULL
);
GO

IF OBJECT_ID('curated.dim_sales_channel') IS NULL
CREATE TABLE curated.dim_sales_channel (
    channel_key   INT         NOT NULL PRIMARY KEY,
    sales_channel VARCHAR(50) NOT NULL UNIQUE
);
GO

IF OBJECT_ID('curated.dim_order_status') IS NULL
CREATE TABLE curated.dim_order_status (
    status_key        INT         NOT NULL PRIMARY KEY,
    order_status      VARCHAR(20) NOT NULL UNIQUE,
    status_group      VARCHAR(20) NOT NULL,                  -- Completed / Returned / Open / Cancelled
    counts_as_revenue BIT         NOT NULL
);
GO

/* ---------- facts ---------- */
/* Grain: one accepted sales transaction line */
IF OBJECT_ID('curated.fact_sales') IS NULL
CREATE TABLE curated.fact_sales (
    sales_key                   INT           NOT NULL PRIMARY KEY,
    transaction_id              VARCHAR(50)   NOT NULL,      -- not unique in the source
    date_key                    INT           NOT NULL REFERENCES curated.dim_date(date_key),
    customer_key                INT           NOT NULL REFERENCES curated.dim_customer(customer_key),
    product_key                 INT           NOT NULL REFERENCES curated.dim_product(product_key),
    channel_key                 INT           NOT NULL REFERENCES curated.dim_sales_channel(channel_key),
    status_key                  INT           NOT NULL REFERENCES curated.dim_order_status(status_key),
    transaction_datetime        DATETIME2     NOT NULL,
    quantity                    INT           NOT NULL,
    unit_price_ngn              DECIMAL(18,2) NOT NULL,
    discount_pct                DECIMAL(9,4)  NOT NULL,
    gross_sales_ngn             DECIMAL(18,2) NOT NULL,
    discount_amount_ngn         DECIMAL(18,2) NOT NULL,
    net_sales_ngn               DECIMAL(18,2) NOT NULL,
    is_missing_customer         BIT           NOT NULL,
    is_duplicate_transaction_id BIT           NOT NULL
);
GO

/* Grain: one product in one warehouse on one snapshot date */
IF OBJECT_ID('curated.fact_inventory_snapshot') IS NULL
CREATE TABLE curated.fact_inventory_snapshot (
    snapshot_key        INT          NOT NULL PRIMARY KEY,
    inventory_record_id VARCHAR(50)  NOT NULL UNIQUE,
    date_key            INT          NOT NULL REFERENCES curated.dim_date(date_key),
    product_key         INT          NOT NULL REFERENCES curated.dim_product(product_key),
    warehouse_key       INT          NOT NULL REFERENCES curated.dim_warehouse(warehouse_key),
    on_hand_units       INT          NOT NULL,
    reserved_units      INT          NOT NULL,
    available_units     INT          NOT NULL,
    reorder_level_units INT          NOT NULL,
    is_below_reorder    BIT          NOT NULL                -- available_units < reorder_level_units
);
GO

/* Grain: one stock movement event */
IF OBJECT_ID('curated.fact_inventory_movement') IS NULL
CREATE TABLE curated.fact_inventory_movement (
    movement_key             INT          NOT NULL PRIMARY KEY,
    movement_id              VARCHAR(50)  NOT NULL,          -- not unique in the source
    date_key                 INT          NOT NULL REFERENCES curated.dim_date(date_key),
    product_key              INT          NOT NULL REFERENCES curated.dim_product(product_key),
    warehouse_key            INT          NOT NULL REFERENCES curated.dim_warehouse(warehouse_key),
    movement_datetime        DATETIME2    NOT NULL,
    movement_type            VARCHAR(50)  NOT NULL,
    reference_type           VARCHAR(50)  NOT NULL,
    reference_id             VARCHAR(50)  NOT NULL,
    approval_status          VARCHAR(30)  NOT NULL,
    quantity_change          INT          NOT NULL,
    is_duplicate_movement_id BIT          NOT NULL,
    is_zero_quantity         BIT          NOT NULL
);
GO

/* ---------- indexes on the join columns Power BI and queries use most ---------- */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_fact_sales_date' AND object_id = OBJECT_ID('curated.fact_sales'))
    CREATE INDEX ix_fact_sales_date ON curated.fact_sales(date_key);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_fact_sales_customer' AND object_id = OBJECT_ID('curated.fact_sales'))
    CREATE INDEX ix_fact_sales_customer ON curated.fact_sales(customer_key);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_fact_sales_product' AND object_id = OBJECT_ID('curated.fact_sales'))
    CREATE INDEX ix_fact_sales_product ON curated.fact_sales(product_key);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_fact_movement_date' AND object_id = OBJECT_ID('curated.fact_inventory_movement'))
    CREATE INDEX ix_fact_movement_date ON curated.fact_inventory_movement(date_key);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_fact_movement_product' AND object_id = OBJECT_ID('curated.fact_inventory_movement'))
    CREATE INDEX ix_fact_movement_product ON curated.fact_inventory_movement(product_key);
GO

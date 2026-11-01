/* ------------------------------------------------------------
   02_create_raw_and_audit_tables.sql
   Raw layer: exact copies of the source sheets. 
   No primary keys and no constraints on purpose,
   Bad data still loads and can be investigated later. 
   Safe to run more than once.
   ------------------------------------------------------------ */
USE FMCG_Pipeline;
GO

/* ---------- audit: one row per pipeline run, one row per table load ---------- */
IF OBJECT_ID('audit.pipeline_run') IS NULL
CREATE TABLE audit.pipeline_run (
    run_id      INT IDENTITY(1,1) PRIMARY KEY,
    stage       VARCHAR(50)  NOT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'RUNNING',
    started_at  DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME(),
    finished_at DATETIME2    NULL
);
GO

IF OBJECT_ID('audit.load_log') IS NULL
CREATE TABLE audit.load_log (
    log_id      INT IDENTITY(1,1) PRIMARY KEY,
    run_id      INT          NOT NULL REFERENCES audit.pipeline_run(run_id),
    table_name  VARCHAR(100) NOT NULL,
    source_rows INT          NOT NULL,
    loaded_rows INT          NOT NULL,
    logged_at   DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

/* ---------- raw tables (last 3 columns of each are load metadata) ---------- */
IF OBJECT_ID('raw.sales_transactions') IS NULL
CREATE TABLE raw.sales_transactions (
    transaction_id       VARCHAR(50)   NULL,
    transaction_datetime DATETIME2     NULL,
    customer_id          VARCHAR(50)   NULL,
    product_id           VARCHAR(50)   NULL,
    quantity             INT           NULL,
    unit_price_ngn       DECIMAL(18,2) NULL,
    discount_pct         DECIMAL(9,4)  NULL,
    gross_sales_ngn      DECIMAL(18,2) NULL,
    discount_amount_ngn  DECIMAL(18,2) NULL,
    net_sales_ngn        DECIMAL(18,2) NULL,
    sales_channel        VARCHAR(50)   NULL,
    order_status         VARCHAR(50)   NULL,
    load_run_id          INT           NULL,
    source_file          VARCHAR(100)  NULL,
    loaded_at            DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('raw.customer_master') IS NULL
CREATE TABLE raw.customer_master (
    customer_id     VARCHAR(50)  NULL,
    customer_name   VARCHAR(100) NULL,
    customer_type   VARCHAR(50)  NULL,
    state           VARCHAR(50)  NULL,
    city            VARCHAR(100) NULL,
    sales_territory VARCHAR(50)  NULL,
    load_run_id     INT          NULL,
    source_file     VARCHAR(100) NULL,
    loaded_at       DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('raw.product_master') IS NULL
CREATE TABLE raw.product_master (
    product_id          VARCHAR(50)   NULL,
    product_name        VARCHAR(200)  NULL,
    category            VARCHAR(100)  NULL,
    brand               VARCHAR(100)  NULL,
    list_price_ngn      DECIMAL(18,2) NULL,
    reorder_level_units INT           NULL,
    unit_cost_ngn       DECIMAL(18,2) NULL,
    active_flag         BIT           NULL,
    load_run_id         INT           NULL,
    source_file         VARCHAR(100)  NULL,
    loaded_at           DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('raw.inventory_snapshot') IS NULL
CREATE TABLE raw.inventory_snapshot (
    inventory_record_id VARCHAR(50)  NULL,
    warehouse_id        VARCHAR(50)  NULL,
    warehouse_name      VARCHAR(100) NULL,
    warehouse_state     VARCHAR(50)  NULL,
    product_id          VARCHAR(50)  NULL,
    on_hand_units       INT          NULL,
    reserved_units      INT          NULL,
    available_units     INT          NULL,
    reorder_level_units INT          NULL,
    snapshot_date       VARCHAR(20)  NULL,   -- kept as text; converted to DATE in the curated layer
    load_run_id         INT          NULL,
    source_file         VARCHAR(100) NULL,
    loaded_at           DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('raw.inventory_movements') IS NULL
CREATE TABLE raw.inventory_movements (
    movement_id       VARCHAR(50)  NULL,
    movement_datetime DATETIME2    NULL,
    warehouse_id      VARCHAR(50)  NULL,
    product_id        VARCHAR(50)  NULL,
    movement_type     VARCHAR(50)  NULL,
    quantity_change   INT          NULL,
    reference_type    VARCHAR(50)  NULL,
    reference_id      VARCHAR(50)  NULL,
    approval_status   VARCHAR(50)  NULL,
    load_run_id       INT          NULL,
    source_file       VARCHAR(100) NULL,
    loaded_at         DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

/* ------------------------------------------------------------
   03_create_staging_and_quarantine_tables.sql
   staging    : validated, typed rows that passed the data-quality rules
   quarantine : rows held back, stored with their ORIGINAL raw values
                plus the reason code(s)
   audit      : results of each data-quality run
   CHECK constraints repeat the key rules as a database safety net.
   Safe to run more than once.
   ------------------------------------------------------------ */
USE FMCG_Pipeline;
GO

IF SCHEMA_ID('staging') IS NULL EXEC('CREATE SCHEMA staging');
GO

/* ---------- audit: results of each data-quality run ---------- */
IF OBJECT_ID('audit.dq_result') IS NULL
CREATE TABLE audit.dq_result (
    dq_result_id         INT IDENTITY(1,1) PRIMARY KEY,
    run_id               INT           NOT NULL REFERENCES audit.pipeline_run(run_id),
    table_name           VARCHAR(100)  NOT NULL,
    rule_code            VARCHAR(60)   NOT NULL,
    outcome              VARCHAR(20)   NOT NULL,
    rows_affected        INT           NOT NULL,
    net_sales_ngn_impact DECIMAL(18,2) NULL,      -- sales rules only
    logged_at            DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('audit.dq_summary') IS NULL
CREATE TABLE audit.dq_summary (
    dq_summary_id    INT IDENTITY(1,1) PRIMARY KEY,
    run_id           INT          NOT NULL REFERENCES audit.pipeline_run(run_id),
    table_name       VARCHAR(100) NOT NULL,
    raw_rows         INT          NOT NULL,
    clean_rows       INT          NOT NULL,
    quarantined_rows INT          NOT NULL,
    logged_at        DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT ck_dq_summary_reconciles CHECK (raw_rows = clean_rows + quarantined_rows)
);
GO

/* ---------- staging ---------- */
IF OBJECT_ID('staging.customer_master') IS NULL
CREATE TABLE staging.customer_master (
    customer_id     VARCHAR(50)  NOT NULL PRIMARY KEY,
    customer_name   VARCHAR(100) NOT NULL,
    customer_type   VARCHAR(50)  NOT NULL,
    state           VARCHAR(50)  NOT NULL,
    city            VARCHAR(100) NOT NULL,
    sales_territory VARCHAR(50)  NOT NULL,
    dq_run_id       INT          NOT NULL REFERENCES audit.pipeline_run(run_id)
);
GO

IF OBJECT_ID('staging.product_master') IS NULL
CREATE TABLE staging.product_master (
    product_id          VARCHAR(50)   NOT NULL PRIMARY KEY,
    product_name        VARCHAR(200)  NOT NULL,
    category            VARCHAR(100)  NOT NULL,
    brand               VARCHAR(100)  NOT NULL,
    list_price_ngn      DECIMAL(18,2) NOT NULL,
    reorder_level_units INT           NOT NULL,
    unit_cost_ngn       DECIMAL(18,2) NOT NULL,
    active_flag         BIT           NOT NULL,
    dq_run_id           INT           NOT NULL REFERENCES audit.pipeline_run(run_id)
);
GO

/* sales_key is our own key: transaction_id is NOT unique in the source data */
IF OBJECT_ID('staging.sales_transactions') IS NULL
CREATE TABLE staging.sales_transactions (
    sales_key                   INT IDENTITY(1,1) PRIMARY KEY,
    transaction_id              VARCHAR(50)   NOT NULL,
    transaction_datetime        DATETIME2     NOT NULL,
    customer_id                 VARCHAR(50)   NOT NULL,   -- 'UNKNOWN' when missing in source
    product_id                  VARCHAR(50)   NOT NULL,
    quantity                    INT           NOT NULL,
    unit_price_ngn              DECIMAL(18,2) NOT NULL,
    discount_pct                DECIMAL(9,4)  NOT NULL,
    gross_sales_ngn             DECIMAL(18,2) NOT NULL,
    discount_amount_ngn         DECIMAL(18,2) NOT NULL,
    net_sales_ngn               DECIMAL(18,2) NOT NULL,
    sales_channel               VARCHAR(50)   NOT NULL,
    order_status                VARCHAR(20)   NOT NULL,
    is_missing_customer         BIT           NOT NULL,
    is_duplicate_transaction_id BIT           NOT NULL,
    dq_run_id                   INT           NOT NULL REFERENCES audit.pipeline_run(run_id),
    CONSTRAINT ck_stg_sales_discount CHECK (discount_pct BETWEEN 0 AND 1),
    CONSTRAINT ck_stg_sales_status   CHECK (order_status IN ('Delivered','Returned','Pending','Cancelled')),
    CONSTRAINT ck_stg_sales_channel  CHECK (sales_channel IN ('Online','Phone','Retail Counter','Field Sales')),
    CONSTRAINT ck_stg_sales_qty      CHECK (quantity >= 0 OR order_status = 'Returned')
);
GO

IF OBJECT_ID('staging.inventory_snapshot') IS NULL
CREATE TABLE staging.inventory_snapshot (
    inventory_record_id VARCHAR(50)  NOT NULL PRIMARY KEY,
    warehouse_id        VARCHAR(50)  NOT NULL,
    warehouse_name      VARCHAR(100) NOT NULL,
    warehouse_state     VARCHAR(50)  NOT NULL,
    product_id          VARCHAR(50)  NOT NULL,
    on_hand_units       INT          NOT NULL,
    reserved_units      INT          NOT NULL,
    available_units     INT          NOT NULL,
    reorder_level_units INT          NOT NULL,
    snapshot_date       DATE         NOT NULL,
    dq_run_id           INT          NOT NULL REFERENCES audit.pipeline_run(run_id),
    CONSTRAINT ck_stg_snap_on_hand   CHECK (on_hand_units >= 0),
    CONSTRAINT ck_stg_snap_available CHECK (available_units = on_hand_units - reserved_units)
);
GO

/* movement_key is our own key: movement_id is NOT unique in the source data */
IF OBJECT_ID('staging.inventory_movements') IS NULL
CREATE TABLE staging.inventory_movements (
    movement_key             INT IDENTITY(1,1) PRIMARY KEY,
    movement_id              VARCHAR(50)  NOT NULL,
    movement_datetime        DATETIME2    NOT NULL,
    warehouse_id             VARCHAR(50)  NOT NULL,
    product_id               VARCHAR(50)  NOT NULL,
    movement_type            VARCHAR(50)  NOT NULL,
    quantity_change          INT          NOT NULL,
    reference_type           VARCHAR(50)  NOT NULL,
    reference_id             VARCHAR(50)  NOT NULL,
    approval_status          VARCHAR(30)  NOT NULL,
    is_duplicate_movement_id BIT          NOT NULL,
    is_zero_quantity         BIT          NOT NULL,
    dq_run_id                INT          NOT NULL REFERENCES audit.pipeline_run(run_id),
    CONSTRAINT ck_stg_mov_approval CHECK (approval_status IN ('Approved','Pending'))
);
GO

/* ---------- quarantine: original raw values + why they were held back ---------- */
IF OBJECT_ID('quarantine.sales_transactions') IS NULL
CREATE TABLE quarantine.sales_transactions (
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
    reason_codes         VARCHAR(200)  NOT NULL,
    dq_run_id            INT           NOT NULL REFERENCES audit.pipeline_run(run_id),
    quarantined_at       DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('quarantine.inventory_snapshot') IS NULL
CREATE TABLE quarantine.inventory_snapshot (
    inventory_record_id VARCHAR(50)  NULL,
    warehouse_id        VARCHAR(50)  NULL,
    warehouse_name      VARCHAR(100) NULL,
    warehouse_state     VARCHAR(50)  NULL,
    product_id          VARCHAR(50)  NULL,
    on_hand_units       INT          NULL,
    reserved_units      INT          NULL,
    available_units     INT          NULL,
    reorder_level_units INT          NULL,
    snapshot_date       VARCHAR(20)  NULL,
    reason_codes        VARCHAR(200) NOT NULL,
    dq_run_id           INT          NOT NULL REFERENCES audit.pipeline_run(run_id),
    quarantined_at      DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('quarantine.inventory_movements') IS NULL
CREATE TABLE quarantine.inventory_movements (
    movement_id       VARCHAR(50)  NULL,
    movement_datetime DATETIME2    NULL,
    warehouse_id      VARCHAR(50)  NULL,
    product_id        VARCHAR(50)  NULL,
    movement_type     VARCHAR(50)  NULL,
    quantity_change   INT          NULL,
    reference_type    VARCHAR(50)  NULL,
    reference_id      VARCHAR(50)  NULL,
    approval_status   VARCHAR(50)  NULL,
    reason_codes      VARCHAR(200) NOT NULL,
    dq_run_id         INT          NOT NULL REFERENCES audit.pipeline_run(run_id),
    quarantined_at    DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

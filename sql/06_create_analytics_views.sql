/* ------------------------------------------------------------
   06_create_analytics_views.sql
   Reporting views for Power BI and for answering the business questions.

   Business definitions (see ADR 001 and ADR 002):
     Revenue        = net sales of Delivered orders (status group 'Completed')
     Returned value = net sales of Returned orders, shown BESIDE revenue as a positive amount
     Open orders    = Pending orders        (not revenue)
     Lost sales     = Cancelled orders      (not revenue)

   Views do not sort. Sorting is done by the report or the query that uses them.
   Safe to run more than once.
   ------------------------------------------------------------ */
USE FMCG_Pipeline;
GO

IF SCHEMA_ID('analytics') IS NULL EXEC('CREATE SCHEMA analytics');
GO

/* ---------- Q1, Q5, Q6: sales by month ---------- */
CREATE OR ALTER VIEW analytics.vw_monthly_sales AS
WITH monthly AS (
    SELECT d.year_month AS sales_month,
           COUNT(CASE WHEN st.status_group = 'Completed' THEN 1 END)                            AS completed_transactions,
           SUM(CASE WHEN st.status_group = 'Completed' THEN f.gross_sales_ngn     ELSE 0 END)   AS gross_sales_ngn,
           SUM(CASE WHEN st.status_group = 'Completed' THEN f.discount_amount_ngn ELSE 0 END)   AS discount_ngn,
           SUM(CASE WHEN st.status_group = 'Completed' THEN f.net_sales_ngn       ELSE 0 END)   AS revenue_ngn,
           SUM(CASE WHEN st.status_group = 'Returned'  THEN f.net_sales_ngn       ELSE 0 END)   AS returned_value_ngn,
           SUM(CASE WHEN st.status_group = 'Open'      THEN f.net_sales_ngn       ELSE 0 END)   AS open_orders_value_ngn,
           SUM(CASE WHEN st.status_group = 'Cancelled' THEN f.net_sales_ngn       ELSE 0 END)   AS lost_sales_value_ngn
    FROM curated.fact_sales AS f
    JOIN curated.dim_date AS d          ON d.date_key = f.date_key
    JOIN curated.dim_order_status AS st ON st.status_key = f.status_key
    GROUP BY d.year_month
)
SELECT sales_month, completed_transactions, gross_sales_ngn, discount_ngn, revenue_ngn,
       returned_value_ngn, open_orders_value_ngn, lost_sales_value_ngn,
       ROUND(discount_ngn * 1.0 / NULLIF(gross_sales_ngn, 0), 4)                      AS discount_rate,
       ROUND(revenue_ngn * 1.0 / NULLIF(completed_transactions, 0), 2)                AS avg_transaction_value_ngn,
       ROUND(returned_value_ngn * 1.0 / NULLIF(revenue_ngn + returned_value_ngn, 0), 4) AS return_rate
FROM monthly;
GO

/* ---------- Q6: how each order status is treated in reporting ---------- */
CREATE OR ALTER VIEW analytics.vw_sales_by_status AS
SELECT st.status_group,
       st.order_status,
       st.counts_as_revenue,
       CASE st.status_group
            WHEN 'Completed' THEN 'Counted as revenue'
            WHEN 'Returned'  THEN 'Shown beside revenue as returned value'
            WHEN 'Open'      THEN 'Not revenue; shown as open orders'
            WHEN 'Cancelled' THEN 'Not revenue; shown as lost sales'
       END                      AS reporting_treatment,
       COUNT(*)                 AS transactions,
       SUM(f.quantity)          AS units,
       SUM(f.net_sales_ngn)     AS net_sales_ngn
FROM curated.fact_sales AS f
JOIN curated.dim_order_status AS st ON st.status_key = f.status_key
GROUP BY st.status_group, st.order_status, st.counts_as_revenue;
GO

/* ---------- Q2, Q3, Q7: product performance (aggregate by category or brand in Power BI) ---------- */
CREATE OR ALTER VIEW analytics.vw_product_performance AS
WITH product_sales AS (
    SELECT p.product_key, p.product_id, p.product_name, p.category, p.brand, p.active_flag,
           SUM(CASE WHEN st.status_group = 'Completed' THEN f.quantity            ELSE 0 END) AS units_sold,
           SUM(CASE WHEN st.status_group = 'Completed' THEN f.gross_sales_ngn     ELSE 0 END) AS gross_sales_ngn,
           SUM(CASE WHEN st.status_group = 'Completed' THEN f.discount_amount_ngn ELSE 0 END) AS discount_ngn,
           SUM(CASE WHEN st.status_group = 'Completed' THEN f.net_sales_ngn       ELSE 0 END) AS revenue_ngn,
           SUM(CASE WHEN st.status_group = 'Returned'  THEN f.net_sales_ngn       ELSE 0 END) AS returned_value_ngn
    FROM curated.dim_product AS p
    LEFT JOIN curated.fact_sales AS f         ON f.product_key = p.product_key
    LEFT JOIN curated.dim_order_status AS st  ON st.status_key = f.status_key
    GROUP BY p.product_key, p.product_id, p.product_name, p.category, p.brand, p.active_flag
)
SELECT product_key, product_id, product_name, category, brand, active_flag,
       units_sold, gross_sales_ngn, discount_ngn, revenue_ngn, returned_value_ngn,
       ROUND(discount_ngn * 1.0 / NULLIF(gross_sales_ngn, 0), 4)                        AS discount_rate,
       ROUND(returned_value_ngn * 1.0 / NULLIF(revenue_ngn + returned_value_ngn, 0), 4) AS return_rate,
       RANK() OVER (ORDER BY revenue_ngn DESC)                         AS revenue_rank,
       RANK() OVER (ORDER BY units_sold DESC)                          AS units_rank,
       RANK() OVER (PARTITION BY category ORDER BY revenue_ngn DESC)   AS revenue_rank_in_category
FROM product_sales;
GO

/* ---------- Q4, Q8: customer performance and revenue concentration ---------- */
CREATE OR ALTER VIEW analytics.vw_customer_performance AS
WITH customer_sales AS (
    SELECT c.customer_key, c.customer_id, c.customer_name, c.customer_type, c.state, c.sales_territory, c.is_unknown,
           COUNT(CASE WHEN st.status_group = 'Completed' THEN 1 END)                       AS completed_transactions,
           SUM(CASE WHEN st.status_group = 'Completed' THEN f.net_sales_ngn ELSE 0 END)    AS revenue_ngn,
           SUM(CASE WHEN st.status_group = 'Returned'  THEN f.net_sales_ngn ELSE 0 END)    AS returned_value_ngn
    FROM curated.dim_customer AS c
    LEFT JOIN curated.fact_sales AS f        ON f.customer_key = c.customer_key
    LEFT JOIN curated.dim_order_status AS st ON st.status_key = f.status_key
    GROUP BY c.customer_key, c.customer_id, c.customer_name, c.customer_type, c.state, c.sales_territory, c.is_unknown
)
SELECT customer_key, customer_id, customer_name, customer_type, state, sales_territory, is_unknown,
       completed_transactions, revenue_ngn, returned_value_ngn,
       ROUND(revenue_ngn * 1.0 / NULLIF(SUM(revenue_ngn) OVER (), 0), 6) AS revenue_share,
       /* rank and cumulative share are for known customers only; the UNKNOWN member is left out of them */
       CASE WHEN is_unknown = 0
            THEN RANK() OVER (PARTITION BY is_unknown ORDER BY revenue_ngn DESC) END AS revenue_rank,
       CASE WHEN is_unknown = 0
            THEN ROUND(SUM(revenue_ngn) OVER (PARTITION BY is_unknown ORDER BY revenue_ngn DESC, customer_key
                                              ROWS UNBOUNDED PRECEDING) * 1.0
                       / NULLIF(SUM(revenue_ngn) OVER (PARTITION BY is_unknown), 0), 6) END AS cumulative_revenue_share
FROM customer_sales;
GO

/* ---------- Q7: does a higher discount go with higher volume? ---------- */
CREATE OR ALTER VIEW analytics.vw_discount_analysis AS
WITH banded AS (
    SELECT CASE WHEN f.discount_pct = 0    THEN 1
                WHEN f.discount_pct < 0.05 THEN 2
                WHEN f.discount_pct < 0.10 THEN 3
                WHEN f.discount_pct < 0.15 THEN 4
                ELSE 5 END AS band_order,
           f.quantity, f.gross_sales_ngn, f.discount_amount_ngn, f.net_sales_ngn
    FROM curated.fact_sales AS f
    JOIN curated.dim_order_status AS st ON st.status_key = f.status_key
    WHERE st.status_group = 'Completed'
)
SELECT band_order,
       CASE band_order WHEN 1 THEN 'No discount' WHEN 2 THEN '1-4%' WHEN 3 THEN '5-9%'
                       WHEN 4 THEN '10-14%' ELSE '15% and above' END AS discount_band,
       COUNT(*)                                   AS transactions,
       SUM(quantity)                              AS units_sold,
       ROUND(AVG(quantity * 1.0), 2)              AS avg_units_per_transaction,
       SUM(gross_sales_ngn)                       AS gross_sales_ngn,
       SUM(discount_amount_ngn)                   AS discount_ngn,
       SUM(net_sales_ngn)                         AS revenue_ngn,
       ROUND(AVG(net_sales_ngn * 1.0), 2)         AS avg_transaction_value_ngn
FROM banded
GROUP BY band_order;
GO

/* ---------- Q9, Q10: products below reorder level at the snapshot date ---------- */
CREATE OR ALTER VIEW analytics.vw_stock_below_reorder AS
SELECT d.full_date AS snapshot_date,
       w.warehouse_id, w.warehouse_name, w.warehouse_state,
       p.product_id, p.product_name, p.category, p.brand,
       s.on_hand_units, s.reserved_units, s.available_units, s.reorder_level_units,
       s.reorder_level_units - s.available_units                          AS shortfall_units,
       ROUND(s.reserved_units * 1.0 / NULLIF(s.on_hand_units, 0), 4)      AS reserved_share_of_on_hand
FROM curated.fact_inventory_snapshot AS s
JOIN curated.dim_date      AS d ON d.date_key = s.date_key
JOIN curated.dim_warehouse AS w ON w.warehouse_key = s.warehouse_key
JOIN curated.dim_product   AS p ON p.product_key = s.product_key
WHERE s.is_below_reorder = 1;
GO

/* ---------- Q11: stock by warehouse and category ---------- */
CREATE OR ALTER VIEW analytics.vw_inventory_by_warehouse_category AS
SELECT w.warehouse_id, w.warehouse_name, p.category,
       COUNT(*)                                                      AS product_lines,
       SUM(s.on_hand_units)                                          AS on_hand_units,
       SUM(s.reserved_units)                                         AS reserved_units,
       SUM(s.available_units)                                        AS available_units,
       SUM(CASE WHEN s.is_below_reorder = 1 THEN 1 ELSE 0 END)       AS lines_below_reorder
FROM curated.fact_inventory_snapshot AS s
JOIN curated.dim_warehouse AS w ON w.warehouse_key = s.warehouse_key
JOIN curated.dim_product   AS p ON p.product_key = s.product_key
GROUP BY w.warehouse_id, w.warehouse_name, p.category;
GO

/* ---------- Q12, Q13: stock movements by warehouse, product and type ---------- */
CREATE OR ALTER VIEW analytics.vw_movement_summary AS
SELECT w.warehouse_id, w.warehouse_name,
       p.product_id, p.product_name, p.category,
       m.movement_type, m.approval_status,
       COUNT(*)                                                          AS movements,
       SUM(CASE WHEN m.quantity_change > 0 THEN m.quantity_change  ELSE 0 END) AS units_in,
       SUM(CASE WHEN m.quantity_change < 0 THEN -m.quantity_change ELSE 0 END) AS units_out,
       SUM(m.quantity_change)                                            AS net_units
FROM curated.fact_inventory_movement AS m
JOIN curated.dim_warehouse AS w ON w.warehouse_key = m.warehouse_key
JOIN curated.dim_product   AS p ON p.product_key = m.product_key
GROUP BY w.warehouse_id, w.warehouse_name, p.product_id, p.product_name, p.category, m.movement_type, m.approval_status;
GO

/* ---------- Q14: can movements be reconciled to the snapshot? ----------
   The snapshot is one date (31 Dec 2025), so we cannot test it against a start-of-year count.
   Assumption: opening stock = closing stock minus the year's APPROVED net movements.
   A negative opening stock is impossible, so those rows show movements and snapshot disagree. */
CREATE OR ALTER VIEW analytics.vw_stock_reconciliation AS
WITH approved AS (
    SELECT product_key, warehouse_key, SUM(quantity_change) AS approved_net_units
    FROM curated.fact_inventory_movement
    WHERE approval_status = 'Approved'
    GROUP BY product_key, warehouse_key
),
pending AS (
    SELECT product_key, warehouse_key, SUM(quantity_change) AS pending_net_units
    FROM curated.fact_inventory_movement
    WHERE approval_status = 'Pending'
    GROUP BY product_key, warehouse_key
)
SELECT w.warehouse_id, w.warehouse_name, p.product_id, p.product_name,
       s.on_hand_units                                                    AS on_hand_at_snapshot,
       COALESCE(a.approved_net_units, 0)                                  AS approved_net_movement_units,
       COALESCE(pe.pending_net_units, 0)                                  AS pending_net_movement_units,
       s.on_hand_units - COALESCE(a.approved_net_units, 0)                AS implied_opening_units,
       CASE WHEN s.on_hand_units - COALESCE(a.approved_net_units, 0) < 0 THEN 1 ELSE 0 END AS is_implied_opening_negative
FROM curated.fact_inventory_snapshot AS s
JOIN curated.dim_warehouse AS w ON w.warehouse_key = s.warehouse_key
JOIN curated.dim_product   AS p ON p.product_key = s.product_key
LEFT JOIN approved AS a  ON a.product_key = s.product_key AND a.warehouse_key = s.warehouse_key
LEFT JOIN pending  AS pe ON pe.product_key = s.product_key AND pe.warehouse_key = s.warehouse_key;
GO

/* ---------- Q16 to Q19: data quality, latest successful run ---------- */
CREATE OR ALTER VIEW analytics.vw_dq_table_summary AS
SELECT s.run_id, r.finished_at AS run_finished_at, s.table_name,
       s.raw_rows, s.clean_rows, s.quarantined_rows,
       ROUND(s.quarantined_rows * 1.0 / NULLIF(s.raw_rows, 0), 4) AS quarantine_rate
FROM audit.dq_summary AS s
JOIN audit.pipeline_run AS r ON r.run_id = s.run_id
WHERE s.run_id = (SELECT MAX(run_id) FROM audit.pipeline_run WHERE stage = 'data_quality' AND status = 'SUCCESS');
GO

CREATE OR ALTER VIEW analytics.vw_dq_rule_results AS
SELECT x.run_id, x.table_name, x.rule_code, x.outcome, x.rows_affected, x.net_sales_ngn_impact
FROM audit.dq_result AS x
WHERE x.run_id = (SELECT MAX(run_id) FROM audit.pipeline_run WHERE stage = 'data_quality' AND status = 'SUCCESS');
GO

/* ---------- Q20 to Q22: pipeline runs and reconciliation ---------- */
CREATE OR ALTER VIEW analytics.vw_pipeline_runs AS
SELECT r.run_id, r.stage, r.status, r.started_at, r.finished_at,
       CASE WHEN r.status = 'SUCCESS'
             AND r.run_id = MAX(CASE WHEN r.status = 'SUCCESS' THEN r.run_id END) OVER (PARTITION BY r.stage)
            THEN 1 ELSE 0 END AS is_latest_success
FROM audit.pipeline_run AS r;
GO

CREATE OR ALTER VIEW analytics.vw_load_reconciliation AS
SELECT l.run_id, r.stage, l.table_name, l.source_rows, l.loaded_rows,
       l.loaded_rows - l.source_rows                                   AS row_difference,
       CASE WHEN l.loaded_rows = l.source_rows THEN 'OK' ELSE 'MISMATCH' END AS result,
       l.logged_at,
       CASE WHEN r.status = 'SUCCESS'
             AND l.run_id = MAX(CASE WHEN r.status = 'SUCCESS' THEN l.run_id END) OVER (PARTITION BY r.stage)
            THEN 1 ELSE 0 END AS is_latest_success
FROM audit.load_log AS l
JOIN audit.pipeline_run AS r ON r.run_id = l.run_id;
GO

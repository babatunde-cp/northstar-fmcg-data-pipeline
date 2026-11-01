/* Compare loaded row counts with the counts in the source workbooks. */
USE FMCG_Pipeline;
GO

SELECT t.table_name, t.loaded_rows, e.expected_rows,
       CASE WHEN t.loaded_rows = e.expected_rows THEN 'OK' ELSE 'MISMATCH' END AS result
FROM (
    SELECT 'sales_transactions'  AS table_name, COUNT(*) AS loaded_rows FROM raw.sales_transactions  UNION ALL
    SELECT 'customer_master',                   COUNT(*)                FROM raw.customer_master      UNION ALL
    SELECT 'product_master',                    COUNT(*)                FROM raw.product_master       UNION ALL
    SELECT 'inventory_snapshot',                COUNT(*)                FROM raw.inventory_snapshot   UNION ALL
    SELECT 'inventory_movements',               COUNT(*)                FROM raw.inventory_movements
) AS t
JOIN (VALUES ('sales_transactions', 65000), ('customer_master', 500), ('product_master', 30),
             ('inventory_snapshot', 120), ('inventory_movements', 15000)) AS e(table_name, expected_rows)
  ON e.table_name = t.table_name;

/* Latest runs and their per-table results */
SELECT TOP 10 * FROM audit.pipeline_run ORDER BY run_id DESC;
SELECT TOP 20 * FROM audit.load_log     ORDER BY log_id DESC;

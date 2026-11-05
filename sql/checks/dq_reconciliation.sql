/* Does raw = staging + quarantine for every table, and what was held back? */
USE FMCG_Pipeline;
GO

/* 1. Reconciliation from the latest data-quality run */
SELECT s.table_name, s.raw_rows, s.clean_rows, s.quarantined_rows,
       CASE WHEN s.raw_rows = s.clean_rows + s.quarantined_rows THEN 'OK' ELSE 'MISMATCH' END AS result
FROM audit.dq_summary AS s
WHERE s.run_id = (SELECT MAX(run_id) FROM audit.pipeline_run WHERE stage = 'data_quality' AND status = 'SUCCESS')
ORDER BY s.dq_summary_id;

/* 2. What each rule did in that run, with the naira value affected (sales rules) */
SELECT r.table_name, r.rule_code, r.outcome, r.rows_affected, r.net_sales_ngn_impact
FROM audit.dq_result AS r
WHERE r.run_id = (SELECT MAX(run_id) FROM audit.pipeline_run WHERE stage = 'data_quality' AND status = 'SUCCESS')
ORDER BY r.dq_result_id;

/* 3. Why rows were quarantined */
SELECT 'sales_transactions' AS table_name, reason_codes, COUNT(*) AS rows_held FROM quarantine.sales_transactions GROUP BY reason_codes
UNION ALL
SELECT 'inventory_snapshot', reason_codes, COUNT(*) FROM quarantine.inventory_snapshot GROUP BY reason_codes
UNION ALL
SELECT 'inventory_movements', reason_codes, COUNT(*) FROM quarantine.inventory_movements GROUP BY reason_codes
ORDER BY table_name, rows_held DESC;

/* 4. Net sales: raw vs staging vs quarantine */
SELECT (SELECT SUM(net_sales_ngn) FROM raw.sales_transactions)        AS raw_net_sales,
       (SELECT SUM(net_sales_ngn) FROM staging.sales_transactions)    AS staging_net_sales,
       (SELECT SUM(net_sales_ngn) FROM quarantine.sales_transactions) AS quarantined_net_sales;
GO

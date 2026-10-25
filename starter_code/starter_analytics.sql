-- Suggested analytical views (adapt after creating curated tables).
-- Define how cancelled/pending/returned orders affect sales before implementing.

-- 1) Monthly net sales:
-- SELECT strftime('%Y-%m', transaction_datetime) AS sales_month,
--        SUM(net_sales_ngn) AS net_sales_ngn
-- FROM fact_sales
-- WHERE order_status = 'Delivered'
-- GROUP BY 1 ORDER BY 1;

-- 2) Products below reorder level:
-- SELECT warehouse_id, product_id, available_units, reorder_level_units
-- FROM fact_inventory_snapshot
-- WHERE available_units < reorder_level_units;

-- 3) Data-quality issue counts:
-- SELECT issue_code, COUNT(*) AS row_count
-- FROM data_quality_issues
-- GROUP BY issue_code ORDER BY row_count DESC;

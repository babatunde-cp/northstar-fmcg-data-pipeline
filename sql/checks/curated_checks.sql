/* Sanity checks on the curated star schema. Run after python src/build_curated.py */
USE FMCG_Pipeline;
GO

/* 1. Row counts of every curated table */
SELECT 'dim_date' AS table_name, COUNT(*) AS row_count FROM curated.dim_date UNION ALL
SELECT 'dim_customer',            COUNT(*) FROM curated.dim_customer UNION ALL
SELECT 'dim_product',             COUNT(*) FROM curated.dim_product UNION ALL
SELECT 'dim_warehouse',           COUNT(*) FROM curated.dim_warehouse UNION ALL
SELECT 'dim_sales_channel',       COUNT(*) FROM curated.dim_sales_channel UNION ALL
SELECT 'dim_order_status',        COUNT(*) FROM curated.dim_order_status UNION ALL
SELECT 'fact_sales',              COUNT(*) FROM curated.fact_sales UNION ALL
SELECT 'fact_inventory_snapshot', COUNT(*) FROM curated.fact_inventory_snapshot UNION ALL
SELECT 'fact_inventory_movement', COUNT(*) FROM curated.fact_inventory_movement;

/* 2. Net sales: staging vs curated (the two numbers must be identical) */
SELECT (SELECT SUM(net_sales_ngn) FROM staging.sales_transactions) AS staging_net_sales,
       (SELECT SUM(net_sales_ngn) FROM curated.fact_sales)         AS curated_net_sales;

/* 3. Sales by order status group, with the revenue definition */
SELECT st.status_group, st.counts_as_revenue, COUNT(*) AS sales_rows, SUM(f.net_sales_ngn) AS net_sales_ngn
FROM curated.fact_sales AS f
JOIN curated.dim_order_status AS st ON st.status_key = f.status_key
GROUP BY st.status_group, st.counts_as_revenue
ORDER BY st.status_group;

/* 4. Sales by month (first real "business" query on the model) */
SELECT d.year_month, SUM(f.net_sales_ngn) AS net_sales_ngn
FROM curated.fact_sales AS f
JOIN curated.dim_date AS d ON d.date_key = f.date_key
GROUP BY d.year_month
ORDER BY d.year_month;

/* 5. Sales linked to the UNKNOWN customer */
SELECT COUNT(*) AS unknown_customer_sales
FROM curated.fact_sales AS f
JOIN curated.dim_customer AS c ON c.customer_key = f.customer_key
WHERE c.is_unknown = 1;

/* 6. Products below their reorder level at the snapshot date */
SELECT w.warehouse_name, COUNT(*) AS products_below_reorder
FROM curated.fact_inventory_snapshot AS s
JOIN curated.dim_warehouse AS w ON w.warehouse_key = s.warehouse_key
WHERE s.is_below_reorder = 1
GROUP BY w.warehouse_name
ORDER BY products_below_reorder DESC;
GO

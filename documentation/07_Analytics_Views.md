# Analytics views: which view answers which business question

All views live in the `analytics` schema and read the curated star schema (and the audit tables).
They do not sort; the report or query that uses them does. Created by `sql/06_create_analytics_views.sql`.

**Definitions** (ADR 001 and ADR 002): revenue is the net sales of Delivered orders. Returned value is
shown beside revenue as a positive amount. Pending is "open orders" and Cancelled is "lost sales";
neither is revenue.

## Questions and views

| Question | Where it is answered |
|---|---|
| 1. Gross sales, discounts and net sales by month | `vw_monthly_sales` |
| 2. Top categories and brands | `vw_product_performance` (group by `category` or `brand`) |
| 3. Top products by quantity and net sales | `vw_product_performance` (`units_rank`, `revenue_rank`) |
| 4. Sales by customer type, state, territory, channel | `vw_customer_performance` (type, state, territory); channel from `fact_sales` and `dim_sales_channel` in the model |
| 5. Monthly average transaction value | `vw_monthly_sales` (`avg_transaction_value_ngn`) |
| 6. How each order status affects reporting | `vw_sales_by_status` (`reporting_treatment`) |
| 7. Discount rate, and does discounting lift volume? | `vw_discount_analysis`; `discount_rate` in `vw_product_performance` and `vw_monthly_sales` |
| 8. Customer contribution and concentration | `vw_customer_performance` (`revenue_share`, `revenue_rank`, `cumulative_revenue_share`) |
| 9, 10. Product and warehouse lines below reorder level, and low available stock | `vw_stock_below_reorder` |
| 11. On-hand, reserved and available by warehouse and category | `vw_inventory_by_warehouse_category` |
| 12, 13. Issues, damages, returns, adjustments; warehouse movement volume | `vw_movement_summary` |
| 14. Reconciling movements to the snapshot | `vw_stock_reconciliation` |
| 15. Invalid or suspicious stock records | `vw_dq_rule_results` (rules I01 to I05) and `quarantine.inventory_snapshot` |
| 16, 17, 18. Duplicate IDs, missing or unknown keys, invalid values | `vw_dq_rule_results` |
| 19. Rows accepted, corrected, quarantined, and why | `vw_dq_table_summary` and `vw_dq_rule_results` |
| 20. Does a re-run create duplicates? | `vw_pipeline_runs` and `vw_load_reconciliation` (counts stay the same across runs) |
| 21. Source and financial totals reconcile | `vw_load_reconciliation`, plus `sql/checks/` |
| 22. Missing, malformed or unexpected workbooks | Not a view. This is covered by pipeline tests (Phase 8) |

## What the data shows (synthetic dataset)

- **Revenue** is about ₦201.9M, with ₦194.2M of returned value. The return rate is about 49%, because
  the four order statuses are nearly equal in size in this generated data.
- **Discounts** average 3.4% of gross sales. Average units per order are about 4.1 to 4.3 in every
  discount band, while average order value falls from about ₦13,091 with no discount to ₦10,745
  at 15% and above. In this data, higher discounts do not go with bigger orders.
- **Customers** are not concentrated. The top 10% of customers give 16.4% of revenue, and 191 of 500
  are needed to reach half. No single customer is above 0.6%.
- **Stock:** 12 of 115 product and warehouse lines are below reorder level, 5 of them in Abuja.
  Tomato sachets (70g) are the biggest gaps, 279 units short in Abuja and 250 in Port Harcourt.
- **Reconciliation:** assuming opening stock equals closing stock minus approved movements, 12 of 115
  lines imply negative opening stock, so movements and the snapshot do not fully agree.
- **Quarantine rates:** sales 1.2%, inventory snapshot 4.2%, inventory movements 0.2%.

## How the views are checked

`python src/validate_views.py` recalculates the key numbers of every view independently with pandas,
from the staging tables, and compares them. It prints one PASS or FAIL line per check.

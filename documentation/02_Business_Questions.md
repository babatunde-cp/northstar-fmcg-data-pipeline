# Business Questions to Answer

## Sales performance
1. What are total gross sales, discounts and net sales by month?
2. Which product categories and brands generate the highest net sales?
3. Which products have the highest quantity sold and highest net sales?
4. How do sales differ by customer type, state, territory and channel?
5. What is the monthly trend in average transaction value?
6. Which transactions are cancelled, pending, delivered or returned, and how should each status affect reporting?
7. What is the discount rate by product/category/channel, and is higher discounting associated with higher sales volume?
8. Which customers contribute most to net sales? Is revenue concentrated among a small number of customers?

## Inventory and replenishment
9. Which product/warehouse combinations are below reorder level?
10. Which products have low available stock after reservations?
11. What are total on-hand, reserved and available units by warehouse and category?
12. Which products experience the most stock issues, damages, returns and adjustments?
13. Which warehouses have the highest movement volume?
14. Can inventory movement totals be reconciled to the snapshot? What assumptions are required because the snapshot is only for 31 Dec 2025?
15. Which stock records are invalid or suspicious, and what should happen to them?

## Data quality and pipeline reliability
16. How many duplicate transaction and movement IDs exist?
17. How many records have missing customer IDs or unknown product/warehouse keys?
18. Which columns contain invalid ranges, inconsistent labels or impossible arithmetic?
19. How many rows are accepted, corrected, quarantined or rejected, and why?
20. Does rerunning the pipeline create duplicate curated records?
21. How do source row counts and financial totals reconcile to raw and curated tables?
22. What happens if one workbook is missing, malformed or has an unexpected column?

## Suggested Power BI pages
- Executive Overview: net sales, transactions, discount rate, stock availability, at-risk SKUs.
- Sales Analysis: monthly trend, category/brand, channel, customer and geography.
- Inventory Health: stock by warehouse, reorder alerts, available vs reserved.
- Inventory Movements: movement types, damage/returns, approval status.
- Data Quality & Pipeline: row counts, issue categories, quarantine rate, last successful run.

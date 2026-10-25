# Data Dictionary

## 01_sales_transactions.xlsx — Sales_Transactions
| Column | Meaning | Expected type / rule |
|---|---|---|
| transaction_id | Unique source transaction identifier | String; unique expected |
| transaction_datetime | Date/time of transaction | Datetime; 2025 |
| customer_id | Customer key | Must match Customer_Master |
| product_id | Product key | Must match Product_Master |
| quantity | Units in transaction | Integer; negative may indicate return/reversal |
| unit_price_ngn | Selling price per unit in NGN | Numeric, non-negative |
| discount_pct | Discount as decimal fraction | 0 to 1 |
| gross_sales_ngn | Quantity × unit price | Numeric; reconcile with rounding |
| discount_amount_ngn | Discount amount | Numeric |
| net_sales_ngn | Gross minus discount | Numeric |
| sales_channel | Sales channel | Standardize labels |
| order_status | Order lifecycle status | Standardize allowed values |

## 01_sales_transactions.xlsx — Customer_Master
| Column | Meaning |
|---|---|
| customer_id | Customer business key |
| customer_name | Synthetic customer label |
| customer_type | Retailer, Wholesaler, Distributor or Supermarket |
| state | Operating state / FCT |
| city | City or area |
| sales_territory | Sales territory grouping |

## 02_product_inventory.xlsx — Product_Master
| Column | Meaning |
|---|---|
| product_id | Product business key |
| product_name | Product display name |
| category | Product category |
| brand | Fictional brand |
| list_price_ngn | Reference selling price |
| reorder_level_units | Target reorder threshold |
| unit_cost_ngn | Synthetic estimated unit cost |
| active_flag | Whether product is active |

## 02_product_inventory.xlsx — Inventory_Snapshot
| Column | Meaning |
|---|---|
| inventory_record_id | Snapshot record identifier |
| warehouse_id | Warehouse business key |
| warehouse_name | Warehouse display name |
| warehouse_state | Warehouse location |
| product_id | Product key |
| on_hand_units | Physical stock quantity at snapshot |
| reserved_units | Units allocated/reserved |
| available_units | Intended to equal on-hand minus reserved |
| reorder_level_units | Reorder threshold |
| snapshot_date | Date stock snapshot was taken |

## 03_inventory_movements.xlsx — Inventory_Movements
| Column | Meaning |
|---|---|
| movement_id | Inventory movement identifier |
| movement_datetime | Movement timestamp |
| warehouse_id | Warehouse key |
| product_id | Product key |
| movement_type | Receipt, sale issue, return, damage, adjustment, transfer |
| quantity_change | Signed quantity change; sign convention must be validated |
| reference_type | Reference business process |
| reference_id | Source reference identifier |
| approval_status | Approval workflow state |

All records are fictional. Confirm each column's actual type in Python rather than relying only on Excel's display formatting.

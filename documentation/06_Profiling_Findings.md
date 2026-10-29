# Profile Findings

# Profiling the data revealed some details

# Sales transaction table

- Rows: 65,000
- Columns: 12

transaction_id - primary key (No nulls), some IDs were repeated in different rows, and this can be tagged as ID collision
Customer id column have some missing values
Some columns have string casing issues, which should be fixed
Ambiguous discount amount noticed, above 100%


## Customer_Master

- Rows: 500
- Columns: 6

No repeated ids or key values


## Product_Master

- Rows: 30
- Columns: 8

No repeated ids or key values

## Inventory_Snapshot

- Rows: 120
- Columns: 10

No repeated ids or key values

One unknown warehouse id
one NaN Snapshot date

## Inventory_Movements

- Rows: 15,000
- Columns: 9

No repeated ids or key values
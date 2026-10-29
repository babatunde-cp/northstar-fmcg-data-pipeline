# Profile Findings

## Sales_Transactions

- Rows: 65,000
- Columns: 12

### Data types and nulls
```
                               dtype  nulls
transaction_id                   str      0
transaction_datetime  datetime64[us]      0
customer_id                      str    110
product_id                       str      0
quantity                       int64      0
unit_price_ngn               float64      0
discount_pct                 float64      0
gross_sales_ngn              float64      0
discount_amount_ngn          float64      0
net_sales_ngn                float64      0
sales_channel                    str      0
order_status                     str      0
```

### Key check: `transaction_id`
- Repeated key values: 80

### Distinct values: `sales_channel`
```
'Phone': 16304
'Online': 16282
'Retail Counter': 16238
'Field Sales': 16036
' field sales ': 44
' online ': 34
' retail counter ': 33
' phone ': 29
```

### Distinct values: `order_status`
```
'Cancelled': 16398
'Delivered': 16349
'Returned': 16101
'Pending': 16052
'delivered': 32
'RETURNED': 24
'PENDING ': 24
'cancelled': 20
```

### Numeric ranges
```
                       count          mean           std        min       25%       50%         75%        max
quantity             65000.0      4.081077      4.069650     -34.00     2.000     3.000      5.0000     100.00
unit_price_ngn       65000.0   3051.424416   2464.584752     230.00  1120.965  2256.165   4238.9800   10583.89
discount_pct         65000.0      0.036482      0.066980       0.00     0.000     0.020      0.0500       1.25
gross_sales_ngn      65000.0  12490.525911  19270.811560 -214103.01  2638.135  6429.890  14889.4475  539669.16
discount_amount_ngn  65000.0    423.722196   1142.795217  -10705.15     0.000    46.570    385.8300   53204.94
net_sales_ngn        65000.0  12066.803715  18662.523496 -203397.86  2545.750  6198.650  14376.4475  539669.16
```

### Baseline totals (before cleaning)
```
gross_sales_ngn: 811,884,184.23
discount_amount_ngn: 27,541,942.73
net_sales_ngn: 784,342,241.50
```

## Customer_Master

- Rows: 500
- Columns: 6

### Data types and nulls
```
                dtype  nulls
customer_id       str      0
customer_name     str      0
customer_type     str      0
state             str      0
city              str      0
sales_territory   str      0
```

### Key check: `customer_id`
- Repeated key values: 0

### Distinct values: `customer_type`
```
'Distributor': 136
'Retailer': 128
'Supermarket': 126
'Wholesaler': 110
```

### Distinct values: `state`
```
'Kano': 91
'Rivers': 89
'Lagos': 83
'Abuja FCT': 82
'Ogun': 80
'Oyo': 75
```

### Distinct values: `sales_territory`
```
'Central': 112
'South': 103
'West': 97
'East': 94
'North': 94
```

## Product_Master

- Rows: 30
- Columns: 8

### Data types and nulls
```
                       dtype  nulls
product_id               str      0
product_name             str      0
category                 str      0
brand                    str      0
list_price_ngn         int64      0
reorder_level_units    int64      0
unit_cost_ngn        float64      0
active_flag             bool      0
```

### Key check: `product_id`
- Repeated key values: 0

### Distinct values: `category`
```
'Dairy': 4
'Beverages': 4
'Home Care': 4
'Baking': 4
'Grains': 2
'Cooking Oil': 2
'Pasta': 2
'Food': 2
'Breakfast': 2
'Seasoning': 2
'Snacks': 2
```

### Distinct values: `active_flag`
```
True: 30
```

### Numeric ranges
```
                     count         mean          std     min       25%      50%        75%     max
list_price_ngn        30.0  3036.666667  2498.410989  250.00  1137.500  2250.00  4125.0000  9800.0
reorder_level_units   30.0   184.333333    96.443063   80.00   100.000   160.00   247.5000   500.0
unit_cost_ngn         30.0  2057.167667  1783.276942  155.62   767.145  1475.25  2774.0575  7547.4
```

## Inventory_Snapshot

- Rows: 120
- Columns: 10

### Data types and nulls
```
                     dtype  nulls
inventory_record_id    str      0
warehouse_id           str      0
warehouse_name         str      0
warehouse_state        str      0
product_id             str      0
on_hand_units        int64      0
reserved_units       int64      0
available_units      int64      0
reorder_level_units  int64      0
snapshot_date          str      1
```

### Key check: `inventory_record_id`
- Repeated key values: 0

### Distinct values: `warehouse_id`
```
'WH-OGN': 30
'WH-ABJ': 30
'WH-PHC': 30
'WH-LAG': 29
'WH-UNKNOWN': 1
```

### Distinct values: `snapshot_date`
```
'2025-12-31': 119
nan: 1
```

### Numeric ranges
```
                     count        mean         std   min     25%    50%     75%     max
on_hand_units        120.0  444.850000  170.906267 -12.0  328.75  452.5  535.00   947.0
reserved_units       120.0  109.191667  910.520207   0.0   12.75   30.0   39.00  9999.0
available_units      120.0  420.883333  167.516972  78.0  307.75  425.0  504.75   936.0
reorder_level_units  120.0  184.333333   95.219634  80.0  100.00  160.0  250.00   500.0
```

## Inventory_Movements

- Rows: 15,000
- Columns: 9

### Data types and nulls
```
                            dtype  nulls
movement_id                   str      0
movement_datetime  datetime64[us]      0
warehouse_id                  str      0
product_id                    str      0
movement_type                 str      0
quantity_change             int64      0
reference_type                str      0
reference_id                  str      0
approval_status               str      0
```

### Key check: `movement_id`
- Repeated key values: 25

### Distinct values: `movement_type`
```
'SALE_ISSUE': 6751
'RECEIPT': 3758
'CUSTOMER_RETURN': 1184
'ADJUSTMENT': 1101
'DAMAGE': 762
'TRANSFER_IN': 737
'TRANSFER_OUT': 707
```

### Distinct values: `reference_type`
```
'SO': 3080
'TRF': 3013
'RET': 2996
'ADJ': 2994
'PO': 2917
```

### Distinct values: `approval_status`
```
'Approved': 11219
'Pending': 3741
'approved ': 40
```

### Numeric ranges
```
                   count      mean        std    min   25%   50%   75%    max
quantity_change  15000.0 -5.641467  69.096047 -120.0 -65.0 -11.0  54.0  120.0
```

## Relationship checks (keys with no match)

- Sales_Transactions.customer_id -> Customer_Master: 0
- Sales_Transactions.product_id -> Product_Master: 90
- Inventory_Snapshot.product_id -> Product_Master: 1
- Inventory_Movements.product_id -> Product_Master: 30
- Inventory_Movements.warehouse_id -> Inventory_Snapshot: 0

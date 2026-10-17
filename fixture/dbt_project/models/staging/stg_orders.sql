select
    order_id,
    customer_id,
    cast(order_date as date) as order_date,
    status,
    amount,
    discount_pct,
    currency
from {{ source('raw', 'raw_orders') }}

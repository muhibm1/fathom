{{ config(tags=['orders']) }}
select
    order_id,
    customer_id,
    order_date,
    status,
    amount,
    discount_pct,
    amount * (1 - discount_pct / 100.0) as net_amount,
    currency,
    paid_amount,
    payment_count
from {{ ref('int_order_payments') }}

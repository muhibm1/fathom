{{ config(tags=['finance']) }}
select
    r.refund_id,
    r.order_id,
    o.customer_id,
    r.refund_amount,
    r.refunded_at,
    r.reason
from {{ ref('stg_refunds') }} r
join {{ ref('fct_orders') }} o on o.order_id = r.order_id

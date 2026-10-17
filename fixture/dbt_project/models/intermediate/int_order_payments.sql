select
    o.order_id,
    o.customer_id,
    o.order_date,
    o.status,
    o.amount,
    o.discount_pct,
    o.currency,
    coalesce(sum(p.paid_amount), 0) as paid_amount,
    count(p.payment_id) as payment_count
from {{ ref('stg_orders') }} o
left join {{ ref('stg_payments') }} p on p.order_id = o.order_id
group by 1, 2, 3, 4, 5, 6, 7

select
    c.customer_id,
    c.first_name,
    c.region,
    c.signup_date,
    count(o.order_id) as order_count,
    sum(o.amount) as lifetime_amount,
    min(o.order_date) as first_order_date,
    max(o.order_date) as last_order_date
from {{ ref('stg_customers') }} c
left join {{ ref('stg_orders') }} o on o.customer_id = c.customer_id
group by 1, 2, 3, 4

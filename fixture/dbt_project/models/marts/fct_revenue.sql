{{ config(tags=['orders', 'finance']) }}
select
    order_date as revenue_date,
    currency,
    sum(net_amount) as gross_revenue,
    sum(paid_amount) as collected_revenue,
    count(distinct order_id) as order_count
from {{ ref('fct_orders') }}
where status in ('completed', 'shipped')
group by 1, 2

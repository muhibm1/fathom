{{ config(tags=['orders', 'ml']) }}
select
    c.customer_id,
    c.region,
    c.order_count,
    c.lifetime_amount,
    c.last_order_date,
    coalesce(s.sessions_30d, 0) as sessions_30d,
    case when c.last_order_date < current_date - interval 60 day then 0.8 else 0.2 end as churn_score
from {{ ref('dim_customers') }} c
left join (
    select customer_id, count(*) as sessions_30d
    from {{ ref('fct_sessions') }}
    where session_date >= current_date - interval 30 day
    group by 1
) s on s.customer_id = c.customer_id

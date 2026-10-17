{{ config(tags=['events']) }}
select
    p.product_id,
    p.product_name,
    p.category,
    count(e.event_id) as views,
    count(distinct e.customer_id) as viewers
from {{ ref('dim_products') }} p
left join {{ ref('stg_events') }} e on e.product_id = p.product_id and e.event_type = 'page_view'
group by 1, 2, 3

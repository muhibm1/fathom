{{ config(tags=['events']) }}
select
    event_date,
    count(distinct customer_id) as active_users,
    count(*) as events
from {{ ref('stg_events') }}
group by 1

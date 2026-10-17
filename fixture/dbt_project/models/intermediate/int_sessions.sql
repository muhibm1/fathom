select
    session_id,
    customer_id,
    min(event_ts) as session_start,
    max(event_ts) as session_end,
    count(*) as event_count,
    min(event_date) as session_date
from {{ ref('stg_events') }}
group by 1, 2

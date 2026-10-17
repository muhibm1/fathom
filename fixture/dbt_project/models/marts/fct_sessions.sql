{{ config(tags=['events']) }}
select
    session_id,
    customer_id,
    session_date,
    session_start,
    session_end,
    event_count,
    date_diff('second', session_start, session_end) as duration_seconds
from {{ ref('int_sessions') }}

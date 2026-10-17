select
    event_id,
    customer_id,
    event_type,
    cast(event_ts as timestamp) as event_ts,
    cast(event_date as date) as event_date,
    cast(ingest_ts as timestamp) as ingest_ts,
    session_id,
    product_id
from {{ source('raw', 'raw_events') }}

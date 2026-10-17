select
    refund_id,
    order_id,
    amount as refund_amount,
    cast(refunded_at as timestamp) as refunded_at,
    reason
from {{ source('raw', 'raw_refunds') }}

{{ config(tags=['orders']) }}
select
    customer_id,
    first_name,
    region,
    signup_date,
    order_count,
    lifetime_amount,
    first_order_date,
    last_order_date
from {{ ref('int_customer_orders') }}

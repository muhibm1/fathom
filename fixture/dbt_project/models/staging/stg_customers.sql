select
    customer_id,
    first_name,
    email,
    cast(signup_date as date) as signup_date,
    region
from {{ source('raw', 'raw_customers') }}

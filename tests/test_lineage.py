from orion.lineage import column_lineage, dejinja

SQL = """
{{ config(materialized='table') }}
select
    o.order_id,
    o.amount * (1 - o.discount_pct / 100.0) as net_amount,
    count(p.payment_id) as payment_count
from {{ ref('stg_orders') }} o
left join {{ source('raw', 'raw_payments') }} p on p.order_id = o.order_id
group by 1, 2
"""


def test_dejinja_substitutes_refs_and_sources():
    sql = dejinja(SQL)
    assert "config" not in sql
    assert "from stg_orders o" in sql
    assert "raw__raw_payments p" in sql


def test_column_lineage_reaches_leaf_columns():
    schema = {
        "stg_orders": {"order_id": "int", "amount": "double", "discount_pct": "double"},
        "raw__raw_payments": {"payment_id": "int", "order_id": "int"},
    }
    lin = column_lineage(dejinja(SQL), schema)
    assert lin.error is None
    assert lin.columns == ["order_id", "net_amount", "payment_count"]
    assert lin.derives["net_amount"] == {("stg_orders", "amount"), ("stg_orders", "discount_pct")}
    assert lin.derives["payment_count"] == {("raw.raw_payments", "payment_id")}

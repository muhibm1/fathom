from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {"owner": "team/data-platform", "retries": 2, "retry_delay": timedelta(minutes=5)}

with DAG(
    dag_id="orders_pipeline",
    schedule="0 * * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args=default_args,
    sla_miss_callback=None,
    tags=["orders"],
) as dag:
    load_orders = BashOperator(
        task_id="load_orders",
        bash_command="python jobs/load_raw.py --tables raw_orders,raw_payments,raw_customers,raw_refunds",
    )
    dbt_staging = BashOperator(
        task_id="dbt_staging",
        bash_command="dbt run --select stg_orders stg_payments stg_customers stg_refunds",
    )
    dbt_marts = BashOperator(
        task_id="dbt_marts",
        bash_command="dbt run --select tag:orders",
        sla=timedelta(minutes=45),
    )
    dbt_test = BashOperator(task_id="dbt_test", bash_command="dbt test --select tag:orders")

    load_orders >> dbt_staging >> dbt_marts >> dbt_test

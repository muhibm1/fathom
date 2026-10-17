from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor

with DAG(
    dag_id="finance_close",
    schedule="0 6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={"owner": "team/finance-data", "retries": 0},
    tags=["finance"],
) as dag:
    wait_for_orders = ExternalTaskSensor(
        task_id="wait_for_orders",
        external_dag_id="orders_pipeline",
        external_task_id="dbt_test",
        timeout=3600,
    )
    dbt_finance = BashOperator(
        task_id="dbt_finance",
        bash_command="dbt run --select tag:finance",
        sla=timedelta(minutes=30),
    )
    export_close = BashOperator(
        task_id="export_close",
        bash_command="python jobs/export_close.py --from fct_revenue --from fct_refunds --to s3://finance/close/",
    )
    wait_for_orders >> dbt_finance >> export_close

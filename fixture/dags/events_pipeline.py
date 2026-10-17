from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="events_pipeline",
    schedule="30 2 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={"owner": "team/data-platform", "retries": 1},
    tags=["events"],
) as dag:
    ingest_events = BashOperator(
        task_id="ingest_events",
        bash_command="spark-submit jobs/ingest_events.py --partition-by event_date --target raw_events",
        pool="spark_pool",
    )
    dbt_events = BashOperator(
        task_id="dbt_events",
        bash_command="dbt run --select stg_events+",
        sla=timedelta(hours=2),
    )
    ingest_events >> dbt_events

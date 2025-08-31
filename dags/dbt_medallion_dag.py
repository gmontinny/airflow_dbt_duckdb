from datetime import datetime, timedelta
import os
from airflow import DAG
from airflow.operators.bash import BashOperator

# Caminhos dentro do container do Airflow
DBT_PROJECT_DIR = "/opt/airflow/dbt/dbt_duckdb_medalhao"
# Garantir que o profiles.yml seja localizado; por padrão é ~/.dbt, mas mantemos no projeto
DBT_PROFILES_DIR = "/opt/airflow/dbt/dbt_duckdb_medalhao"

default_args = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="dbt_medallion_pipeline",
    description="Executa o pipeline dbt do medalhão: deps -> seed -> run (landing+bronze+silver+gold) -> test",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["dbt", "duckdb", "medallion"],
) as dag:

    env = {
        "DBT_PROFILES_DIR": DBT_PROFILES_DIR,
    }

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"cd {DBT_PROJECT_DIR} && /home/airflow/.local/bin/dbt deps",
        env=env,
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"cd {DBT_PROJECT_DIR} && /home/airflow/.local/bin/dbt seed --full-refresh",
        env=env,
    )

    dbt_run = BashOperator(
        task_id="dbt_run_medallion",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            "/home/airflow/.local/bin/dbt run --select 'landing_zone+ bronze+ silver+ gold+'"
        ),
        env=env,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_PROJECT_DIR} && /home/airflow/.local/bin/dbt test",
        env=env,
    )

    dbt_deps >> dbt_seed >> dbt_run >> dbt_test

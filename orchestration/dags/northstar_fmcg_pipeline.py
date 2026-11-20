"""Airflow DAG for the Northstar FMCG pipeline.

Each task runs one of the project's existing scripts, in order, using the project's Windows Python
"""
from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

REPO = "/mnt/c/Users/HP/Documents/My DA Stuffs/North star project/northstar-fmcg-data-pipeline"
PYTHON = f"{REPO}/.venv/Scripts/python.exe"


def step(task_id: str, command: str) -> BashOperator:
    return BashOperator(task_id=task_id, bash_command=f'cd "{REPO}" && "{PYTHON}" {command}')


with DAG(
    dag_id="northstar_fmcg_pipeline",
    description="Excel to SQL Server to star schema, with data-quality checks",
    schedule=None,  # run it by hand for now; later this can become "@daily"
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=2)},
    tags=["northstar", "fmcg"],
) as dag:
    load_raw = step("load_raw", "src/load_raw.py")
    data_quality = step("data_quality", "src/run_dq.py")
    build_curated = step("build_curated", "src/build_curated.py")
    apply_views = step("apply_views", "src/run_pipeline.py --from views --skip-checks")
    validate_views = step("validate_views", "src/validate_views.py")

    load_raw >> data_quality >> build_curated >> apply_views >> validate_views
"""Run the whole pipeline with one command.

    python src/run_pipeline.py                  run every step
    python src/run_pipeline.py --skip-checks    run everything except the final validation
    python src/run_pipeline.py --from build     start at a later step (load, dq, build, views, check)

The database objects must already exist (run sql/01 to sql/04 once). 
Each step is also a script you can run on its own. 
If a step fails, the pipeline stops there and tells you which log to read.
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

from check_connection import build_engine, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VIEWS_SQL = PROJECT_ROOT / "sql" / "06_create_analytics_views.sql"


def run_script(name: str) -> None:
    """Run one of the pipeline scripts. Its own output is shown as it runs."""
    result = subprocess.run([sys.executable, str(PROJECT_ROOT / "src" / name)], cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise RuntimeError(f"{name} exited with code {result.returncode}")


def split_batches(sql_text: str) -> list:
    """Split a SQL Server script into batches at the GO lines. Comments are removed first."""
    sql_text = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.S)
    batches, current = [], []
    for line in sql_text.splitlines():
        if line.strip().upper() == "GO":
            if "".join(current).strip():
                batches.append("\n".join(current))
            current = []
        else:
            current.append(line)
    if "".join(current).strip():
        batches.append("\n".join(current))
    return batches


def apply_views() -> None:
    """(Re)create the analytics views. The script is safe to run again."""
    batches = split_batches(VIEWS_SQL.read_text(encoding="utf-8"))
    engine = build_engine(load_config())
    with engine.begin() as conn:
        for batch in batches:
            conn.exec_driver_sql(batch)
    print(f"  {len(batches)} SQL batches applied")


# (key, description, what to run, log to read if it fails)
STEPS = [
    ("load", "Load the Excel sheets into the raw tables", lambda: run_script("load_raw.py"), "logs/raw_load.log"),
    ("dq", "Apply the data-quality rules (staging and quarantine)", lambda: run_script("run_dq.py"), "logs/dq_run.log"),
    ("build", "Build the curated star schema", lambda: run_script("build_curated.py"), "logs/curated_build.log"),
    ("views", "Create the analytics views", apply_views, "the message above"),
    ("check", "Validate the views against independent calculations", lambda: run_script("validate_views.py"), "the output above"),
]


def select_steps(steps: list, start: str = "load", skip_checks: bool = False) -> list:
    """The steps to run: from the chosen start, without the final check if asked."""
    keys = [s[0] for s in steps]
    if start not in keys:
        raise ValueError(f"Unknown step '{start}'. Choose one of: {', '.join(keys)}")
    chosen = steps[keys.index(start):]
    return [s for s in chosen if not (skip_checks and s[0] == "check")]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the whole FMCG pipeline.")
    parser.add_argument("--from", dest="start", default="load", choices=[s[0] for s in STEPS],
                        help="step to start at (default: load)")
    parser.add_argument("--skip-checks", action="store_true", help="do not run the final validation")
    args = parser.parse_args(argv)

    steps = select_steps(STEPS, args.start, args.skip_checks)
    results = []
    overall_start = time.time()
    for number, (key, description, action, log_hint) in enumerate(steps, start=1):
        print(f"\n[{number}/{len(steps)}] {description}")
        started = time.time()
        try:
            action()
        except Exception as exc:
            print(f"\nFAILED at step '{key}': {exc}")
            print(f"Read {log_hint} for details. Nothing after this step was run.")
            return 1
        results.append((key, time.time() - started))

    print("\nPipeline finished.")
    for key, seconds in results:
        print(f"  {key:<6} {seconds:6.1f}s")
    print(f"  total  {time.time() - overall_start:6.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
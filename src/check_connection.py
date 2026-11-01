"""Confirm Python can reach the FMCG_Pipeline database.

Run from the project root:  python src/check_connection.py
"""
from pathlib import Path
from urllib.parse import quote_plus

import yaml
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(PROJECT_ROOT / "config" / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_engine(cfg: dict):
    db = cfg["database"]
    odbc = (
        f"DRIVER={{{db['driver']}}};SERVER={db['server']};DATABASE={db['name']};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}")


if __name__ == "__main__":
    engine = build_engine(load_config())
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT DB_NAME()")).scalar()
        schemas = conn.execute(
            text("SELECT name FROM sys.schemas WHERE name IN ('raw','curated','quarantine','audit') ORDER BY name")
        ).scalars().all()
    print(f"Connected to: {db_name}")
    print(f"Schemas found: {schemas}")

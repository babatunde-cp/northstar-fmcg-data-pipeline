"""Builds the date dimension (one row per calendar day). No database needed."""
from datetime import date

import pandas as pd


def build_dim_date(start: date, end: date) -> pd.DataFrame:
    """Return one row per day from start to end, both included."""
    days = pd.date_range(start, end, freq="D")
    if len(days) == 0:
        raise ValueError("end date is before start date")
    return pd.DataFrame(
        {
            "date_key": (days.year * 10000 + days.month * 100 + days.day).to_numpy(),
            "full_date": days.date,
            "calendar_year": days.year.to_numpy(),
            "calendar_quarter": days.quarter.to_numpy(),
            "calendar_month": days.month.to_numpy(),
            "calendar_month_name": days.month_name().to_numpy(),
            "year_month": days.strftime("%Y-%m").to_numpy(),
            "day_of_month": days.day.to_numpy(),
            "day_of_week": (days.dayofweek + 1).to_numpy(),
            "day_name": days.day_name().to_numpy(),
            "is_weekend": (days.dayofweek >= 5).astype(int),
            "iso_week": days.isocalendar().week.astype(int).to_numpy(),
        }
    )

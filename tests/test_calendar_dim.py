from datetime import date

import pytest

from calendar_dim import build_dim_date


def test_a_normal_year_has_365_days():
    assert len(build_dim_date(date(2025, 1, 1), date(2025, 12, 31))) == 365


def test_a_leap_year_has_366_days():
    assert len(build_dim_date(date(2024, 1, 1), date(2024, 12, 31))) == 366


def test_date_key_format_and_attributes():
    row = build_dim_date(date(2025, 3, 15), date(2025, 3, 15)).iloc[0]
    assert row["date_key"] == 20250315
    assert row["calendar_quarter"] == 1
    assert row["calendar_month_name"] == "March"
    assert row["year_month"] == "2025-03"
    assert row["day_name"] == "Saturday"
    assert row["day_of_week"] == 6
    assert row["is_weekend"] == 1


def test_weekday_is_not_weekend():
    row = build_dim_date(date(2025, 3, 17), date(2025, 3, 17)).iloc[0]  # a Monday
    assert row["day_name"] == "Monday" and row["is_weekend"] == 0 and row["day_of_week"] == 1


def test_date_keys_are_unique():
    df = build_dim_date(date(2025, 1, 1), date(2025, 12, 31))
    assert df["date_key"].is_unique and df["full_date"].is_unique


def test_end_before_start_is_rejected():
    with pytest.raises(ValueError):
        build_dim_date(date(2025, 2, 1), date(2025, 1, 1))

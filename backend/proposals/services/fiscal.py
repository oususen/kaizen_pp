from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

BASE_FISCAL_YEAR = 1973
FISCAL_YEAR_START_MONTH = 10


def fiscal_term(dt: datetime | date) -> int:
    year = dt.year
    if dt.month < FISCAL_YEAR_START_MONTH:
        year -= 1
    return year - BASE_FISCAL_YEAR


def fiscal_quarter(dt: datetime | date) -> int:
    month_offset = (dt.month - FISCAL_YEAR_START_MONTH) % 12
    return month_offset // 3 + 1


def term_date_range(term_number: int) -> tuple[date, date]:
    start_year = BASE_FISCAL_YEAR + term_number
    start_date = date(start_year, FISCAL_YEAR_START_MONTH, 1)
    # end date = start date + 1 year - 1 day
    if FISCAL_YEAR_START_MONTH == 1:
        end_date = date(start_year, 12, 31)
    else:
        next_year = start_year + 1 if FISCAL_YEAR_START_MONTH > 1 else start_year
        next_month = ((FISCAL_YEAR_START_MONTH - 1 + 12) % 12) + 1
        # easier: add 1 year then subtract a day
        temp_start = date(start_year, FISCAL_YEAR_START_MONTH, 1)
        end_date = temp_start.replace(year=temp_start.year + 1) - timedelta(days=1)
    return start_date, end_date


def fiscal_month_sequence() -> list[int]:
    return [((FISCAL_YEAR_START_MONTH - 1 + i) % 12) + 1 for i in range(12)]

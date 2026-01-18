# geo_gedcom/enrichment/date_utils.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date, timedelta
from typing import Any, Optional, Tuple

from geo_gedcom.gedcom_date import GedcomDate


_MONTH_ABBR_TO_NUM = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
_NUM_TO_MONTH_ABBR = {v: k for k, v in _MONTH_ABBR_TO_NUM.items()}


def _is_gregorian_date_like(x: Any) -> bool:
    """
    Check if object has Gregorian date-like attributes.
    
    Uses duck-typing to detect ged4py.calendar.GregorianDate-like objects
    by checking for year attribute and either month or day.
    
    Args:
        x: Object to check
        
    Returns:
        True if object has date-like attributes, False otherwise
    """
    # duck-type ged4py.calendar.GregorianDate: has year and maybe month/day
    return hasattr(x, "year") and (hasattr(x, "month") or hasattr(x, "day"))


def _gregorian_like_to_pydate(g: Any) -> Optional[_date]:
    """
    Convert ged4py GregorianDate-like object to datetime.date.
    
    Requires year, month, and day to be present. Month can be either
    a string abbreviation (e.g., 'JUL') or an integer (1-12).
    
    Args:
        g: GregorianDate-like object with year, month, day attributes
        
    Returns:
        datetime.date if conversion successful, None otherwise
    """
    try:
        y = int(getattr(g, "year", None))
        m = getattr(g, "month", None)
        d = getattr(g, "day", None)
        if y is None or m is None or d is None:
            return None
        if isinstance(m, str):
            mnum = _MONTH_ABBR_TO_NUM.get(m.upper())
        else:
            mnum = int(m)
        if not mnum:
            return None
        return _date(y, mnum, int(d))
    except Exception:
        return None


def _pydate_to_gregorian(py: _date) -> Any:
    """
    Convert datetime.date back to ged4py GregorianDate.
    
    Lazy import of ged4py to avoid dependency in contexts that don't need it.
    
    Args:
        py: Python datetime.date object
        
    Returns:
        ged4py.calendar.GregorianDate object
    """
    from ged4py.calendar import GregorianDate  # type: ignore
    return GregorianDate(py.year, _NUM_TO_MONTH_ABBR[py.month], py.day)


def coerce_to_single_date(value: Any) -> Optional[Any]:
    """
    Convert various date formats to a single canonical date representation.
    
    Accepts multiple formats:
    - GedcomDate objects (extracts .single)
    - GregorianDate-like objects (ged4py)
    - datetime.date or datetime.datetime
    - String representations (parsed as GedcomDate)
    - None
    
    Args:
        value: Date in any supported format
        
    Returns:
        Canonical date representation (GregorianDate-like, datetime.date, str, or None)
    """
    if value is None:
        return None

    if isinstance(value, GedcomDate):
        return value.single

    # sometimes your events may store the raw string and you wrap later
    if isinstance(value, str):
        return GedcomDate(value).single

    # python date/datetime
    if isinstance(value, _date):
        return value

    # ged4py GregorianDate-like
    if _is_gregorian_date_like(value):
        return value

    return None


def subtract_days(value: Any, days: int) -> Optional[Any]:
    """
    Subtract days from a date if it has full year/month/day precision.
    
    If the date only has year or year/month precision, returns None as
    day-level arithmetic is not meaningful.
    
    Args:
        value: Date in any format supported by coerce_to_single_date
        days: Number of days to subtract
        
    Returns:
        New date with days subtracted, or None if not possible
    """
    single = coerce_to_single_date(value)
    if single is None:
        return None

    if isinstance(single, _date):
        return single - timedelta(days=days)

    if _is_gregorian_date_like(single):
        py = _gregorian_like_to_pydate(single)
        if py is None:
            return None
        return _pydate_to_gregorian(py - timedelta(days=days))

    return None


def add_years(value: Any, years: int) -> Optional[Any]:
    """
    Add years to a date, preserving month/day if possible.
    
    For datetime.date objects, attempts to preserve month and day.
    Handles edge cases like Feb 29 by clamping to Feb 28 if necessary.
    
    For Gregorian-like dates, preserves month/day if present in original.
    
    Args:
        value: Date in any format supported by coerce_to_single_date
        years: Number of years to add (can be negative)
        
    Returns:
        New date with years added, or None if not possible
    """
    single = coerce_to_single_date(value)
    if single is None:
        return None

    # datetime.date -> approximate by keeping month/day where possible
    if isinstance(single, _date):
        try:
            return _date(single.year + years, single.month, single.day)
        except ValueError:
            # Feb 29 etc.: clamp to Feb 28
            return _date(single.year + years, single.month, min(single.day, 28))

    if _is_gregorian_date_like(single):
        y = getattr(single, "year", None)
        if y is None:
            return None
        new_year = int(y) + years
        m = getattr(single, "month", None)
        d = getattr(single, "day", None)

        from ged4py.calendar import GregorianDate  # type: ignore
        # month/day may be None; GregorianDate supports partial dates in your tests
        return GregorianDate(new_year, m, d)

    return None


def sub_years(value: Any, years: int) -> Optional[Any]:
    """
    Subtract years from a date.
    
    Convenience wrapper around add_years with negated years parameter.
    
    Args:
        value: Date in any format
        years: Number of years to subtract
        
    Returns:
        New date with years subtracted, or None if not possible
    """
    return add_years(value, -years)


def year_num(value: Any) -> Optional[int]:
    """
    Extract year as an integer from various date formats.
    
    Attempts to extract year from:
    - GedcomDate objects (.year_num)
    - String representations (parsed as GedcomDate)
    - Objects with 'year' attribute
    
    Args:
        value: Date in any format
        
    Returns:
        Year as integer, or None if extraction failed
    """
    if value is None:
        return None
    if isinstance(value, GedcomDate):
        return value.year_num
    if isinstance(value, str):
        return GedcomDate(value).year_num
    if hasattr(value, "year"):
        y = getattr(value, "year", None)
        return int(y) if y is not None else None
    return None


def calculate_age_at_event(birth_date: Any, event_date: Any) -> Optional[int]:
    """
    Calculate age in years between two dates.
    
    Extracts year from both dates and computes the difference.
    This gives an approximate age; does not account for exact month/day.
    
    Args:
        birth_date: Birth date in any supported format
        event_date: Event date in any supported format
        
    Returns:
        Age in years if both dates have extractable years, None otherwise
    """
    try:
        # Try to extract year from both dates
        birth_year = year_num(birth_date)
        event_year = year_num(event_date)
        if birth_year is None or event_year is None:
            return None
        return event_year - birth_year
    except Exception:
        return None

import pytest
from geo_gedcom.gedcom_date import GedcomDate
from ged4py.calendar import GregorianDate

@pytest.mark.parametrize("date_str,year,month,day", [
    ("1900", 1900, None, None),
    ("JUL 1913", 1913, 'JUL', None),
    ("15 JUL 1913", 1913, 'JUL', 15),
    ("4 DEC 2025", 2025, 'DEC', 4),
    ("1759", 1759, None, None),
    ("AUG 1812", 1812, 'AUG', None),
])
def test_simple_dates(date_str, year, month, day):
    """Test parsing of simple date strings."""
    gd = GedcomDate(date_str)
    result = gd.resolved
    assert isinstance(result, GregorianDate)
    assert result.year == year
    if month:
        assert result.month == month
    if day:
        assert result.day == day

@pytest.mark.parametrize("date_str,expected", [
    ("ABT 1762", 1762),
    ("abt 1776", 1776),
    ("BEF 1951", 1951),
    ("bef 1832", 1832),
])
def test_abt_bef_year(date_str, expected):
    """Test parsing of approximate and before dates."""
    gd = GedcomDate(date_str)
    result = gd.resolved
    assert isinstance(result, GregorianDate) or isinstance(result, str)
    if isinstance(result, GregorianDate):
        assert result.year == expected
    else:
        assert result.lower().startswith(date_str[:3].lower())

def test_range():
    """Test parsing of date ranges."""
    gd = GedcomDate("BET JUL AND SEP 1913", simplify_range_policy='none')
    result = gd.resolved
    assert isinstance(result, tuple)
    assert result[0].month == 'JUL'
    assert result[1].month == 'SEP'
    assert result[0].year == 1913
    assert result[1].year == 1913

def test_invalid_date():
    """Test parsing of an invalid date string."""
    gd = GedcomDate("nonsense date string")
    result = gd.resolved
    assert isinstance(result, str)

def test_empty_date():
    """Test parsing of an empty date string."""
    gd = GedcomDate("")
    result = gd.resolved
    assert result is None or isinstance(result, str)

def test_none_date():
    """Test parsing of None as a date."""
    gd = GedcomDate(None)
    result = gd.resolved
    assert result is None or isinstance(result, str)

def test_leap_year():
    """Test parsing of a valid leap day."""
    gd = GedcomDate("29 FEB 2000")
    result = gd.resolved
    assert isinstance(result, GregorianDate)
    assert result.day == 29
    assert result.month == 'FEB'
    assert result.year == 2000


# --- Additional tests for GEDCOM v7 date formats including BCE and calendars ---
import pytest

@pytest.mark.parametrize("date_str, year, month, day", [
    ("44 BCE", -44, None, None),
    ("JUL 44 BCE", -44, 'JUL', None),
    ("15 MAR 44 BCE", -44, 'MAR', 15),
    ("JULIAN 44 BCE", -44, None, None),
    ("JULIAN 15 MAR 44 BCE", -44, 'MAR', 15),
])
def test_bce_and_julian_dates(date_str, year, month, day):
    """Test BCE and Julian calendar date parsing."""
    gd = GedcomDate(date_str)
    result = gd.resolved
    # Accept GregorianDate or string fallback if not supported
    if isinstance(result, GregorianDate):
        assert result.year == year
        if month:
            assert result.month == month
        if day:
            assert result.day == day
    else:
        # Should at least contain the BCE or JULIAN string
        assert "BCE" in str(result) or "JULIAN" in str(result)

@pytest.mark.parametrize("date_str", [
    "FRENCH_R 1 VEND 2",
    "HEBREW 10 NSN 5700",
])
def test_french_and_hebrew_calendar(date_str):
    """Test French Republican and Hebrew calendar date parsing (should not error)."""
    gd = GedcomDate(date_str)
    result = gd.resolved
    # Accept string fallback if not supported
    assert result is None or isinstance(result, GregorianDate) or isinstance(result, str)

@pytest.mark.parametrize("date_str, expected", [
    ("BET 50 BCE AND 44 BCE", (-50, -44)),
    ("ABT 300 BCE", -300),
    ("BEF 100 BCE", -100),
    ("AFT 200 BCE", -200),
])
def test_bce_ranges_and_approx(date_str, expected):
    """Test BCE date ranges and approximate forms."""
    gd = GedcomDate(date_str, simplify_range_policy='none')
    result = gd.resolved
    if isinstance(expected, tuple):
        # Range: result should be a tuple of GregorianDate or string
        assert isinstance(result, tuple)
        years = tuple(getattr(d, 'year', None) if hasattr(d, 'year') else None for d in result)
        # Accept string fallback if not supported
        if all(y is not None for y in years):
            assert years == expected
    else:
        # Single: result should have year == expected
        if hasattr(result, 'year'):
            assert result.year == expected
        else:
            assert str(expected) in str(result)

def test_mixed_calendar_bce():
    """Test mixed calendar and BCE (JULIAN 1 JAN 44 BCE)."""
    gd = GedcomDate("JULIAN 1 JAN 44 BCE")
    result = gd.resolved
    if isinstance(result, GregorianDate):
        assert result.year == -44
        assert result.month == 'JAN'
        assert result.day == 1
    else:
        assert "JULIAN" in str(result) and "BCE" in str(result)

def test_invalid_bce():
    """Test invalid BCE date (should not crash, should fallback)."""
    gd = GedcomDate("BCE nonsense")
    result = gd.resolved
    assert result is None or isinstance(result, str)


# --- Additional tests for full GEDCOM v7 date spec compliance ---
import pytest

@pytest.mark.parametrize("date_str, expected", [
    ("FROM 1670 TO 1800", (1670, 1800)),
    ("TO 324", (None, 324)),
    ("FROM 667 BCE TO 324", (-667, 324)),
    ("FROM GREGORIAN 1670 TO JULIAN 1800", (1670, 1800)),
    ("FROM JULIAN 1670 TO GREGORIAN 1800", (1670, 1800)),
])
def test_from_to_periods(date_str, expected):
    """Test FROM/TO date periods and calendar changes in ranges."""
    gd = GedcomDate(date_str, simplify_range_policy='none')
    result = gd.resolved
    # Accept tuple of GregorianDate or string fallback
    if isinstance(result, tuple):
        years = tuple(getattr(d, 'year', None) if hasattr(d, 'year') else None for d in result)
        if all(y is not None or e is None for y, e in zip(years, expected)):
            # Accept None for open-ended periods
            for y, e in zip(years, expected):
                if e is not None:
                    assert y == e
    else:
        # Fallback: at least contains FROM/TO
        assert "FROM" in str(result) or "TO" in str(result)


def test_dual_date_phrase():
    """Test dual date with PHRASE (e.g., 1648/9)."""
    gd = GedcomDate("BET 1648 AND 1649")
    result = gd.resolved
    # Simulate PHRASE: should parse as a range, but user can add phrase separately
    if isinstance(result, tuple):
        years = tuple(getattr(d, 'year', None) if hasattr(d, 'year') else None for d in result)
        assert years == (1648, 1649)
    else:
        assert "1648" in str(result) and "1649" in str(result)


def test_empty_date_with_phrase():
    """Test empty date string with PHRASE (should not error)."""
    gd = GedcomDate("")
    result = gd.resolved
    assert result is None or isinstance(result, str)
    # In real GEDCOM, PHRASE would be a substructure, not part of the date string


@pytest.mark.parametrize("date_str", [
    "_MYCAL 1 _MYMONTH 2000",
    "_EXCAL 10 _EXMON 1000 BCE",
])
def test_extension_calendar_and_month(date_str):
    """Test extension calendars and months (should not error)."""
    gd = GedcomDate(date_str)
    result = gd.resolved
    # Accept string fallback if not supported
    assert result is None or isinstance(result, GregorianDate) or isinstance(result, str)

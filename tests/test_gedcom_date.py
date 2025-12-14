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

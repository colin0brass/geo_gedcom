# /Users/osborne/git/gedcom-to-visualmap/gedcom-to-map/geo_gedcom/enrichment/tests/test_date_utils.py
"""
Tests for enrichment.date_utils module.
"""
from __future__ import annotations

import pytest
from datetime import date as _date

from geo_gedcom.enrichment.date_utils import (
    coerce_to_single_date,
    subtract_days,
    add_years,
    sub_years,
    year_num,
    calculate_age_at_event
)
from geo_gedcom.gedcom_date import GedcomDate


class TestCoerceToSingleDate:
    """Tests for coerce_to_single_date function."""
    
    def test_none_input(self):
        """Test that None returns None."""
        assert coerce_to_single_date(None) is None
    
    def test_gedcom_date_input(self):
        """Test with GedcomDate input."""
        gd = GedcomDate("1 JAN 1900")
        result = coerce_to_single_date(gd)
        assert result is not None
    
    def test_string_input(self):
        """Test with string input."""
        result = coerce_to_single_date("1 JAN 1900")
        assert result is not None
    
    def test_python_date_input(self):
        """Test with datetime.date input."""
        d = _date(1900, 1, 1)
        result = coerce_to_single_date(d)
        assert result == d


class TestSubtractDays:
    """Tests for subtract_days function."""
    
    def test_subtract_days_from_date(self):
        """Test subtracting days from datetime.date."""
        d = _date(1900, 1, 15)
        result = subtract_days(d, 10)
        assert result == _date(1900, 1, 5)
    
    def test_subtract_days_crosses_month(self):
        """Test subtracting days across month boundary."""
        d = _date(1900, 2, 5)
        result = subtract_days(d, 10)
        assert result == _date(1900, 1, 26)
    
    def test_subtract_days_none(self):
        """Test subtracting from None returns None."""
        result = subtract_days(None, 10)
        assert result is None


class TestAddYears:
    """Tests for add_years function."""
    
    def test_add_years_to_date(self):
        """Test adding years to datetime.date."""
        d = _date(1900, 6, 15)
        result = add_years(d, 25)
        assert result == _date(1925, 6, 15)
    
    def test_add_years_leap_day(self):
        """Test adding years to Feb 29 (leap day)."""
        d = _date(2000, 2, 29)  # Leap year
        result = add_years(d, 1)  # 2001 is not a leap year
        assert result == _date(2001, 2, 28)  # Should clamp to Feb 28
    
    def test_add_years_negative(self):
        """Test adding negative years (going backwards)."""
        d = _date(1950, 6, 15)
        result = add_years(d, -25)
        assert result == _date(1925, 6, 15)
    
    def test_add_years_none(self):
        """Test adding years to None returns None."""
        result = add_years(None, 10)
        assert result is None


class TestSubYears:
    """Tests for sub_years function."""
    
    def test_sub_years_from_date(self):
        """Test subtracting years from datetime.date."""
        d = _date(1950, 6, 15)
        result = sub_years(d, 25)
        assert result == _date(1925, 6, 15)
    
    def test_sub_years_none(self):
        """Test subtracting years from None returns None."""
        result = sub_years(None, 10)
        assert result is None


class TestYearNum:
    """Tests for year_num function."""
    
    def test_year_num_none(self):
        """Test extracting year from None returns None."""
        assert year_num(None) is None
    
    def test_year_num_gedcom_date(self):
        """Test extracting year from GedcomDate."""
        gd = GedcomDate("15 JUN 1925")
        result = year_num(gd)
        assert result == 1925
    
    def test_year_num_string(self):
        """Test extracting year from string."""
        result = year_num("1925")
        assert result == 1925
    
    def test_year_num_date_object(self):
        """Test extracting year from datetime.date."""
        d = _date(1925, 6, 15)
        result = year_num(d)
        assert result == 1925


class TestCalculateAgeAtEvent:
    """Tests for calculate_age_at_event function."""
    
    def test_calculate_age_basic(self):
        """Test calculating age with datetime.date objects."""
        birth = _date(1950, 1, 1)
        event = _date(1975, 1, 1)
        result = calculate_age_at_event(birth, event)
        assert result == 25
    
    def test_calculate_age_with_gedcom_dates(self):
        """Test calculating age with GedcomDate objects."""
        birth = GedcomDate("1 JAN 1950")
        event = GedcomDate("1 JAN 1975")
        result = calculate_age_at_event(birth, event)
        assert result == 25
    
    def test_calculate_age_none_birth(self):
        """Test with None birth date returns None."""
        event = _date(1975, 1, 1)
        result = calculate_age_at_event(None, event)
        assert result is None
    
    def test_calculate_age_none_event(self):
        """Test with None event date returns None."""
        birth = _date(1950, 1, 1)
        result = calculate_age_at_event(birth, None)
        assert result is None
    
    def test_calculate_age_negative(self):
        """Test with event before birth (negative age)."""
        birth = _date(1975, 1, 1)
        event = _date(1950, 1, 1)
        result = calculate_age_at_event(birth, event)
        assert result == -25
    
import pytest
from geo_gedcom import LifeEvent, LatLon

@pytest.mark.parametrize(
    "place,date,what,expected_year,expected_month,expected_place",
    [
        ("London", "1900", "BIRT", 1900, None, "London"),
        ("Luanshya, Zambia", "16 JUN 1970", "BIRT", 1970, "JUN", "Luanshya, Zambia"),
        (None, "1759", "BIRT", 1759, None, None),
        (None, "ABT 1762", "BIRT", 1762, None, None),
        ("Eastfield, Hickling, Norfolk, England", "1841", "RESI", 1841, None, "Eastfield, Hickling, Norfolk, England"),
        ("Norfolk, England", "13 NOV 1831", "BAPM", 1831, "NOV", "Norfolk, England"),
        ("Swansea, Glamorgan, Wales", "24 NOV 1990", "DEAT", 1990, "NOV", "Swansea, Glamorgan, Wales"),
        ("North Mymms, Welwyn Hatfield District, Hertfordshire, England", "1812", "BURI", 1812, None, "North Mymms, Welwyn Hatfield District, Hertfordshire, England"),
    ]
)
def test_life_event_various(place, date, what, expected_year, expected_month, expected_place):
    """Test LifeEvent creation for various event types and date formats."""
    event = LifeEvent(place=place, date=date, what=what)
    assert event.what == what
    assert event.place == expected_place
    assert event.date.year_num == expected_year
    if expected_month:
        assert event.date.single.month == expected_month

def test_life_event_with_location():
    """Test LifeEvent with explicit LatLon location."""
    latlon = LatLon(51.5, -0.1)
    event = LifeEvent(place="London", date="1900", latlon=latlon, what="BIRT")
    assert event.location.latlon == latlon
    assert event.location is not None
    assert event.location.latlon.lat == 51.5
    assert event.location.latlon.lon == -0.1

@pytest.mark.parametrize(
    "place,date,what",
    [
        (None, None, "BIRT"),
        ("", "", "BIRT"),
        ("Unknown", "INVALID DATE", "BIRT"),
        ("Somewhere", "2020", "UNKNOWN"),
    ]
)
def test_life_event_edge_cases(place, date, what):
    """Test LifeEvent with missing, empty, or invalid data."""
    event = LifeEvent(place=place, date=date, what=what)
    assert event.what == what
    # Place may be None or empty string
    assert event.place == place
    # Date parsing: year_num may be None for invalid date
    if date and date.isdigit():
        assert event.date.year_num == int(date)
    elif date and "INVALID" in date:
        assert event.date.year_num is None

def test_life_event_repr_str():
    """Test __repr__ and __str__ methods for LifeEvent (if implemented)."""
    event = LifeEvent(place="London", date="1900", what="BIRT")
    assert "London" in repr(event)
    assert "BIRT" in str(event)

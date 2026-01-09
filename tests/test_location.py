import pytest
from geo_gedcom.location import Location
from geo_gedcom.lat_lon import LatLon

def test_location_init():
    """Test Location initialization with valid data."""
    loc = Location(address="Test Address", latlon=LatLon(lat=51.5, lon=-0.1))
    assert loc.address == "Test Address"
    assert loc.latlon.lat == 51.5
    assert loc.latlon.lon == -0.1

def test_location_empty_address():
    """Test Location with empty address."""
    loc = Location(address="", latlon=LatLon(lat=0.0, lon=0.0))
    assert loc.address == ""
    assert loc.latlon.lat == 0.0
    assert loc.latlon.lon == 0.0

def test_location_str_repr():
    """Test __str__ and __repr__ methods for Location if implemented."""
    loc = Location(address="Test", latlon=LatLon(lat=10.0, lon=20.0))
    assert "Test" in str(loc)
    assert "Test" in repr(loc)

import pytest
from geo_gedcom.lat_lon import LatLon

def test_latlon_init():
    """Test LatLon initialization with valid data."""
    ll = LatLon(51.5, -0.1)
    assert ll.lat == 51.5
    assert ll.lon == -0.1

def test_latlon_negative_coordinates():
    """Test LatLon with negative coordinates."""
    ll = LatLon(-45.0, -90.0)
    assert ll.lat == -45.0
    assert ll.lon == -90.0

def test_latlon_zero_coordinates():
    """Test LatLon with zero coordinates."""
    ll = LatLon(0.0, 0.0)
    assert ll.lat == 0.0
    assert ll.lon == 0.0

def test_latlon_missing_arguments():
    """Test LatLon initialization with missing arguments."""
    with pytest.raises(TypeError):
        LatLon(51.5)  # Missing longitude

def test_latlon_str_repr():
    """Test __str__ and __repr__ methods for LatLon if implemented."""
    ll = LatLon(10.0, 20.0)
    assert "10.0" in str(ll)
    assert "20.0" in repr(ll)
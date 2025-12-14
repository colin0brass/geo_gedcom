import pytest
from geo_gedcom.partner import Partner
from geo_gedcom.lat_lon import LatLon

def test_partner_init():
    """Test Partner initialization with valid LatLon."""
    p = Partner("@I1@", LatLon(51.5, -0.1))
    assert p.xref_id == "@I1@"
    assert p.latlon.lat == 51.5
    assert p.latlon.lon == -0.1

def test_partner_str_repr():
    """Test __str__ and __repr__ methods if implemented."""
    p = Partner("@I4@", LatLon(40.0, -75.0))
    assert "@I4@" in str(p)
    assert "@I4@" in repr(p)

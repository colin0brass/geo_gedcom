from geo_gedcom.location import Location
from geo_gedcom.lat_lon import LatLon

def test_location_init():
    loc = Location(address="Test Address", latitude=51.5, longitude=-0.1)
    assert loc.address == "Test Address"
    assert loc.latlon.lat == 51.5
    assert loc.latlon.lon == -0.1

def test_latlon_init():
    ll = LatLon(51.5, -0.1)
    assert ll.lat == 51.5
    assert ll.lon == -0.1

from geo_gedcom.partner import Partner
from geo_gedcom.lat_lon import LatLon

def test_partner_init():
    p = Partner("@I1@", LatLon(51.5, -0.1))
    assert p.xref_id == "@I1@"
    assert p.latlon.lat == 51.5
    assert p.latlon.lon == -0.1

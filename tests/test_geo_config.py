from geo_gedcom.geo_config import GeoConfig

def test_geo_config_init():
    config = GeoConfig()
    assert isinstance(config, GeoConfig)

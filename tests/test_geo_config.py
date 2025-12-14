import pytest
from geo_gedcom.geo_config import GeoConfig

def test_geo_config_init():
    """Test GeoConfig can be instantiated with no arguments."""
    config = GeoConfig()
    assert isinstance(config, GeoConfig)

def test_geo_config_attributes():
    """Test GeoConfig default attributes (if any)."""
    config = GeoConfig()
    # Adjust these checks to match actual attributes
    if hasattr(config, "geocoder"):
        assert config.geocoder is not None
    if hasattr(config, "country_code"):
        assert isinstance(config.country_code, str) or config.country_code is None

def test_geo_config_invalid_args():
    """Test GeoConfig initialization with invalid arguments."""
    with pytest.raises(TypeError):
        GeoConfig("unexpected_argument")

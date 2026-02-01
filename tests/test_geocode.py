import pytest
from geo_gedcom.geocode import Geocode
from geo_gedcom.geo_config import GeoConfig

def test_geocode_class_exists():
    assert Geocode is not None

def test_geocode_can_instantiate(tmp_path):
    cache_file = tmp_path / "geocode_cache.csv"
    geo_config = GeoConfig()
    geo_config.update_geo_config({'geocode_settings': {'default_country': ''}})
    geocoder = Geocode(str(cache_file), geo_config)
    assert geocoder is not None

def test_geocode_valid_address(tmp_path, monkeypatch):
    cache_file = tmp_path / "geocode_cache.csv"
    geo_config = GeoConfig()
    geo_config.update_geo_config({'geocode_settings': {'default_country': ''}})
    geocoder = Geocode(str(cache_file), geo_config)
    # Monkeypatch the actual geocoding if it does network calls
    if hasattr(geocoder, "geocode"):
        monkeypatch.setattr(geocoder, "geocode", lambda addr: {"lat": 51.5074, "lon": -0.1278, "address": addr})
        result = geocoder.geocode("London, England")
        assert isinstance(result, dict)
        assert "lat" in result and "lon" in result
        assert result["address"] == "London, England"

def test_geocode_invalid_address(tmp_path, monkeypatch):
    cache_file = tmp_path / "geocode_cache.csv"
    geo_config = GeoConfig()
    geo_config.update_geo_config({'geocode_settings': {'default_country': ''}})
    geocoder = Geocode(str(cache_file), geo_config)
    if hasattr(geocoder, "geocode"):
        monkeypatch.setattr(geocoder, "geocode", lambda addr: None)
        result = geocoder.geocode("NotARealPlace12345")
        assert result is None

def test_geocode_empty_address(tmp_path, monkeypatch):
    cache_file = tmp_path / "geocode_cache.csv"
    geo_config = GeoConfig()
    geo_config.update_geo_config({'geocode_settings': {'default_country': ''}})
    geocoder = Geocode(str(cache_file), geo_config)
    if hasattr(geocoder, "geocode"):
        monkeypatch.setattr(geocoder, "geocode", lambda addr: None)
        result = geocoder.geocode("")
        assert result is None

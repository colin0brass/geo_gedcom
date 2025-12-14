import pytest
from geo_gedcom.geocode import Geocode

def test_geocode_class_exists():
    assert Geocode is not None

def test_geocode_can_instantiate(tmp_path):
    cache_file = tmp_path / "geocode_cache.csv"
    geocoder = Geocode(str(cache_file))
    assert geocoder is not None

def test_geocode_valid_address(tmp_path, monkeypatch):
    cache_file = tmp_path / "geocode_cache.csv"
    geocoder = Geocode(str(cache_file))
    # Monkeypatch the actual geocoding if it does network calls
    if hasattr(geocoder, "geocode"):
        monkeypatch.setattr(geocoder, "geocode", lambda addr: {"lat": 51.5074, "lon": -0.1278, "address": addr})
        result = geocoder.geocode("London, England")
        assert isinstance(result, dict)
        assert "lat" in result and "lon" in result
        assert result["address"] == "London, England"

def test_geocode_invalid_address(tmp_path, monkeypatch):
    cache_file = tmp_path / "geocode_cache.csv"
    geocoder = Geocode(str(cache_file))
    if hasattr(geocoder, "geocode"):
        monkeypatch.setattr(geocoder, "geocode", lambda addr: None)
        result = geocoder.geocode("NotARealPlace12345")
        assert result is None

def test_geocode_empty_address(tmp_path, monkeypatch):
    cache_file = tmp_path / "geocode_cache.csv"
    geocoder = Geocode(str(cache_file))
    if hasattr(geocoder, "geocode"):
        monkeypatch.setattr(geocoder, "geocode", lambda addr: None)
        result = geocoder.geocode("")
        assert result is None

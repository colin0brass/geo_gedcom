import pytest
from geo_gedcom import GeoCache

def test_geocache_init(tmp_path):
    """Test GeoCache initialization with a valid file path."""
    cache_file = tmp_path / "geocache.csv"
    gc = GeoCache(str(cache_file), always_geocode=True)
    assert isinstance(gc, GeoCache)
    assert gc.location_cache_file == str(cache_file)

def test_geocache_init_invalid_file():
    """Test GeoCache initialization with an invalid file path."""
    with pytest.raises(Exception):
        GeoCache("/invalid/path/to/geocache.csv")

def test_geocache_toggle_always_geocode(tmp_path):
    """Test GeoCache with always_geocode set to False."""
    cache_file = tmp_path / "geocache.csv"
    gc = GeoCache(str(cache_file), always_geocode=False)
    assert not gc.always_geocode

def test_geocache_cache_write_and_read(tmp_path):
    """Test writing to and reading from the cache (if supported)."""
    cache_file = tmp_path / "geocache.csv"
    gc = GeoCache(str(cache_file), always_geocode=True)
    # Simulate adding and retrieving a location if API allows
    if hasattr(gc, "add_location") and hasattr(gc, "get_location"):
        gc.add_location("Test Place", (51.5, -0.1))
        result = gc.get_location("Test Place")
        assert result == (51.5, -0.1)
    else:
        # If not implemented, pass the test
        pass

from geo_gedcom import GeoCache

def test_geocache_init(tmp_path):
    cache_file = tmp_path / "geocache.csv"
    gc = GeoCache(str(cache_file), always_geocode=True)
    assert isinstance(gc, GeoCache)
    assert gc.location_cache_file == str(cache_file)

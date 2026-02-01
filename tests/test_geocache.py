import pytest
import csv
from geo_gedcom import GeoCache
from geo_gedcom.location import Location
from geo_gedcom.lat_lon import LatLon
from geo_gedcom.geocache import GeoCacheEntry

def test_geocache_init(tmp_path):
    """Test GeoCache initialization with a valid file path."""
    cache_file = tmp_path / "geocache.csv"
    gc = GeoCache(str(cache_file), always_geocode=True)
    assert isinstance(gc, GeoCache)
    assert gc.location_cache_file == str(cache_file)
    assert gc.always_geocode is True

def test_geocache_init_with_nonexistent_file(tmp_path):
    """Test GeoCache initialization with a non-existent file path (should not raise)."""
    cache_file = tmp_path / "nonexistent.csv"
    gc = GeoCache(str(cache_file), always_geocode=False)
    assert isinstance(gc, GeoCache)
    assert gc.location_cache_file == str(cache_file)

def test_geocache_toggle_always_geocode(tmp_path):
    """Test GeoCache with always_geocode set to False."""
    cache_file = tmp_path / "geocache.csv"
    gc = GeoCache(str(cache_file), always_geocode=False)
    assert not gc.always_geocode

def test_geocache_add_and_lookup_entry(tmp_path):
    """Test adding a geocache entry and looking it up."""
    cache_file = tmp_path / "geocache.csv"
    gc = GeoCache(str(cache_file), always_geocode=False)
    
    location = Location(
        used=1,
        latlon=LatLon(51.5074, -0.1278),
        country_code='GB',
        country_name='United Kingdom',
        continent='Europe',
        found_country=True,
        address='London, UK'
    )
    
    gc.add_geo_cache_entry('London', location)
    
    # Lookup the entry
    use_addr, cache_entry = gc.lookup_geo_cache_entry('London')
    assert use_addr == 'London'
    assert cache_entry is not None
    assert cache_entry.country_code == 'GB'
    assert cache_entry.latitude == 51.5074
    assert cache_entry.longitude == -0.1278

def test_geocache_add_no_result_entry(tmp_path):
    """Test adding a no-result entry to the cache."""
    cache_file = tmp_path / "geocache.csv"
    gc = GeoCache(str(cache_file), always_geocode=False)
    
    gc.add_no_result_entry('Nonexistent Place')
    
    use_addr, cache_entry = gc.lookup_geo_cache_entry('Nonexistent Place')
    assert cache_entry is not None
    assert cache_entry.no_result is True

def test_geocache_save_and_load(tmp_path):
    """Test saving and loading the geocache."""
    cache_file = tmp_path / "geocache.csv"
    
    # Create cache and add entries
    gc1 = GeoCache(str(cache_file), always_geocode=False)
    location = Location(
        used=1,
        latlon=LatLon(48.8566, 2.3522),
        country_code='FR',
        country_name='France',
        continent='Europe',
        found_country=True,
        address='Paris, France'
    )
    gc1.add_geo_cache_entry('Paris', location)
    gc1.save_geo_cache()
    
    # Load cache in new instance
    gc2 = GeoCache(str(cache_file), always_geocode=False)
    use_addr, cache_entry = gc2.lookup_geo_cache_entry('Paris')
    
    assert cache_entry is not None
    assert cache_entry.country_code == 'FR'
    assert cache_entry.country_name == 'France'
    assert float(cache_entry.latitude) == 48.8566
    assert float(cache_entry.longitude) == 2.3522

def test_geocache_case_insensitive_lookup(tmp_path):
    """Test that geocache lookups are case-insensitive."""
    cache_file = tmp_path / "geocache.csv"
    gc = GeoCache(str(cache_file), always_geocode=False)
    
    location = Location(
        used=1,
        latlon=LatLon(40.7128, -74.0060),
        country_code='US',
        country_name='United States',
        continent='North America',
        found_country=True,
        address='New York, USA'
    )
    
    gc.add_geo_cache_entry('New York', location)
    
    # Try different cases
    use_addr1, entry1 = gc.lookup_geo_cache_entry('new york')
    use_addr2, entry2 = gc.lookup_geo_cache_entry('NEW YORK')
    use_addr3, entry3 = gc.lookup_geo_cache_entry('New York')
    
    assert entry1 is not None
    assert entry2 is not None
    assert entry3 is not None
    assert entry1.country_code == entry2.country_code == entry3.country_code == 'US'

def test_geocache_empty_when_always_geocode(tmp_path):
    """Test that cache is not loaded when always_geocode is True."""
    cache_file = tmp_path / "geocache.csv"
    
    # Create and save cache
    gc1 = GeoCache(str(cache_file), always_geocode=False)
    location = Location(
        used=1,
        latlon=LatLon(52.5200, 13.4050),
        country_code='DE',
        country_name='Germany',
        continent='Europe',
        found_country=True,
        address='Berlin, Germany'
    )
    gc1.add_geo_cache_entry('Berlin', location)
    gc1.save_geo_cache()
    
    # Load with always_geocode=True
    gc2 = GeoCache(str(cache_file), always_geocode=True)
    assert len(gc2.geo_cache) == 0  # Should not load cache

def test_geocache_entry_from_dict():
    """Test GeoCacheEntry.from_dict with various input formats."""
    data = {
        'address': 'Test Address',
        'latitude': '51.5',
        'longitude': '-0.1',
        'country_code': 'GB',
        'country_name': 'United Kingdom',
        'continent': 'Europe',
        'found_country': 'true',
        'no_result': 'false',
        'timestamp': '1234567890.5',
        'used': '3'
    }
    
    entry = GeoCacheEntry.from_dict(data)
    assert entry.address == 'Test Address'
    assert entry.latitude == '51.5'
    assert entry.longitude == '-0.1'
    assert entry.country_code == 'GB'
    assert entry.found_country is True
    assert entry.no_result is False
    assert entry.timestamp == 1234567890.5
    assert entry.used == 3

def test_geocache_entry_as_dict():
    """Test GeoCacheEntry.as_dict serialization."""
    entry = GeoCacheEntry(
        address='Test',
        latitude='51.5',
        longitude='-0.1',
        country_code='GB',
        found_country=True,
        no_result=False,
        timestamp=1234567890.5,
        used=2
    )
    
    d = entry.as_dict()
    assert d['address'] == 'Test'
    assert d['found_country'] == 'True'
    assert d['no_result'] == 'False'
    assert d['timestamp'] == '1234567890.5'
    assert d['used'] == '2'

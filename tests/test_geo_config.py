import pytest
from pathlib import Path
from geo_gedcom.geo_config import GeoConfig


def _default_geo_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "geo_config.yaml"

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

def test_geo_config_get_set():
    """Test get_geo_config and set_geo_config methods."""
    config = GeoConfig()
    
    # Set a value
    config.set_geo_config('test_key', 'test_value')
    
    # Get the value
    value = config.get_geo_config('test_key')
    assert value == 'test_value'
    
    # Get entire config
    all_config = config.get_geo_config()
    assert 'test_key' in all_config
    assert all_config['test_key'] == 'test_value'

def test_geo_config_update_from_dict():
    """Test update_geo_config method to update multiple settings from a dict."""
    config = GeoConfig()
    
    # Update with a dictionary
    updates = {
        'setting1': 'value1',
        'setting2': 42,
        'setting3': {'nested': 'dict'}
    }
    config.update_geo_config(updates)
    
    # Verify all settings were updated
    assert config.get_geo_config('setting1') == 'value1'
    assert config.get_geo_config('setting2') == 42
    assert config.get_geo_config('setting3') == {'nested': 'dict'}
    
    # Verify entire config contains all updates
    all_config = config.get_geo_config()
    for key, value in updates.items():
        assert all_config[key] == value

def test_geo_config_update_existing_values():
    """Test that update_geo_config can overwrite existing values."""
    config = GeoConfig()
    
    # Set initial values
    config.set_geo_config('key1', 'original')
    config.set_geo_config('key2', 'unchanged')
    
    # Update with overlapping keys
    updates = {
        'key1': 'updated',
        'key3': 'new'
    }
    config.update_geo_config(updates)
    
    # Verify updates
    assert config.get_geo_config('key1') == 'updated'
    assert config.get_geo_config('key2') == 'unchanged'
    assert config.get_geo_config('key3') == 'new'


def test_geo_config_substitute_country_name_ignores_punctuation():
    config = GeoConfig(_default_geo_config_path())

    assert config.substitute_country_name('U.S.A.') == ('USA', True)
    assert config.substitute_country_name('U.K.') == ('United Kingdom', True)
    assert config.substitute_country_name('U-S-A') == ('USA', True)


def test_geo_config_get_place_and_countrycode_ignores_punctuation():
    config = GeoConfig(_default_geo_config_path())

    place, country_code, country_name, found = config.get_place_and_countrycode('Boston, U.S.A.')
    assert found is True
    assert country_code == 'US'
    assert country_name == 'USA'
    assert place.lower().endswith('usa')

    place, country_code, country_name, found = config.get_place_and_countrycode('London, U.K.')
    assert found is True
    assert country_code == 'GB'
    assert country_name == 'United Kingdom'
    assert place.lower().endswith('united kingdom')


def test_geo_config_get_place_and_countrycode_infers_canada_from_province_aliases():
    config = GeoConfig(_default_geo_config_path())

    place, country_code, country_name, found = config.get_place_and_countrycode('Metcalfe Twp., Carleton, Ont.')
    assert found is True
    assert country_code == 'CA'
    assert country_name == 'Canada'
    assert place.lower().endswith('canada')


def test_geo_config_get_place_and_countrycode_infers_country_from_non_canadian_subdivision():
    config = GeoConfig(_default_geo_config_path())

    place, country_code, country_name, found = config.get_place_and_countrycode('Albany, New York')
    assert found is True
    assert country_code == 'US'
    assert country_name == 'United States'
    assert place.lower().endswith('united states')


def test_geo_config_reverse_country_code_lookup_prefers_canonical_names():
    config = GeoConfig(_default_geo_config_path())

    assert config.country_code_to_name_dict['US'] == 'United States'
    assert config.country_code_to_name_dict['GB'] == 'United Kingdom'
    assert config.country_code_to_name_dict['CA'] == 'Canada'

    place, country_code, country_name, found = config.get_place_and_countrycode('Viking, Camrose, Alta.')
    assert found is True
    assert country_code == 'CA'
    assert country_name == 'Canada'
    assert place.lower().endswith('canada')


def test_geo_config_get_place_and_countrycode_strips_leading_noise_tokens():
    config = GeoConfig(_default_geo_config_path())

    place, country_code, country_name, found = config.get_place_and_countrycode('of, GREENBUSH,LEEDS,ONTARIO')
    assert found is True
    assert country_code == 'CA'
    assert country_name == 'Canada'
    assert place == 'greenbush, leeds, canada'

"""
geocode.py - Geocoding utilities for GEDCOM mapping.

Handles geocoding, country/continent lookup, and caching of location results.
Loads fallback continent mappings from geo_config.yaml.

Author: @colin0brass
"""

import time
import logging
import random
import re
from pathlib import Path
from typing import Optional, Tuple, Dict

from numpy import place
import pycountry
import pycountry_convert as pc
import requests
import yaml  # Ensure PyYAML is installed
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable
from geopy.adapters import AdapterHTTPError

from .geocache import GeoCache
from .geo_config import GeoConfig
from .app_hooks import AppHooks

from .location import Location
from .addressbook import FuzzyAddressBook
from .geocache import GeoCache

# Re-use higher-level logger (inherits configuration from main script)
logger = logging.getLogger(__name__)

GEOCODEUSERAGENT = "gedcom_geocoder"

def load_yaml_config(path: Path) -> dict:
    """
    Load YAML configuration from the given path.

    Args:
        path (Path): Path to the YAML file.

    Returns:
        dict: Parsed YAML configuration or empty dict if not found/error.
    """
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        logger.warning(f"Could not load geo_config.yaml: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading geo_config.yaml: {e}")
    return {}

class Geocode:
    """
    Handles geocoding logic, cache management, and country/continent lookups for addresses.

    Attributes:
        default_country (str): Default country for geocoding.
        always_geocode (bool): If True, always geocode and ignore cache.
        cache_only (bool): If True, only use cache and do not perform live geocoding.
        location_cache_file (str): Path to cache file.
        geo_cache (GeoCache): Geocoded location cache manager.
        geolocator (Nominatim): Geopy Nominatim geocoder instance.
        geo_config (GeoConfig): Geographic configuration instance.
        app_hooks (Optional[AppHooks]): Optional application hooks for progress reporting.
        _last_geocode_time (float): Timestamp of the last geocode request.
    """

    __slots__ = [
        'default_country', 'always_geocode', 'cache_only', 'location_cache_file', 'additional_countries_codes_dict_to_add',
        'additional_countries_to_add', 'country_substitutions', 'geo_cache',
        'geolocator', 'geo_config', 'app_hooks', '_last_geocode_time'
    ]
    geocode_sleep_interval = 1  # Delay due to Nominatim request limit

    def __init__(
        self,
        cache_file: str,
        default_country: Optional[str] = None,
        always_geocode: bool = False,
        cache_only: Optional[bool] = False,
        alt_place_file_path: Optional[Path] = None,
        geo_config_path: Optional[Path] = None,
        file_geo_cache_path: Optional[Path] = None,
        app_hooks: Optional['AppHooks'] = None
    ):
        """
        Initialize the Geocode object, loading country info and cache.

        Args:
            cache_file (str): Path to cache file.
            default_country (str, optional): Default country for geocoding.
            always_geocode (bool): Ignore cache if True.
            alt_place_file_path (Optional[Path]): Alternative place names file path.
            geo_config_path (Optional[Path]): Path to geocode.yaml configuration file.
            file_geo_cache_path (Optional[Path]): Path to per-file geo cache.
        """
        self.default_country = default_country
        self.always_geocode = always_geocode
        self.cache_only = cache_only
        self.location_cache_file = cache_file

        self.geo_cache = GeoCache(cache_file, always_geocode, alt_place_file_path, file_geo_cache_path)
        self.geolocator = Nominatim(user_agent="gedcom_geocoder")
        self.geo_config = GeoConfig(geo_config_path)

        self.app_hooks = app_hooks

        self._last_geocode_time = 0.0  # Timestamp of last geocode request

    def save_geo_cache(self) -> None:
        """
        Save address cache to disk if applicable.
        """
        if self.geo_cache.location_cache_file:
            self.geo_cache.save_geo_cache()

    def geocode_address(self, address: str, country_code: str, country_name: str, found_country: bool = False, address_depth: int = 0) -> Optional[Location]:
        """
        Geocode an address string and return a Location object.

        Args:
            address (str): Address string.
            country_code (str): Country code.
            country_name (str): Country name.
            found_country (bool): Whether country was found.
            address_depth (int): Recursion depth for less precise geocoding.

        Returns:
            Optional[Location]: Location object or None.
        """
        location = None

        if not address or self.cache_only:
            return None

        max_retries = 3
        geo_location = None
        backoff_base = 0.5
        for attempt in range(1, max_retries + 1):
            # refresh last request timestamp each iteration
            last_ts = getattr(self, "_last_geocode_time", 0.0)
            now = time.time()
            to_wait = self.geocode_sleep_interval - (now - last_ts)
            if to_wait > 0:
                time.sleep(to_wait)
            try:
                self._last_geocode_time = time.time()
                ccodes = country_code if (country_code and country_code.lower() != 'none') else None
                logger.debug(f"Geocodeing {address} country={ccodes} (attempt {attempt}/{max_retries})")
                geo_location = self.geolocator.geocode(
                    address, country_codes=ccodes, timeout=10,
                    addressdetails=True, exactly_one=True
                )

                # If geopy returned None (HTTP 200 but no match), do not retry — it's not a transient error.
                if geo_location is None:
                    logger.debug("No geocoding result for %r (not retrying)", place)
                    break
                break  # Successful geocode, exit retry loop
            except (GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable, AdapterHTTPError, requests.RequestException) as e:
                # Determine HTTP status when available and treat 5xx as transient (retryable) errors
                status = getattr(e, 'status', None)
                if status and 500 <= status < 600:
                    logger.error(f"Transient geocoding error for {address} (HTTP {status}): {e}")
                else:
                    logger.error(f"Non-retryable geocoding error for {address}: {e}")
                    break  # Non-retryable error, exit loop
                
            except Exception as e:
                logger.error(f"Unexpected error geocoding {address} (attempt {attempt}/{max_retries}): {e}")

            # exponential backoff with small jitter before next attempt
            if attempt < max_retries:
                sleep_time = backoff_base * (2 ** (attempt - 1)) + random.uniform(0.0, 0.2)
                logger.info(f"Retrying geocode for {address} (attempt {attempt+2}/{max_retries}) after {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error(f"Giving up on geocoding {address} after {max_retries} attempts.")
                geo_location = None

        if geo_location:
            if country_name is None and 'country' in geo_location.raw.get('address', {}):
                country_name = geo_location.raw['address']['country']
                if 'country_code' in geo_location.raw.get('address', {}):
                    country_code = geo_location.raw['address']['country_code'].upper()
                    found_country = True
            continent = self.geo_config.get_continent_for_country_code(country_code)
            country_code = country_code.upper() if country_code else None
            location = Location(
                used=1,
                latitude=geo_location.latitude,
                longitude=geo_location.longitude,
                country_code=country_code,
                country_name=country_name,
                continent=continent,
                found_country=found_country,
                address=geo_location.address
            )

        if location is None and address_depth < 3:
            logger.info(f"Retrying geocode for {address} with less precision")
            parts = address.split(',')
            if len(parts) > 1:
                less_precise_address = ','.join(parts[1:]).strip()
                location = self.geocode_address(less_precise_address, country_code, country_name, found_country, address_depth + 1)

        return location

    def separate_cached_locations(self, address_book: FuzzyAddressBook) -> Tuple[FuzzyAddressBook, FuzzyAddressBook]:
        """
        Separate addresses into cached and non-cached address books.

        Args:
            address_book (FuzzyAddressBook): Address book containing full addresses.

        Returns:
            Tuple[FuzzyAddressBook, FuzzyAddressBook]: (cached_places, non_cached_places)
        """
        cached_places = FuzzyAddressBook()
        non_cached_places = FuzzyAddressBook()
        for place, data in address_book.addresses().items():
            place_lower = place.lower()
            if not self.always_geocode and (place_lower in self.geo_cache.geo_cache):
                cached_places.add_address(place, data)
            else:
                non_cached_places.add_address(place, data)
        return (cached_places, non_cached_places)

    def lookup_location(self, place: str) -> Optional[Location]:
        """
        Lookup a place in the cache or geocode it if not found.

        Args:
            place (str): Place string.

        Returns:
            Optional[Location]: Location object or None.
        """
        found_in_cache = False
        found_country = False
        location = None

        if not place:
            return None

        use_place_name = place
        cache_entry = None
        if not self.always_geocode:
            use_place_name, cache_entry = self.geo_cache.lookup_geo_cache_entry(place)

        if cache_entry and cache_entry.get("no_result"):
            logger.info(f"Place '{place}' marked as no_result in cache; skipping geocoding.")
            return None
        
        (place_with_country, country_code, country_name, found_country) = self.geo_config.get_place_and_countrycode(use_place_name)

        if cache_entry and not self.always_geocode:
            if cache_entry.get('latitude') and cache_entry.get('longitude'):
                found_in_cache = True
                location = Location.from_dict(cache_entry)
                if cache_entry.get('found_country', False) == False or cache_entry.get('country_name', '') == '':
                    # Not sure this is needed
                    if cache_entry.get('found_country', False):
                        logger.info(f"Found country in cache for {use_place_name}, but it was not marked as found.")
                        location.found_country = True
                        location.country_code = country_code.upper()
                        location.country_name = country_name
                        location.continent = self.geo_config.get_continent_for_country_code(country_code)
                        self.geo_cache.add_geo_cache_entry(place, location)
                    else:
                        logger.info(f"Unable to add country from geo cache lookup for {use_place_name}")
                if not location.found_country:
                    logger.info(f"Country not found in cache for {use_place_name}")

        if not found_in_cache:
            location = self.geocode_address(place_with_country, country_code, country_name, found_country, address_depth=0)
            if location is not None:
                location.address = place
                self.geo_cache.add_geo_cache_entry(place, location)
                logger.info(f"Geocoded {place} to {location.latlon}")
            else: # record negative cache so we avoid re-trying repeatedly
                self.geo_cache.add_no_result_entry(place)
                logger.info(f"Geocoding couldn't find {place}, so marked as no_result to reduce fruitless attempts.")

        if location:
            continent = location.continent
            if not continent or continent.strip().lower() in ('', 'none'):
                location.continent = self.geo_config.get_continent_for_country_code(location.country_code)

        return location

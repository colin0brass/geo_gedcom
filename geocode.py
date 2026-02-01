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

import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable
from geopy.adapters import AdapterHTTPError

from .geocache import GeoCache
from .geo_config import GeoConfig
from .app_hooks import AppHooks

from .location import Location
from .lat_lon import LatLon
from .addressbook import AddressBook
from .geocache import GeoCache

# Re-use higher-level logger (inherits configuration from main script)
logger = logging.getLogger(__name__)


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
        'default_country', 'always_geocode', 'cache_only', 'geo_config', 'location_cache_file', 'additional_countries_codes_dict_to_add',
        'additional_countries_to_add', 'country_substitutions', 'geo_cache',
        'geolocator', 'geo_config', 'app_hooks', '_last_geocode_time',
        'num_geocoded', 'num_from_cache', 'num_from_cache_no_location_result',
        'max_retries', 'retry_delay', 'backoff_base', 'geocode_timeout', 'days_between_retrying_failed_lookups',
        'get_continent_for_country_code', 'get_place_and_countrycode'
    ]
    
    # Class constants
    HTTP_SERVER_ERROR_MIN = 500  # Start of HTTP 5xx server error range (transient/retryable)
    HTTP_SERVER_ERROR_MAX = 600  # End of HTTP 5xx server error range (exclusive)

    def __init__(
        self,
        cache_file: str,
        geo_config: GeoConfig,
        alt_place_file_path: Optional[Path] = None,
        file_geo_cache_path: Optional[Path] = None,
        app_hooks: Optional['AppHooks'] = None
    ):
        """
        Initialize the Geocode object, loading country info and cache.

        Args:
            cache_file (str): Path to cache file.
            alt_place_file_path (Optional[Path]): Alternative place names file path.
            file_geo_cache_path (Optional[Path]): Path to per-file geo cache.
        """
        self.location_cache_file = cache_file

        geocode_settings = geo_config.get_geo_config('geocode_settings')
        self.always_geocode = geo_config.get_geo_config('always_geocode', False)
        self.cache_only = geo_config.get_geo_config('cache_only', False)
        self.default_country = geocode_settings.get('default_country', '')
        # self.additional_countries_codes_dict_to_add = geo_config.get_geo_config('additional_countries_codes_dict_to_add') or {}
        self.max_retries = geocode_settings.get('max_retries', 3)
        self.retry_delay = geocode_settings.get('rate_limit_seconds', 1.0)
        self.backoff_base = geocode_settings.get('backoff_base', 0.5)
        self.geocode_timeout = geocode_settings.get('timeout', 10.0)
        self.days_between_retrying_failed_lookups = geocode_settings.get('days_between_retrying_failed_lookups', 7)
        self.get_continent_for_country_code = geo_config.get_continent_for_country_code
        self.get_place_and_countrycode = geo_config.get_place_and_countrycode

        self.geo_cache = GeoCache(cache_file, self.always_geocode, alt_place_file_path, file_geo_cache_path,
                                  self.days_between_retrying_failed_lookups)
        user_agent = geocode_settings.get('user_agent', "gedcom_geocoder")
        self.geolocator = Nominatim(user_agent=user_agent)

        self.app_hooks = app_hooks

        self._last_geocode_time = 0.0  # Timestamp of last geocode request

        self.num_geocoded = 0
        self.num_from_cache = 0
        self.num_from_cache_no_location_result = 0

    def save_geo_cache(self) -> None:
        """
        Save address cache to disk if applicable.
        """
        if self.geo_cache.location_cache_file:
            self.geo_cache.save_geo_cache()

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limiting between geocoding requests."""
        last_ts = getattr(self, "_last_geocode_time", 0.0)
        now = time.time()
        to_wait = self.retry_delay - (now - last_ts)
        if to_wait > 0:
            time.sleep(to_wait)

    def _perform_geocode_request(self, address: str, country_code: str) -> Optional[any]:
        """
        Perform a single geocoding request.

        Args:
            address: The address to geocode.
            country_code: The country code to use for filtering.

        Returns:
            The geocoding result or None if no match found.
        """
        self._last_geocode_time = time.time()
        ccodes = country_code if (country_code and country_code.lower() != 'none') else None
        return self.geolocator.geocode(
            address, country_codes=ccodes, timeout=self.geocode_timeout,
            addressdetails=True, exactly_one=True,
            language="en"
        )

    def _infer_country_from_result(self, geo_location, country_code: str, country_name: str, found_country: bool) -> Tuple[str, str, bool]:
        """
        Infer country information from geocoding result if not already known.

        Args:
            geo_location: The geocoding result object.
            country_code: Current country code.
            country_name: Current country name.
            found_country: Whether country was already found.

        Returns:
            Tuple of (country_code, country_name, found_country).
        """
        if not country_name or country_name.lower() == 'none':
            if 'country' in geo_location.raw.get('address', {}):
                country_name = geo_location.raw['address']['country']
                country_code = geo_location.raw['address'].get('country_code', '').upper()
                found_country = True
        return country_code, country_name, found_country

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable (transient) or not.

        Args:
            error: The exception that occurred.

        Returns:
            True if the error is retryable, False otherwise.
        """
        status = getattr(error, 'status', None)
        return status is not None and self.HTTP_SERVER_ERROR_MIN <= status < self.HTTP_SERVER_ERROR_MAX

    def _backoff_sleep(self, attempt: int, address: str) -> None:
        """
        Perform exponential backoff sleep before retry.

        Args:
            attempt: Current attempt number.
            address: The address being geocoded (for logging).
        """
        sleep_time = self.retry_delay * (2 ** (attempt - 1)) + random.uniform(0.0, self.backoff_base)
        logger.info(f"Retrying geocode for {address} (attempt {attempt+2}/{self.max_retries}) after {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)

    def _create_location_from_result(self, geo_location, country_code: str, country_name: str, found_country: bool) -> Location:
        """
        Create a Location object from a successful geocoding result.

        Args:
            geo_location: The geocoding result object.
            country_code: Country code.
            country_name: Country name.
            found_country: Whether country was found.

        Returns:
            Location object with geocoding results.
        """
        continent = self.get_continent_for_country_code(country_code)
        return Location(
            used=1,
            latlon=LatLon(geo_location.latitude, geo_location.longitude),
            country_code=country_code,
            country_name=country_name,
            continent=continent,
            found_country=found_country,
            address=geo_location.address
        )

    def _retry_with_less_precision(self, address: str, country_code: str, country_name: str, 
                                   found_country: bool, address_depth: int) -> Optional[Location]:
        """
        Retry geocoding with less precise address (removing leftmost component).

        Args:
            address: The original address.
            country_code: Country code.
            country_name: Country name.
            found_country: Whether country was found.
            address_depth: Current recursion depth.

        Returns:
            Location object or None.
        """
        if address_depth >= 3:
            return None
            
        logger.info(f"Retrying geocode for {address} with less precision")
        parts = address.split(',')
        if len(parts) > 1:
            less_precise_address = ','.join(parts[1:]).strip()
            return self.geocode_address(less_precise_address, country_code, country_name, 
                                       found_country, address_depth + 1)
        return None

    def geocode_address(self, address: str, country_code: str, country_name: str, 
                       found_country: bool = False, address_depth: int = 0) -> Optional[Location]:
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
        if not address or self.cache_only:
            return None

        geo_location = None
        for attempt in range(1, self.max_retries + 1):
            self._wait_for_rate_limit()
            
            try:
                logger.debug(f"Geocoding {address} (attempt {attempt}/{self.max_retries})")
                geo_location = self._perform_geocode_request(address, country_code)

                if geo_location is None:
                    logger.debug("No geocoding result for %r (not retrying)", address)
                else:
                    country_code, country_name, found_country = self._infer_country_from_result(
                        geo_location, country_code, country_name, found_country)
                break  # Successful geocode, exit retry loop
                
            except (GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable, 
                   AdapterHTTPError, requests.RequestException) as e:
                if self._is_retryable_error(e):
                    logger.error(f"Transient geocoding error for {address} (HTTP {getattr(e, 'status', None)}): {e}")
                else:
                    logger.error(f"Non-retryable geocoding error for {address}: {e}")
                    break  # Non-retryable error, exit loop
                    
            except Exception as e:
                logger.error(f"Unexpected error geocoding {address} (attempt {attempt}/{self.max_retries}): {e}")

            # Handle retry backoff
            if attempt < self.max_retries:
                self._backoff_sleep(attempt, address)
            else:
                logger.error(f"Giving up on geocoding {address} after {self.max_retries} attempts.")
                geo_location = None

        # Create location from successful result
        location = None
        if geo_location:
            location = self._create_location_from_result(geo_location, country_code, country_name, found_country)

        # Try with less precision if unsuccessful
        if location is None:
            location = self._retry_with_less_precision(address, country_code, country_name, 
                                                      found_country, address_depth)

        return location

    def separate_cached_locations(self, address_book: AddressBook) -> Tuple[AddressBook, AddressBook]:
        """
        Separate addresses into cached and non-cached address books.

        Args:
            address_book (AddressBook): Address book containing full addresses.

        Returns:
            Tuple[AddressBook, AddressBook]: (cached_places, non_cached_places)
        """
        fuzz = address_book.fuzz
        cached_places = AddressBook(fuzz=fuzz)
        non_cached_places = AddressBook(fuzz=fuzz)
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

        if cache_entry and cache_entry.no_result:
            self.num_from_cache_no_location_result += 1
            return None
        
        (place_with_country, country_code, country_name, found_country) = self.get_place_and_countrycode(use_place_name)

        if cache_entry and not self.always_geocode:
            self.num_from_cache += 1
            if cache_entry.latitude and cache_entry.longitude:
                found_in_cache = True
                location = Location.from_dict(cache_entry)
                if (not cache_entry.found_country) or (cache_entry.country_name == ''):
                    # Not sure this is needed
                    if cache_entry.found_country:
                        logger.debug(f"Found country in cache for {use_place_name}, but it was not marked as found.")
                        location.found_country = True
                        location.country_code = country_code.upper()
                        location.country_name = country_name
                        location.continent = self.get_continent_for_country_code(country_code)
                        self.geo_cache.add_geo_cache_entry(place, location)
                    else:
                        logger.debug(f"Unable to add country from geo cache lookup for {use_place_name}")
                if not location.found_country:
                    logger.debug(f"Country not found in cache for {use_place_name}")

        if not found_in_cache and not self.cache_only:
            self.num_geocoded += 1
            location = self.geocode_address(place_with_country, country_code, country_name, found_country, address_depth=0)
            if location is not None:
                location.address = place
                self.geo_cache.add_geo_cache_entry(place, location)
                logger.debug(f"Geocoded {place} to {location.latlon}")
            else: # record negative cache so we avoid re-trying repeatedly
                self.geo_cache.add_no_result_entry(place)
                logger.debug(f"Geocoding couldn't find {place}, so marked as no_result to reduce fruitless attempts.")

        if location:
            continent = location.continent
            if not continent or continent.strip().lower() in ('', 'none'):
                location.continent = self.get_continent_for_country_code(location.country_code)

        return location

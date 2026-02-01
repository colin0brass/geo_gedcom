"""
geocache.py - Geocoded location cache utilities for GEDCOM mapping.

Handles reading and saving geocoded location cache as CSV.

Author: @colin0brass
"""

import os
import csv
import logging
from pathlib import Path
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field

from geo_gedcom.location import Location
from geo_gedcom.lat_lon import LatLon

logger = logging.getLogger(__name__)


@dataclass
class GeoCacheEntry:
    """
    Represents a single geocoded location cache entry.
    """
    address: str
    alt_addr: str = ''
    latitude: str = ''
    longitude: str = ''
    country_code: str = ''
    country_name: str = ''
    continent: str = ''
    found_country: bool = False
    no_result: bool = False
    timestamp: float = 0.0
    used: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> 'GeoCacheEntry':
        """
        Create a GeoCacheEntry from a dictionary, converting types as needed.

        Args:
            d (dict): Dictionary with entry data.
        Returns:
            GeoCacheEntry: The constructed entry.
        """
        found_country = d.get('found_country', False)
        if isinstance(found_country, str):
            found_country = found_country.lower() in ('true', '1')
        else:
            found_country = bool(found_country)
        no_result = d.get('no_result', False)
        if isinstance(no_result, str):
            no_result = no_result.lower() in ('true', '1')
        else:
            no_result = bool(no_result)
        timestamp = d.get('timestamp', 0.0)
        try:
            if not timestamp or timestamp == '':
                timestamp = 0.0
            else:
                timestamp = float(timestamp)
        except (TypeError, ValueError):
            timestamp = 0.0
        used = d.get('used', 0)
        try:
            used = int(used)
        except (TypeError, ValueError):
            used = 0
        return cls(
            address=d.get('address', ''),
            alt_addr=d.get('alt_addr', ''),
            latitude=d.get('latitude', ''),
            longitude=d.get('longitude', ''),
            country_code=d.get('country_code', ''),
            country_name=d.get('country_name', ''),
            continent=d.get('continent', ''),
            found_country=found_country,
            no_result=no_result,
            timestamp=timestamp,
            used=used
        )

    def as_dict(self) -> dict:
        """
        Convert the GeoCacheEntry to a dictionary suitable for CSV serialization.

        Returns:
            dict: Dictionary representation of the entry.
        """
        d = asdict(self)
        # CSV expects 'True'/'False' strings for found_country and no_result
        d['found_country'] = 'True' if self.found_country else 'False'
        d['no_result'] = 'True' if self.no_result else 'False'
        d['timestamp'] = str(self.timestamp)
        d['used'] = str(self.used)
        return d


    def __getattr__(self, name):
        """
        Allow safe attribute access for GeoCacheEntry, returning None for missing attributes.
        """
        if name in self.__dataclass_fields__:
            return self.__dict__.get(name)
        return None

    @classmethod
    def from_location(cls, address: str, location: 'Location') -> 'GeoCacheEntry':
        """
        Create a GeoCacheEntry from an address and a Location object.

        Args:
            address (str): The address string.
            location (Location): The geocoded location object.
        Returns:
            GeoCacheEntry: The constructed entry.
        """
        return cls(
            address=address,
            alt_addr=getattr(location, 'alt_addr', ''),
            latitude=getattr(location.latlon, 'lat', ''),
            longitude=getattr(location.latlon, 'lon', ''),
            country_code=getattr(location, 'country_code', ''),
            country_name=getattr(location, 'country_name', ''),
            continent=getattr(location, 'continent', ''),
            found_country=bool(getattr(location, 'found_country', False)),
            no_result=False,
            timestamp=time.time(),
            used=1
        )


@dataclass
class GeoCacheAltAddrEntry:
    """
    Represents a single alternative address cache entry.
    """
    alt_addr: str = '',
    count: int = 0,
    address: str = ''

    @classmethod
    def from_dict(cls, d: dict) -> 'GeoCacheAltAddrEntry':
        """
        Create a GeoCacheAltAddrEntry from a dictionary.

        Args:
            d (dict): Dictionary with entry data.
        Returns:
            GeoCacheAltAddrEntry: The constructed entry.
        """
        count = d.get('count', 0)
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 0
        return cls(
            alt_addr=d.get('alt_addr', ''),
            count=count,
            address=d.get('associated_address', '')
        )
    
    @classmethod
    def as_dict(cls, entry: 'GeoCacheAltAddrEntry') -> dict:
        """
        Convert the GeoCacheAltAddrEntry to a dictionary suitable for CSV serialization.

        Returns:
            dict: Dictionary representation of the entry.
        """
        d = asdict(entry)
        d['count'] = str(entry.count)
        return d


class GeoCache:
    """
    Manages reading and writing of geocoded location cache data for GEDCOM mapping.

    Loads cached geocoding results from a CSV file, normalizes fields,
    and provides methods to save updated cache data back to disk. Ensures
    consistent handling of fields such as 'found_country' and tracks usage counts.

    Attributes:
        location_cache_file (str): Path to the cache CSV file.
        always_geocode (bool): If True, ignore cache and always geocode.
        geo_cache (Dict[str, dict]): Dictionary mapping place names to cached geocode data.
        alt_addr_cache (Dict[str, dict]): Dictionary mapping place names to alternative address data.
        time_between_retrying_failed_geocodes (int): Time in seconds to wait before retrying failed geocodes.
    """

    def __init__(
        self,
        cache_file: str,
        always_geocode: bool,
        alt_addr_file: Optional[Path] = None,
        file_geo_cache_path: Optional[Path] = None,
        days_between_retrying_failed_geocodes: int = 7
    ):
        """
        Initialize the GeoCache object.

        Args:
            cache_file (str): Path to the cache CSV file.
            always_geocode (bool): If True, ignore cache and always geocode.
            alt_addr_file (Optional[Path]): Path to alternative address file.
            file_geo_cache_path (Optional[Path]): Path to per-file geo cache.
            days_between_retrying_failed_geocodes: int = 7
        """
        self.location_cache_file = cache_file
        self.always_geocode = always_geocode
        self.geo_cache: Dict[str, GeoCacheEntry] = {}
        self.alt_addr_cache: Dict[str, GeoCacheAltAddrEntry] = {}
        self.file_geo_cache_path = file_geo_cache_path

        self.time_between_retrying_failed_geocodes = days_between_retrying_failed_geocodes * 24 * 3600  # One day

        self.geo_cache = self.read_geo_cache(self.location_cache_file)
        self.geo_cache.update(self.read_geo_cache(self.file_geo_cache_path))
        
        if alt_addr_file:
            self.read_alt_addr_file(alt_addr_file)
            self.add_alt_addr_to_cache()
    
    def read_geo_cache(self, location_file_path: Optional[Path]) -> Dict[str, GeoCacheEntry]:
        """
        Read geocoded location cache from the CSV file.

        Loads cached geocoding results into self.geo_cache.
        Normalizes the 'found_country' field to boolean.
        If always_geocode is True or the cache file does not exist, skips loading.
        """
        geo_cache: Dict[str, GeoCacheEntry] = {}
        if self.always_geocode:
            logger.info('Configured to ignore cache')
            return geo_cache
        if not location_file_path or not os.path.exists(location_file_path):
            logger.info(f'No location cache file found: {location_file_path}')
            return geo_cache
        try:
            with open(location_file_path, newline='', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f, dialect='excel')
                for line in csv_reader:
                    key = line.get('address', '').lower()
                    entry = GeoCacheEntry.from_dict(line)
                    geo_cache[key] = entry
        except FileNotFoundError as e:
            logger.warning(f'Location cache file not found: {e}')
        except csv.Error as e:
            logger.error(f'CSV error reading location cache file {self.location_cache_file}: {e}')
        except Exception as e:
            logger.error(f'Error reading location cache file {self.location_cache_file}: {e}')

        return geo_cache

    def save_geo_cache(self) -> None:
        """
        Save geocoded location cache to the CSV file.

        Writes all cached geocoding results from self.geo_cache to disk.
        Ensures the 'found_country' field is saved as a 'True' or 'False' string.
        """
        if not self.geo_cache:
            logger.info('No geocoded location cache to save')
            return
        try:
            # Collect all fieldnames from all cache entries
            all_fieldnames = set()
            for entry in self.geo_cache.values():
                all_fieldnames.update(entry.as_dict().keys())
            fieldnames = list(all_fieldnames)
            if not fieldnames:
                logger.info('Geocoded location cache is empty, nothing to save.')
                return
            with open(self.location_cache_file, 'w', newline='', encoding='utf-8') as f:
                csv_writer = csv.DictWriter(f, fieldnames=fieldnames, dialect='excel')
                csv_writer.writeheader()
                for entry in self.geo_cache.values():
                    csv_writer.writerow(entry.as_dict())
            logger.info(f'Saved geocoded location cache to: {self.location_cache_file}')
        except FileNotFoundError as e:
            logger.warning(f'Location cache file not found for saving: {e}')
        except csv.Error as e:
            logger.error(f'CSV error saving geocoded location cache: {e}')
        except Exception as e:
            logger.error(f'Error saving geocoded location cache: {e}')

    def read_alt_addr_file(self, alt_addr_file: Optional[Path]) -> None:
        """
        Read alternative address names from a CSV file.

        Args:
            alt_addr_file (Optional[Path]): Path to alternative address file.
        """
        if not alt_addr_file or not os.path.exists(alt_addr_file):
            logger.info(f'No alternative address file found: {alt_addr_file}')
            return
        try:
            with open(alt_addr_file, newline='', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f, dialect='excel')
                for line in csv_reader:
                    key = line.get('address', '').lower()
                    entry = GeoCacheAltAddrEntry.from_dict(line)
                    self.alt_addr_cache[key] = entry
        except FileNotFoundError as e:
            logger.warning(f'Alternative address file not found: {e}')
        except csv.Error as e:
            logger.error(f'CSV error reading alternative address file {alt_addr_file}: {e}')
        except Exception as e:
            logger.error(f'Error reading alternative address file {alt_addr_file}: {e}')

    def _should_retry_failed_geocode(self, cache_entry: GeoCacheEntry) -> bool:
        """
        Determine if a failed geocode entry should be retried based on timestamp.
        """
        last_attempt = getattr(cache_entry, 'timestamp', 0)
        try:
            last_attempt = float(last_attempt)
        except (TypeError, ValueError):
            last_attempt = 0
        return time.time() - last_attempt > self.time_between_retrying_failed_geocodes

    def _update_cache_entry_with_alt_addr(self, cache_entry: GeoCacheEntry, alt_addr_entry: GeoCacheAltAddrEntry) -> None:
        """
        Update a cache entry with alternative address data.
        """
        cache_entry.alt_addr = alt_addr_entry.alt_addr
        if alt_addr_entry.latitude and alt_addr_entry.longitude:
            cache_entry.latitude = alt_addr_entry.latitude
            cache_entry.longitude = alt_addr_entry.longitude

    def lookup_geo_cache_entry(self, address: str) -> Tuple[str, Optional[dict]]:
        """
        Look up an address in the geocoded cache or alternative address names.

        Args:
            address (str): The address string to look up.

        Returns:
            Tuple[str, Optional[dict]]: (possibly substituted address, cached geocode data if found, else None)
        """
        address_lower = address.lower()
        alt_addr_entry: Optional[GeoCacheAltAddrEntry] = self.alt_addr_cache.get(address_lower)
        alt_addr_name: Optional[str] = alt_addr_entry.alt_addr if alt_addr_entry else None

        use_addr_name = alt_addr_name if alt_addr_name else address

        cache_entry: Optional[GeoCacheEntry] = self.geo_cache.get(address_lower)
        if cache_entry:
            if cache_entry.no_result:
                if self._should_retry_failed_geocode(cache_entry):
                    logger.info(f"Retrying geocode for previously failed address: {address}")
                    del self.geo_cache[address_lower]
                    return use_addr_name, None
                return use_addr_name, cache_entry

            if alt_addr_entry and alt_addr_name:
                logger.info(f"Adding alternative address name for cache entry: {address} : {alt_addr_name}")
                self._update_cache_entry_with_alt_addr(cache_entry, alt_addr_entry)
            return use_addr_name, cache_entry

        return use_addr_name, None

    def add_no_result_entry(self, address: str) -> None:
        """
        Add a 'no result' entry to the geocoded location cache.

        Args:
            address (str): The address string.
        """
        entry = GeoCacheEntry(
            address=address,
            no_result=True,
            timestamp=time.time()
        )
        self.geo_cache[address.lower()] = entry

    def add_geo_cache_entry(self, address: str, location: Location) -> None:
        """
        Add a new entry to the geocoded location cache.

        Args:
            address (str): The address string.
            location (Location): The geocoded location object.
        """
        entry = GeoCacheEntry.from_location(address, location)
        self.geo_cache[address.lower()] = entry

    def add_alt_addr_to_cache(self) -> None:
        """
        Add alternative address names to the cache.

        Iterates through alt_addr_cache and adds entries to geo_cache if not already present.
        """
        for address, data in self.alt_addr_cache.items():
            if address.lower() not in self.geo_cache:
                logger.info(f"Adding alternative address to cache: {address} : {data.get('alt_addr')}")
                # Use the real Location class for temporary location creation
                lat = data.get('latitude', '')
                lon = data.get('longitude', '')
                latlon = LatLon(lat, lon)
                temp_location = Location(
                    address=address,
                    alt_addr=data.get('alt_addr', ''),
                    latlon=latlon,
                    country_code=data.get('country_code', ''),
                    country_name=data.get('country_name', ''),
                    continent=data.get('continent', ''),
                    found_country=False
                )
                entry = GeoCacheEntry.from_location(address, temp_location)
                entry.no_result = False
                entry.timestamp = time.time()
                entry.used = 0
                self.geo_cache[address.lower()] = entry

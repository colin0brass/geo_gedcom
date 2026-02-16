import logging

from pathlib import Path
from typing import Dict, List, Optional

from .gedcom import Gedcom
from .geocode import Geocode
from .geo_config import GeoConfig
from .location import Location
from .addressbook import AddressBook
from .life_event import LifeEvent
from .lat_lon import LatLon
from .app_hooks import AppHooks

logger = logging.getLogger(__name__)

class GeolocatedGedcom(Gedcom):
    """
    GEDCOM handler with geolocation support.

    Attributes:
        geocoder (Geocode): Geocode instance.
        address_book (AddressBook): Address book of places.
    """
    __slots__ = [
        'geocoder',
        'address_book',
        'geo_config',
        'alt_place_file_path',
        'geo_config_path',
        'file_geo_cache_path',
        'app_hooks',
        'cache_only'
    ]
    geolocate_all_logger_interval = 20

    def __init__(
            self,
            gedcom_file: Path,
            location_cache_file: Path,
            alt_place_file_path: Optional[Path] = None,
            geo_config_path: Optional[Path] = None,
            geo_config_updates: Optional[Dict] = None,
            file_geo_cache_path: Optional[Path] = None,
            app_hooks: Optional['AppHooks'] = None,
            fuzz: bool = False,
            enable_enrichment: bool = True,
            enable_statistics: bool = True
    ):
        """
        Initialize GeolocatedGedcom.

        Args:
            gedcom_file (str): Path to GEDCOM file.
            location_cache_file (str): Location cache file.
            always_geocode (Optional[bool]): Whether to always geocode.
            cache_only (Optional[bool]): Whether to only use cache for geocoding.
            alt_place_file_path (Optional[Path]): Path to alternative place file.
            geo_config_path (Optional[Path]): Path to geographic configuration file.
            file_geo_cache_path (Optional[Path]): Path to per-file geo cache.
            geo_config_updates: Optional[Dict] = None
            app_hooks (Optional[AppHooks]): Application hooks for progress reporting.
            fuzz (bool): Whether to use fuzzy matching for place names.
            enable_enrichment (bool): Whether to run enrichment processing.
            enable_statistics (bool): Whether to run statistics processing.
        """
        super().__init__(gedcom_file=gedcom_file, app_hooks=app_hooks, enable_enrichment=enable_enrichment, enable_statistics=enable_statistics)

        # Skip remaining initialization if parsing was stopped
        if self.gedcom_parser._stop_was_requested:
            logger.info("Skipping address book and geolocation due to stop request during parsing")
            self.address_book = None
            self.geo_config = None
            self.geocoder = None
            return

        self.address_book = AddressBook(fuzz=fuzz)
        self.app_hooks = app_hooks

        self.geo_config = GeoConfig(geo_config_path, geo_config_updates)
        self._report_step("Initializing geocoder ...", target=0, reset_counter=True)
        self.geocoder = Geocode(
            cache_file=location_cache_file,
            geo_config=self.geo_config,
            alt_place_file_path=alt_place_file_path if alt_place_file_path else None,
            file_geo_cache_path=file_geo_cache_path,
            app_hooks=app_hooks
        )
        cache_only = self.geo_config.get_geo_config('cache_only', False)

        # Set target for address book reading based on parsed people scanned
        total_records = self.gedcom_parser.num_people
        self._report_step("Reading address book ...", target=total_records, reset_counter=True)
        self.read_full_address_book()

        # Skip geolocation if address book reading was stopped
        if not self._stop_requested():
            self._report_step("Geolocating addresses", target=0, reset_counter=True)
            self.geolocate_all(cache_only)

        self._report_step("Locating People", target=self.gedcom_parser.num_people, reset_counter=True)
        self.geolocate_people()

        # Final completion message
        self._report_step("Geolocation complete", target=0, reset_counter=True)
        self._update_key_value(key="parsed", value=True)

    def _report_step(self, info: str = "", target: Optional[int] = None, reset_counter: bool = False, plus_step: int = 0) -> None:
        """
        Report a step via app hooks if available. (Private method)

        Args:
            info (str): Information message.
            target (int): Target count for progress.
            reset_counter (bool): Whether to reset the counter.
            plus_step (int): Incremental step count.
        """
        if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
            self.app_hooks.report_step(info=info, target=target, reset_counter=reset_counter, plus_step=plus_step)
        else:
            logger.info(info)

    def _stop_requested(self, logger_stop_message: str = "Stop requested by user") -> bool:
        """
        Check if stop has been requested via app hooks. (Private method)

        Returns:
            bool: True if stop requested, False otherwise.
        """
        if self.app_hooks and callable(getattr(self.app_hooks, "stop_requested", None)):
            if self.app_hooks.stop_requested():
                if logger_stop_message:
                    logger.info(logger_stop_message)
                return True
        return False

    def _update_key_value(self, key: str, value) -> None:
        """
        Update a key-value pair via app hooks. (Private method)

        Args:
            key (str): Key to update.
            value: Value to set.
        """
        if self.app_hooks and callable(getattr(self.app_hooks, "update_key_value", None)):
            self.app_hooks.update_key_value(key=key, value=value)

    def save_location_cache(self) -> None:
        """
        Save the location cache to the specified file.
        """
        self.geocoder.save_geo_cache()

    def _process_address_book_with_progress(
        self,
        address_book: AddressBook,
        progress_message: str,
        force_none_location: bool = False,
        save_cache_interval: int = 0
    ) -> bool:
        """
        Process an address book with progress reporting and stop checking.

        Args:
            address_book: The address book to process.
            progress_message: Message to display during progress.
            force_none_location: If True, always add None as location regardless of lookup result.
            save_cache_interval: If > 0, save cache every N items (0 = no periodic saves).

        Returns:
            bool: True if stopped by user, False if completed normally.
        """
        num_places = address_book.len()
        self._report_step(progress_message, target=num_places, reset_counter=True)

        for idx, (place, data) in enumerate(address_book.addresses().items(), 1):
            use_place = data.alt_addr if data.alt_addr else place
            location = self.geocoder.lookup_location(use_place)

            # Add to address book with appropriate location
            if force_none_location:
                self.address_book.add_address(place, None)
            else:
                self.address_book.add_address(place, location)

            # Check for stop request
            if self._stop_requested(logger_stop_message="Geolocation process stopped by user."):
                return True

            # Report progress at intervals
            if idx % self.geolocate_all_logger_interval == 0 or idx == num_places:
                self._report_step(plus_step=self.geolocate_all_logger_interval, info=progress_message)

            # Save cache periodically if requested
            if save_cache_interval > 0 and idx % save_cache_interval == 0:
                self.save_location_cache()

        return False

    def geolocate_all(self, cache_only: bool = False) -> None:
        """
        Geolocate all places in the GEDCOM file.
        """
        self._report_step("Loading cached places ...", target=0, reset_counter=True)
        cached_places_with_geolocation, cached_places_without_geolocation, non_cached_places = self.geocoder.separate_cached_locations(self.address_book)
        num_cached_places_with_geolocation = cached_places_with_geolocation.len()
        num_cached_places_without_geolocation = cached_places_without_geolocation.len()
        num_non_cached_places = non_cached_places.len()
        logger.info(f"Found {num_cached_places_with_geolocation} cached places with geolocation, {num_cached_places_without_geolocation} cached places without geolocation, {num_non_cached_places} non-cached places.")

        # Process cached places with geolocation
        if self._process_address_book_with_progress(
            cached_places_with_geolocation,
            "Matching cached places with geolocation ..."
        ):
            return

        # Process cached places without geolocation
        # Temporarily enable cache_only to prevent retrying failed geocodes
        original_cache_only = self.geocoder.cache_only
        self.geocoder.cache_only = True
        try:
            if self._process_address_book_with_progress(
                cached_places_without_geolocation,
                "Processing cached places without geolocation ...",
                force_none_location=True
            ):
                return
        finally:
            self.geocoder.cache_only = original_cache_only

        # Process non-cached places if not in cache-only mode
        if cache_only:
            logger.info("Cache-only mode enabled; skipping geolocation of non-cached places.")
        else:
            self._process_address_book_with_progress(
                non_cached_places,
                "Geolocating uncached places ...",
                save_cache_interval=100
            )
            self.save_location_cache()  # Final save

        logger.info(f"Geolocation of all {self.address_book.len()} places completed. ({self.geocoder.num_geocoded} geocoded, {self.geocoder.num_from_cache} from cache, {self.geocoder.num_from_cache_no_location_result} from cache with no location result.)")

    def read_full_address_book(self) -> None:
        """
        Get all places from the GEDCOM file.
        """
        super().read_full_address_list()
        num_addresses = len(self.address_list)

        # Reset counter for second phase: populating address book
        self._report_step(f"Populating address book with {num_addresses} places", target=num_addresses, reset_counter=True)

        num_addresses_existed = 0
        num_addresses_didnt_exist = 0
        for idx, place in enumerate(self.address_list):
            if self._stop_requested(logger_stop_message="Reading address book process stopped by user."):
                break
            if idx > 0 and idx % 100 == 0:
                self._report_step(plus_step=100)
            if not self.address_book.get_address(place):
                location = None
                self.address_book.add_address(place, location)
                num_addresses_didnt_exist += 1
                logger.debug(f"Added address to address book: `{place}`")
            else:
                num_addresses_existed += 1

        # Report final progress
        remainder = len(self.address_list) % 100
        if remainder > 0:
            self._report_step(plus_step=remainder)

        logger.info(f"Address book read completed: {num_addresses} addresses, {num_addresses_existed} already existed, {num_addresses_didnt_exist} added.")
        logger.info(f"Address book stats: {self.address_book.address_existed} addresses existed during lookups, {self.address_book.address_didnt_exist} did not exist.")

    def geolocate_people(self) -> None:
        """
        Geolocate all life events for all people using the iter_life_events generator.
        """
        exit_requested: bool = False
        total_people = len(self.people)
        for idx, person in enumerate(self.people.values(), 1):
            # Report progress every 100 people or at the end
            if idx % 100 == 0 or idx == total_people:
                person_name = getattr(person, 'name', '-Unknown-')
                self._report_step(info=f"Locating people: {person_name}", plus_step=100 if idx % 100 == 0 else idx % 100)

            for event in person.iter_life_events():
                self.__geolocate_event(event)
                if self._stop_requested(logger_stop_message="Locating people process stopped by user."):
                    exit_requested = True
                    break
            if exit_requested:
                break

        if not exit_requested:
            logger.info(f"Geolocated events for {total_people} people.")

    def __geolocate_event(self, event: LifeEvent) -> LifeEvent:
        """
        Geolocate a single event. If no location is found, event.location remains None.

        Args:
            event (LifeEvent): The event to geolocate.

        Returns:
            LifeEvent: The event with updated location and latlon if found.
        """
        record = getattr(event, 'record', None)
        if record:
            place_tag = record.sub_tag('PLAC')
            if place_tag:
                map_tag = place_tag.sub_tag('MAP')
                if place_tag.value:
                    location = self.geocoder.lookup_location(place_tag.value)
                    event.location = location if location else Location(address=place_tag.value)
                if map_tag:
                    lat = map_tag.sub_tag('LATI')
                    lon = map_tag.sub_tag('LONG')
                    if lat and lon:
                        latlon = LatLon(lat.value, lon.value)
                        event.location.latlon = latlon if latlon.is_valid() else None
                    else:
                        event.location.latlon = None
            else:
                logger.debug(f"No place tag found for event in record {record}")
        else:
            logger.debug("No record found for event")
        return event

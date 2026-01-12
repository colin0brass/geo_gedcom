import logging

from pathlib import Path
from typing import Dict, List, Optional

from .gedcom import Gedcom
from .geocode import Geocode
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
            default_country: Optional[str] = None,
            always_geocode: Optional[bool] = False,
            cache_only: Optional[bool] = False,
            alt_place_file_path: Optional[Path] = None,
            geo_config_path: Optional[Path] = None,
            file_geo_cache_path: Optional[Path] = None,
            app_hooks: Optional['AppHooks'] = None,
            fuzz: bool = False
    ):
        """
        Initialize GeolocatedGedcom.

        Args:
            gedcom_file (str): Path to GEDCOM file.
            location_cache_file (str): Location cache file.
            default_country (Optional[str]): Default country for geocoding.
            always_geocode (Optional[bool]): Whether to always geocode.
            cache_only (Optional[bool]): Whether to only use cache for geocoding.
            alt_place_file_path (Optional[Path]): Path to alternative place file.
            geo_config_path (Optional[Path]): Path to geographic configuration file.
            file_geo_cache_path (Optional[Path]): Path to per-file geo cache.
        """
        super().__init__(gedcom_file=gedcom_file, app_hooks=app_hooks)

        self.address_book = AddressBook(fuzz=fuzz)
        self.app_hooks = app_hooks

        if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
            self.app_hooks.report_step("Initializing geocoder ...")
        self.geocoder = Geocode(
            cache_file=location_cache_file,
            default_country=default_country,
            always_geocode=always_geocode,
            cache_only=cache_only,
            alt_place_file_path=alt_place_file_path if alt_place_file_path else None,
            geo_config_path=geo_config_path if geo_config_path else None,
            file_geo_cache_path=file_geo_cache_path,
            app_hooks=app_hooks
        )
        self.cache_only = cache_only

        if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
            self.app_hooks.report_step("Reading address book ...", target=0) # reset_counter=True

        self.read_full_address_book()

        if not cache_only:
            if self.app_hooks and callable(getattr(self.app_hooks, "stop_requested", None)):
                if self.app_hooks.stop_requested():
                    logger.info("Geolocation process stopped by user.")
                    return
            if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
                self.app_hooks.report_step("Geolocating addresses ...") # reset_counter=True

            self.geolocate_all()

        if self.app_hooks and callable(getattr(self.app_hooks, "stop_requested", None)):
            if self.app_hooks.stop_requested():
                logger.info("Geolocation process stopped by user.")
                return
        if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
            self.app_hooks.report_step("Parsed people ...", target=0, reset_counter=True)
       
        self.parse_people()

        if self.app_hooks and callable(getattr(self.app_hooks, "update_key_value", None)):
            self.app_hooks.update_key_value(key="parsed", value=True)

    def save_location_cache(self) -> None:
        """
        Save the location cache to the specified file.
        """
        self.geocoder.save_geo_cache()

    def geolocate_all(self) -> None:
        """
        Geolocate all places in the GEDCOM file.
        """
        if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
            self.app_hooks.report_step("Loading Cached ...")
        cached_places, non_cached_places = self.geocoder.separate_cached_locations(self.address_book)
        num_cached_places = cached_places.len()
        num_non_cached_places = non_cached_places.len()
        logger.info(f"Found {num_cached_places} cached places, {num_non_cached_places} non-cached places.")

        logger.info(f"Matching {num_cached_places} cached places...")
        if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
            self.app_hooks.report_step(f"Matching cached places ...", target=num_cached_places, reset_counter=True)
        for idx, (place, data) in enumerate(cached_places.addresses().items(), 1):
            use_place = data.alt_addr if data.alt_addr else place
            location = self.geocoder.lookup_location(use_place)
            # Address could be in address book already
            self.address_book.add_address(place, location)      
            if self.app_hooks and callable(getattr(self.app_hooks, "stop_requested", None)):
                if self.app_hooks.stop_requested():
                    logger.info("Geolocation process stopped by user.")
                    break
            if idx % self.geolocate_all_logger_interval == 0 or idx == num_cached_places:
                if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
                    self.app_hooks.report_step(plus_step=self.geolocate_all_logger_interval)
        num_non_cached_places = non_cached_places.len()

        logger.info(f"Geolocating {num_non_cached_places} non-cached places...")
        if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
            self.app_hooks.report_step(f"Geolocating uncached places ...", target=num_non_cached_places, reset_counter=True)
        for idx, (place, data) in enumerate(non_cached_places.addresses().items(), 1):
            use_place = data.alt_addr if data.alt_addr else place
            location = self.geocoder.lookup_location(use_place)
            self.address_book.add_address(place, location)
            if self.app_hooks and callable(getattr(self.app_hooks, "stop_requested", None)):
                if self.app_hooks.stop_requested():
                    logger.info("Geolocation process stopped by user.")
                    break
            if idx % self.geolocate_all_logger_interval == 0 or idx == num_non_cached_places:
                logger.info(f"Geolocated {idx} of {num_non_cached_places} non-cached places ...")
                if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
                    self.app_hooks.report_step(plus_step=self.geolocate_all_logger_interval, info=f"Geolocated {idx} of {num_non_cached_places}")
            # Save the cache every 100 locations
            if idx % 100 == 0:
                self.save_location_cache()
        self.save_location_cache() # Final save

        logger.info(f"Geolocation of all {self.address_book.len()} places completed. ({self.geocoder.num_geocoded} geocoded, {self.geocoder.num_from_cache} from cache, {self.geocoder.num_from_cache_no_location_result} from cache with no location result.)")

    def parse_people(self) -> None:
        """
        Parse and geolocate all people in the GEDCOM file.
        """
        super()._parse_people()
        if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
            self.app_hooks.report_step("Locating People", target=self.gedcom_parser.num_people, reset_counter=True)
        if not self.cache_only:
            self.geolocate_people()

    def read_full_address_book(self) -> None:
        """
        Get all places from the GEDCOM file.
        """
        super().read_full_address_list()
        num_addresses = len(self.address_list)
        num_addresses_existed = 0
        num_addresses_didnt_exist = 0
        for idx, place in enumerate(self.address_list):
            if self.app_hooks and callable(getattr(self.app_hooks, "stop_requested", None)):
                if self.app_hooks.stop_requested():
                    logger.info("Reading address book process stopped by user.")
                    break
            if idx % 100 == 0:
                logger.info(f"Read {idx} of {num_addresses} addresses ...")
                if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
                    self.app_hooks.report_step(plus_step=100, info=f"Read {idx} of {num_addresses}")
            if not self.address_book.get_address(place):
                location = None
                self.address_book.add_address(place, location)
                num_addresses_didnt_exist += 1
                logger.info(f"Added address to address book: `{place}`")
            else:
                num_addresses_existed += 1
        logger.info(f"Address book read completed: {num_addresses} addresses, {num_addresses_existed} already existed, {num_addresses_didnt_exist} added.")
        logger.info(f"Address book stats: {self.address_book.address_existed} addresses existed during lookups, {self.address_book.address_didnt_exist} did not exist.")

    def geolocate_people(self) -> None:
        """
        Geolocate all life events for all people using the iter_life_events generator.
        """
        for person in self.people.values():
            if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
                self.app_hooks.report_step(info=f"Reviewing {getattr(person, 'name', '-Unknown-')}")
            for event in person.iter_life_events():
                self.__geolocate_event(event)

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
                logger.info(f"No place tag found for event in record {record}")
        else:
            logger.warning("No record found for event")
        return event

"""Geo-GEDCOM package: GEDCOM parsing, geocoding, and genealogical data processing.

This package provides comprehensive GEDCOM file parsing, geocoding (address-to-GPS),
address enrichment, genealogical relationship tracking, and data quality analysis.

Core components:
    - GedcomParser: Parse GEDCOM files into structured data
    - Gedcom: High-level GEDCOM file interface
    - GeolocatedGedcom: GEDCOM with geocoded addresses
    - Person: Individual genealogical record
    - Marriage: Marital relationship record
    - GedcomDate: Genealogical date representation
    - LatLon: Geographic coordinate
    - Location: Geographic location with address
    - Geocode: Address-to-GPS resolution
    - GeoCache: Geocoding result caching
    - AddressBook: Centralized address management
    - GenerationTracker: Family generation tracking

Submodules:
    - enrichment: Data quality enrichment and inference
    - app_hooks: Callback protocol for customization
    - geo_config: Geographic configuration

Usage:
    >>> from geo_gedcom import GedcomParser, GeolocatedGedcom
    >>> parser = GedcomParser()
    >>> people = parser.parse('family.ged')
    >>> geogedcom = GeolocatedGedcom(people)
    >>> geogedcom.add_geocoding_callback(...)
"""

from .addressbook import AddressBook
from .gedcom import Gedcom, GenerationTracker
from .gedcom_date import GedcomDate
from .gedcom_parser import GedcomParser
from .geocache import GeoCache
from .geocode import Geocode
from .geolocated_gedcom import GeolocatedGedcom
from .lat_lon import LatLon
from .location import Location
from .person import LifeEvent, Partner, Person
from .marriage import Marriage
from .app_hooks import AppHooks
from .geo_config import GeoConfig

__all__ = [
    # Core GEDCOM
    "GedcomParser",
    "Gedcom",
    "GeolocatedGedcom",
    # Person/relationship data
    "Person",
    "Marriage",
    "Partner",
    "LifeEvent",
    # Geographic data
    "LatLon",
    "Location",
    "GedcomDate",
    # Geocoding
    "Geocode",
    "GeoCache",
    "AddressBook",
    # Utilities
    "GenerationTracker",
    "AppHooks",
    "GeoConfig",
]
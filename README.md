# geo_gedcom Python Module

This module provides core functionality for parsing, filtering, geocoding, and exporting GEDCOM genealogical data. It is designed for modularity, maintainability, and robust handling of genealogical records, including people, places, events, and photos.

## Requirements
- Python 3.8 or newer
- [ged4py](https://pypi.org/project/ged4py/)
- [rapidfuzz](https://pypi.org/project/rapidfuzz/)
- [unidecode](https://pypi.org/project/Unidecode/)
- [pycountry](https://pypi.org/project/pycountry/)
- [pycountry-convert](https://pypi.org/project/pycountry-convert/)
- [bpemb](https://pypi.org/project/bpemb/)
- [pytest](https://pypi.org/project/pytest/) (for testing)
- [pytest-cov](https://pypi.org/project/pytest-cov/) (for test coverage)

## Installation

Clone the repository and install dependencies:

```sh
git clone https://github.com/YOUR_ORG/gedcom-to-visualmap.git
cd gedcom-to-visualmap/gedcom-to-map/geo_gedcom
pip install -r requirements.txt
```

Or install directly with pip:

```sh
pip install ged4py rapidfuzz unidecode pycountry pycountry-convert bpemb pyyaml
```

## Key Features
- **GEDCOM Parsing:** Efficiently parses GEDCOM files and extracts individuals, families, events, and places.
- **Filtering:** Supports advanced ancestor/descendant filtering by generation.
- **Photo Management:** Handles photo file extraction and management from GEDCOM records.
- **Geocoding Integration:** Integrates with geolocation utilities for mapping places and events.
- **Export Utilities:** Allows exporting filtered data and associated photos to new GEDCOM files.
- **Memory Optimization:** Uses `__slots__` in key classes for reduced memory usage.
- **Type Hints & Docstrings:** All major classes and functions are documented and typed for clarity and maintainability.
- **Comprehensive Testing:** Extensive pytest-based test suite for all core modules and models.

## Main Classes & Modules
- `Gedcom`: High-level handler for people and places.
- `GedcomParser`: Utilities for parsing and exporting GEDCOM data.
- `Person`, `LifeEvent`, `Marriage`: Data models for individuals, life events, and marriages.
- `LifeEventSet`: Structured, type-annotated, and robust container for organizing and retrieving life events by type, supporting sorting and flexible event handling.
- `Location`, `LatLon`: Geocoding and location utilities.
- `FuzzyAddressBook`: Place/address management.
- `GedcomDate`: Robust date parsing and normalization.
- `GeoCache`, `Geocode`: Geocoding cache and lookup utilities.
- `geo_config`: Country/continent configuration and mapping.

## Usage Example
```python
from geo_gedcom import Gedcom

gedcom_file = "Tree_2025-12-04.ged"
g = Gedcom(gedcom_file, only_use_photo_tags=False)
filtered, msg = g.filter_generations(
    starting_person_id="@I1@",
    num_ancestor_generations=3,
    num_descendant_generations=2,
    wider_descendants_end_generation=None,
    include_partners=True,
    include_siblings=True
)
print(msg)
g.export_people_with_photos(filtered, "filtered.ged", "output", "photos")
```

## Directory Structure
```
geo_gedcom/
├── __init__.py
├── addressbook.py
├── app_hooks.py
├── gedcom.py
├── gedcom_date.py
├── gedcom_parser.py
├── geo_config.py
├── geocache.py
├── geocode.py
├── geolocated_gedcom.py
├── lat_lon.py
├── life_event.py
├── life_event_set.py
├── location.py
├── marriage.py
├── partner.py
├── person.py
├── requirements.txt
├── README.md
├── samples/
│   ├── bronte.ged
│   ├── bronte_alt.csv
│   ├── bronte_cache.csv
│   ├── pres2020.ged
│   ├── pres2020_alt.csv
│   ├── pres2020_cache.csv
│   ├── royal92.ged
│   ├── royal92_alt.csv
│   ├── royal92_cache.csv
│   ├── shakespeare.ged
│   ├── shakespeare_alt.csv
│   └── shakespeare_cache.csv
├── tests/
│   ├── test_addressbook.py
│   ├── test_gedcom_date.py
│   ├── test_gedcom_parser.py
│   ├── test_geo_config.py
│   ├── test_geo_gedcom_imports.py
│   ├── test_geocache.py
│   ├── test_geocode.py
│   ├── test_geolocated_gedcom.py
│   ├── test_latlon.py
│   ├── test_life_event.py
│   ├── test_location.py
│   ├── test_marriage.py
│   ├── test_partner.py
│   └── test_person.py
```

## Authors
- @colin0brass
- @lmallez
- @D-jeffrey

## License
See the main repository LICENSE.txt for details.

## Extending & Contributing
Contributions and extensions are welcome! Please see the main repository for guidelines and open an issue or pull request for major changes.

## Testing

To run the test suite:
```sh
pytest
```
All core modules and models are covered by pytest-based tests. See the `tests/` directory for details.

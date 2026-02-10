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
- **Data Enrichment:** Infers missing events, detects data quality issues, and applies domain knowledge (see `enrichment/` module).
- **Statistics Collection:** Aggregates demographic, event, and geographic statistics from genealogical datasets (see `statistics/` module).
- **Export Utilities:** Allows exporting filtered data and associated photos to new GEDCOM files.
- **Memory Optimization:** Uses `__slots__` in key classes for reduced memory usage.
- **Type Hints & Docstrings:** All major classes and functions are documented and typed for clarity and maintainability.
- **Comprehensive Testing:** Extensive pytest-based test suite for all core modules and models.

## Main Classes & Modules

### Core Parsing & Data Models
- `Gedcom`: High-level handler for people and places.
- `GedcomParser`: Utilities for parsing and exporting GEDCOM data.
- `Person`, `LifeEvent`, `Marriage`: Data models for individuals, life events, and marriages.
- `LifeEventSet`: Structured, type-annotated, and robust container for organizing and retrieving life events by type, supporting sorting and flexible event handling.

### Geocoding & Location
- `Location`, `LatLon`: Geocoding and location utilities.
- `FuzzyAddressBook`: Place/address management.
- `GeoCache`, `Geocode`: Geocoding cache and lookup utilities with support for cache-only mode.
  - **Cache-only mode**: When enabled, the geocoder uses only cached results without making network requests. Failed lookup attempts are not retried, and the cache file is not modified, ensuring true read-only behavior.
- `geo_config`: Country/continent configuration and mapping.

### Data Processing
- `GedcomDate`: Robust date parsing and normalization.
- **`enrichment/` module**: Infer missing events, detect data quality issues, apply domain knowledge
  - See [enrichment/README.md](enrichment/README.md) for details
- **`statistics/` module**: Collect aggregate statistics from genealogical data
  - See [statistics/README.md](statistics/README.md) for details

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
├── enrichment/           # Data enrichment module
│   ├── __init__.py
│   ├── README.md
│   ├── enrichment.py
│   ├── pipeline.py
│   ├── config.py
│   ├── config.yaml
│   ├── model.py
│   ├── date_utils.py
│   ├── rules/
│   └── tests/
├── statistics/           # Statistics collection module
│   ├── __init__.py
│   ├── README.md
│   ├── statistics.py
│   ├── pipeline.py
│   ├── model.py
│   ├── base.py
│   ├── collectors/
│   └── tests/
├── samples/
│   ├── bronte.ged
│   ├── pres2020.ged
│   ├── royal92.ged
│   └── shakespeare.ged
└── tests/
    ├── test_addressbook.py
    ├── test_gedcom_date.py
    ├── test_gedcom_parser.py
    └── ...g.py
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

"""
geo_config.py - Geographic configuration and country/continent utilities for GEDCOM mapping.

Provides GeoConfig for loading continent mappings, country substitutions, and related
geographic settings from a YAML configuration file.
"""

import yaml
import logging
import re
from pathlib import Path
from typing import Optional, Tuple

import pycountry
import pycountry_convert as pc

logger = logging.getLogger(__name__)

LEADING_PLACE_NOISE_TOKENS = {"of"}


def _normalize_country_lookup_key(country_name: str) -> str:
    """Normalize country lookup text by removing punctuation and collapsing spaces."""
    cleaned = re.sub(r"[^\w\s]", "", country_name or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def _clean_place_components(place: str) -> list[str]:
    """Split a place into cleaned comma-separated components and drop leading noise."""
    parts = [part.strip() for part in (place or "").split(',') if part and part.strip()]
    while parts and _normalize_country_lookup_key(parts[0]) in LEADING_PLACE_NOISE_TOKENS:
        parts.pop(0)
    return parts


class GeoConfig:
    """
    GeoConfig manages loading of geographic configuration data from a YAML file.

    Loads continent mappings, country substitutions, and other geographic settings
    for use in geocoding and location processing tasks.

    Attributes:
        geo_config_path (Optional[Path]): Path to the configuration YAML file.
        countrynames (List[str]): List of country names.
        countrynames_lower (List[str]): List of country names in lowercase.
        country_name_to_code_dict (Dict[str, str]): Mapping of country names to ISO codes.
        country_code_to_name_dict (Dict[str, str]): Mapping of ISO codes to country names.
        country_code_to_continent_dict (Dict[str, str]): Mapping of ISO codes to continent names.
        country_substitutions_lower (Dict[str, str]): Lowercase-keyed substitution mapping.
        countrynames_dict_lower (Dict[str, str]): Lowercase-keyed country name mapping.
        default_country (str): Default country name.
        fallback_continent_map (Dict[str, str]): Fallback continent mapping for country codes.
    """

    def __init__(self, geo_config_path: Optional[Path] = None, geo_config_updates: Optional[dict] = None) -> None:
        """Initialize GeoConfig with country data and optional configuration.

        Args:
            geo_config_path: Optional path to the configuration YAML file.
            
        Raises:
            TypeError: If geo_config_path is not a Path or None.
        """
        if geo_config_path is not None and not isinstance(geo_config_path, Path):
            raise TypeError("geo_config_path must be a pathlib.Path or None")
        self.__geo_config_path: Optional[Path] = geo_config_path
        self.countrynames: list[str] = []
        self.countrynames_lower: list[str] = []
        self.country_name_to_code_dict: dict = {}
        self.country_code_to_continent_dict: dict = {}
        self.country_code_to_name_dict: dict = {}
        self.country_substitutions_lower: dict = {}
        self.countrynames_dict_lower: dict = {}  # Initialize to empty dict
        self.subdivision_country_lookup: dict = {}
        self.default_country = None
        self.fallback_continent_map = {}

        self.__geo_config = {}
        if geo_config_path:
            self.load_geo_config()
        if geo_config_updates:
            self.update_geo_config(geo_config_updates)
        self.initialize_country_data()

    def load_geo_config(self) -> None:
        """
        Load geographic configuration from the YAML file.

        Populates country substitutions, default country, continent mappings,
        and additional country codes from the config file.
        """
        if self.__geo_config_path and self.__geo_config_path.exists():
            try:
                with open(self.__geo_config_path, 'r', encoding='utf-8') as f:
                    self.__geo_config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load geo config from {self.__geo_config_path}: {e}")
                self.__geo_config = {}
        else:
            self.__geo_config = {}

    def get_geo_config(self, key: Optional[str] = None, default=None):
        """
        Get the geo configuration dictionary or a specific key value.

        Args:
            key: Optional key to retrieve a specific value. If None, returns entire config.
            default: Default value to return if key is not found (only used when key is specified).

        Returns:
            The entire config dict if key is None, otherwise the value for the specified key.
            Returns default if key is not found.
        """
        if not hasattr(self, '_GeoConfig__geo_config'):
            return {} if key is None else default
        
        if key is None:
            return self.__geo_config.copy()
        return self.__geo_config.get(key, default)

    def set_geo_config(self, key: str, value) -> None:
        """
        Set a value in the geo configuration dictionary.

        Args:
            key: The configuration key to set.
            value: The value to set for the key.
        """
        if not hasattr(self, '_GeoConfig__geo_config'):
            self.__geo_config = {}
        self.__geo_config[key] = value

    def update_geo_config(self, settings_dict: dict) -> None:
        """
        Update multiple values in the geo configuration dictionary from a dict.

        Args:
            settings_dict: Dictionary of key-value pairs to update in the config.
        """
        if not hasattr(self, '_GeoConfig__geo_config'):
            self.__geo_config = {}
        self.__geo_config.update(settings_dict)

    def initialize_country_data(self) -> None:
        """
        Initialize country data structures from the loaded configuration.
        Populates country names, codes, substitutions, and continent mappings.
        """
        country_substitutions = self.__geo_config.get('country_substitutions', {})
        subdivision_country_substitutions = self.__geo_config.get('subdivision_country_substitutions', {})
        self.default_country = self.__geo_config.get('default_country', '')
        additional_countries_codes_dict_to_add = self.__geo_config.get('additional_countries_codes_dict_to_add', {})
        self.fallback_continent_map = self.__geo_config.get('fallback_continent_map', {})

        additional_countries_to_add = list(additional_countries_codes_dict_to_add.keys())
        self.countrynames = [country.name for country in pycountry.countries]
        self.countrynames.extend(additional_countries_to_add)

        self.countrynames_lower = [name.lower() for name in self.countrynames]

        self.country_name_to_code_dict = {country.name: country.alpha_2 for country in pycountry.countries}
        self.country_name_to_code_dict.update(additional_countries_codes_dict_to_add)

        # Keep canonical display names from pycountry and only fill in extra codes that do not
        # already exist (for synthetic entries like EU or WI).
        self.country_code_to_name_dict = {country.alpha_2: country.name for country in pycountry.countries}
        for country_name, country_code in additional_countries_codes_dict_to_add.items():
            self.country_code_to_name_dict.setdefault(country_code, country_name)
        self.country_code_to_continent_dict = {code: self.country_code_to_name_dict.get(code) for code in self.country_code_to_name_dict.keys()}

        self.country_substitutions_lower = {
            _normalize_country_lookup_key(k): v for k, v in country_substitutions.items()
        }
        self.countrynames_dict_lower = {
            _normalize_country_lookup_key(name): name for name in self.countrynames
        }
        self.subdivision_country_lookup, self.subdivision_display_lookup = self._build_subdivision_lookups(
            subdivision_country_substitutions
        )

    def _build_subdivision_lookups(self, subdivision_country_substitutions: dict) -> tuple[dict[str, str], dict[str, str]]:
        """Build normalized subdivision lookups for country inference and display labels.

        Uses pycountry ISO-3166-2 subdivisions where the normalized subdivision name maps
        uniquely to a single country, then overlays any explicit config aliases for local
        shorthand such as genealogical abbreviations.
        """
        subdivision_to_country_codes: dict[str, set[str]] = {}

        for subdivision in pycountry.subdivisions:
            normalized_name = _normalize_country_lookup_key(subdivision.name)
            if not normalized_name:
                continue
            subdivision_to_country_codes.setdefault(normalized_name, set()).add(subdivision.country_code)

        country_lookup: dict[str, str] = {}
        display_lookup: dict[str, str] = {}
        for normalized_name, country_codes in subdivision_to_country_codes.items():
            if len(country_codes) != 1:
                continue
            country_code = next(iter(country_codes))
            country_name = self.country_code_to_name_dict.get(country_code)
            if country_name:
                country_lookup[normalized_name] = country_name

        for subdivision in pycountry.subdivisions:
            normalized_name = _normalize_country_lookup_key(subdivision.name)
            if normalized_name in country_lookup:
                display_lookup[normalized_name] = subdivision.name

        for alias, country_name in subdivision_country_substitutions.items():
            canonical_country = self._canonicalize_country_reference(country_name)
            if canonical_country:
                normalized_alias = _normalize_country_lookup_key(alias)
                country_lookup[normalized_alias] = canonical_country
                display_lookup[normalized_alias] = self._resolve_subdivision_display_name(alias, canonical_country)

        return country_lookup, display_lookup

    def _resolve_subdivision_display_name(self, subdivision_name: str, canonical_country: str) -> str:
        """Resolve a subdivision alias to a stable display label when possible."""
        normalized_name = _normalize_country_lookup_key(subdivision_name)
        if not normalized_name:
            return subdivision_name

        subdivision_matches = []
        country_code = self.get_country_code(canonical_country)
        for subdivision in pycountry.subdivisions:
            if country_code and subdivision.country_code != country_code:
                continue

            normalized_subdivision_name = _normalize_country_lookup_key(subdivision.name)
            if (
                normalized_subdivision_name == normalized_name
                or normalized_subdivision_name.startswith(normalized_name)
            ):
                subdivision_matches.append(subdivision.name)

        if len(subdivision_matches) == 1:
            return subdivision_matches[0]

        return subdivision_name.strip()

    def _canonicalize_country_reference(self, country_name: str) -> str:
        """Resolve a configured country reference to its canonical display name."""
        substituted_name, _ = self.substitute_country_name(country_name)
        canonical_name, found = self.get_country_name(substituted_name)
        return canonical_name if found else substituted_name

    def infer_country_from_place_component(self, place_component: str) -> Optional[str]:
        """Infer a country from a trailing subdivision/state/province component."""
        return self.subdivision_country_lookup.get(_normalize_country_lookup_key(place_component))

    def canonicalize_subdivision_name(self, subdivision_name: str) -> str:
        """Return a stable display label for a subdivision/state/province name."""
        if not subdivision_name:
            return ""
        return self.subdivision_display_lookup.get(
            _normalize_country_lookup_key(subdivision_name),
            subdivision_name.strip(),
        )

    def get_continent_for_country_code(self, country_code: str) -> Optional[str]:
        """
        Get the continent name for a given ISO alpha-2 country code.

        Args:
            country_code (str): The ISO alpha-2 country code.

        Returns:
            Optional[str]: The continent name if found, else None.
        """
        if not country_code or country_code.strip().lower() in ('', 'none'):
            return None
        try:
            continent_code = pc.country_alpha2_to_continent_code(country_code)
            continent_name = pc.convert_continent_code_to_continent_name(continent_code)
            return continent_name
        except KeyError:
            # If pycountry_convert does not have the mapping, check fallback map
            return self.fallback_continent_map.get(country_code)
        except Exception as e:
            logger.error(f"Error getting continent for country code '{country_code}': {e}")
            return None
        
    def substitute_country_name(self, country_name: str) -> Tuple[str, bool]:
        """
        Substitute a country name using the config's substitution mapping.

        Args:
            country_name (str): The original country name.

        Returns:
            Tuple[str, bool]: (Substituted country name, True if substituted, False otherwise)
        """
        if not country_name:
            return country_name, False
        substituted = self.country_substitutions_lower.get(_normalize_country_lookup_key(country_name))
        if substituted:
            return substituted, True
        return country_name, False
    
    def get_country_name(self, country_name: str) -> Tuple[Optional[str], bool]:
        """
        Get the canonical country name for a given country name.

        Args:
            country_name (str): The country name.

        Returns:
            Tuple[Optional[str], bool]: (Canonical country name if found, True if found, else None and False)
        """
        normalized_key = _normalize_country_lookup_key(country_name)
        if normalized_key in self.countrynames_dict_lower:
            return self.countrynames_dict_lower[normalized_key], True
        else:
            return None, False
        
    def get_country_code(self, country_name: str) -> Optional[str]:
        """
        Get the ISO alpha-2 country code for a given country name.

        Args:
            country_name (str): The country name.

        Returns:
            Optional[str]: The ISO alpha-2 country code if found, else None.
        """
        return self.country_name_to_code_dict.get(country_name)
    
    def get_place_and_countrycode(self, place: str) -> Tuple[str, str, str, bool]:
        """
        Given a place string, return (place, country_code, country_name, found).

        Args:
            place (str): Place string.

        Returns:
            Tuple[str, str, str, bool]: (place, country_code, country_name, found)
        """
        found = False
        country_name = ''

        parts = _clean_place_components(place)
        place_lower = ', '.join(part.lower() for part in parts)
        last_place_element = parts[-1] if parts else ''

        country_name, found_sub = self.substitute_country_name(last_place_element)
        if found_sub:
            logger.debug(f"Substituting country '{last_place_element}' with '{country_name}' in place '{place}'")
            if parts:
                parts[-1] = country_name
                place_lower = ', '.join(part.lower() for part in parts)
            found = True
        else:
            country_name, found_country = self.get_country_name(last_place_element)
            if found_country:
                found = True

        if not found:
            inferred_country = self.infer_country_from_place_component(last_place_element)
            if inferred_country:
                country_name = inferred_country
                parts[-1] = inferred_country
                place_lower = ', '.join(part.lower() for part in parts)
                found = True

        if not found and self.default_country and self.default_country.lower() != 'none':
            logger.debug(f"Adding default country '{self.default_country}' to place '{place}'")
            place_lower = (place_lower + ', ' if place_lower else '') + self.default_country
            country_name = self.default_country

        country_code = self.get_country_code(country_name) if country_name else 'none'
        
        return (place_lower, country_code, country_name, found)

"""
addressbook.py - AddressBook for geo_gedcom mapping.

Defines the AddressBook class for storing, managing, and fuzzy-matching geocoded addresses and locations.
Supports summary reporting and integration with Location and LatLon classes.

Module: geo_gedcom.addressbook
Author: @colin0brass
Last updated: 2025-11-29
"""

import logging
from typing import Any, Dict, Optional, Union, List
from rapidfuzz import process, fuzz

from .location import Location
from .lat_lon import LatLon

logger = logging.getLogger(__name__)

class AddressBook:
    """
    Stores and manages a collection of geocoded addresses with fuzzy matching support.

    Attributes:
        __addresses (Dict[str, Location]): Internal mapping of address strings to Location objects.
        __alt_addr_to_address_lookup (Dict[str, List[str]]): Maps alt_addr to addresses.
        summary_columns (List[str]): List of columns for summary output.
        fuzz (bool): Whether to use fuzzy matching when adding addresses.
        address_existed (int): Count of addresses that existed in the book during lookups.
        address_didnt_exist (int): Count of addresses that did not exist in the book during lookups.
    """

    def __init__(self, fuzz: bool = False):
        """
        Initialize an empty AddressBook.
        """
        self.__addresses : Dict[str, Location] = {}
        self.__alt_addr_to_address_lookup: Dict[str, List[str]] = {}
        self.summary_columns = [
            'address', 'alt_addr', 'used', 'type', 'class_', 'icon',
            'latitude', 'longitude', 'found_country', 'country_code', 'country_name'
        ]
        self.fuzz: bool = fuzz
        self.address_existed: int = 0
        self.address_didnt_exist: int = 0

        # Find the caller information
        (filename, line_number, function_name, stack)= logger.findCaller(stacklevel=2)
        # Print the caller information
        
        logger.debug(f"Initialized AddressBook : Caller: {function_name} in {filename} at line {line_number}")
        

    def get_summary_row_dict(self, address: str) -> Dict[str, Any]:
        """
        Get a summary dictionary for a given address.

        Args:
            address (str): The address to summarize.

        Returns:
            Dict[str, Any]: Summary dictionary with keys from self.summary_columns.
        """
        location = self.__addresses.get(address)
        if location is None:
            return {}
        row = {col: getattr(location, col, None) for col in self.summary_columns}
        if location.latlon:
            row['latitude'] = location.latlon.lat
            row['longitude'] = location.latlon.lon
        else:
            row['latitude'] = None
            row['longitude'] = None
        return row
    
    def __add_address(self, key: str, location: Location):
        """
        Add a Location object to the address book and update alt_addr lookup.

        Args:
            key (str): Address string.
            location (Location): Location object to add.
        """
        if location is not None:
            self.__addresses[key] = location
            self.__add_alt_addr_to_address_lookup(location.alt_addr, key)

    def add_address(self, address: str, location: Union[Location, None]):
        """
        Add a new address to the address book, using fuzzy matching to find
        the best existing address if there's a close match, and use same alt_addr.

        Args:
            address (str): The address to add.
            location (Location): The location data associated with the address.
        """
        if self.fuzz:
            existing_key = self.fuzzy_lookup_address(address)
        else:
            existing_location =  self.get_address(address) 
            existing_key = address if existing_location is not None else None

        if existing_key is not None:
            # If a similar (or identical) address exists, create or update the entry with the same alt_addr
            existing_location = self.__addresses[existing_key]
            if existing_key == address: # exact match; use existing location and increment usage
                if isinstance(existing_location, Location):
                    location = existing_location.merge(location)
                    location.used = existing_location.used + 1
                if not isinstance(location, Location):
                    location = Location(address=address, used=1)
            # Update the existing entry with the new location data
            self.__add_address(existing_key, location)
        else:
            location = Location(address=address) if location is None else location

            # If no similar address exists, add it as a new entry.
            self.__add_address(address, location)

    def get_address(self, key: str) -> Optional[Location]:
        """
        Retrieve a Location object by address key.

        Args:
            key (str): Address string.

        Returns:
            Optional[Location]: Location object if found, else None.
        """
        return self.__addresses.get(key)

    def __add_alt_addr_to_address_lookup(self, alt_addr: str, address: str):
        """
        Add an address to the alt_addr lookup dictionary.

        Args:
            alt_addr (str): Alternative address string.
            address (str): Address string to associate.
        """
        if alt_addr is not None and alt_addr != '' and alt_addr.lower() != 'none':
            if alt_addr not in self.__alt_addr_to_address_lookup:
                self.__alt_addr_to_address_lookup[alt_addr] = []
            self.__alt_addr_to_address_lookup[alt_addr].append(address)

    def get_address_list_for_alt_addr(self, alt_addr: str) -> List[str]:
        """
        Get a list of addresses associated with a given alt_addr.

        Args:
            alt_addr (str): Alternative address string.

        Returns:
            List[str]: List of associated addresses.
        """
        return self.__alt_addr_to_address_lookup.get(alt_addr, [])

    def addresses(self) -> Dict[str, Location]:
        """
        Returns the addresses in the address book.

        Returns:
            Dict[str, Location]: Dictionary of addresses.
        """
        return self.__addresses
    
    def get_alt_addr_list(self) -> List[str]:
        """
        Returns the list of alternative addresses in the address book.

        Returns:
            List[str]: List of alternative addresses.
        """
        return list(self.__alt_addr_to_address_lookup.keys())

    def get_address_list(self) -> List[str]:
        """
        Returns the list of addresses in the address book.

        Returns:
            List[str]: List of addresses.
        """
        return list(self.__addresses.keys())

    def len(self) -> int:
        """
        Returns the number of addresses in the address book.

        Returns:
            int: Number of addresses.
        """
        return len(self.__addresses)

    def fuzzy_lookup_address(self, address: str, threshold: int = 90) -> Optional[str]:
        """
        Find the best fuzzy match for an address in the address book.

        Args:
            address (str): The address to match.
            threshold (int): Minimum similarity score (0-100) to accept a match.

        Returns:
            Optional[str]: The best matching address key, or None if no good match found.
        """

        # This products a 100% match if the address exists exactly
        match = self.__addresses.get(address)
        if match is not None:
            self.address_existed += 1
            return match.address
        else:
            self.address_didnt_exist += 1
        
        choices = list(self.__addresses.keys())
        if choices:
            match, score, _ = process.extractOne(address, choices, scorer=fuzz.token_sort_ratio)
            if score >= threshold:
                return match
        return None
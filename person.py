"""
person.py - geo_gedcom person and individual modeling for GEDCOM data.

This module provides the Person class and utilities for modeling individuals
in GEDCOM genealogical data. It supports:
    - Parsing person records
    - Extracting and normalizing personal attributes
    - Associating people with life events and relationships

Module: geo_gedcom.person
Authors: @lmallez, @D-jeffrey, @colin0brass
Last updated: 2025-12-06
"""

__all__ = ['Person']

import logging
from typing import Dict, Union, Optional, List

from .lat_lon import LatLon
from .location import Location
from .partner import Partner
from .marriage import Marriage
from .life_event import LifeEvent
from .life_event_set import LifeEventSet

logger = logging.getLogger(__name__)

class Person:
    """
    Represents a person in the GEDCOM file.

    Attributes:
        xref_id (str): GEDCOM cross-reference ID.
        name (Optional[str]): Full name.
        firstname (Optional[str]): First name.
        surname (Optional[str]): Surname.
        maidenname (Optional[str]): Maiden name.
        sex (Optional[str]): Sex ('M', 'F', or None).
        title (Optional[str]): Title.
        event_type_list (List[str]): List of allowed event types.
        allow_new_event_types (bool): Whether to allow new event types.
        father (Person): Father (xref ID or Person).
        mother (Person): Mother (xref ID or Person).
        children (List[str]): List of children xref IDs.
        partners (List[str]): List of partner xref IDs.
        age (Optional[Union[int, str]]): Age or age with cause of death.
        photos_all (List[str]): All photo file paths or URLs.
        photo (Optional[str]): Primary photo file path or URL.
        location (Optional[Location]): Best known location (may be None).
        latlon (LatLon): Latitude/longitude (best known position).
        family_spouse (List[str]): FAMS family IDs (as spouse/partner).
        family_child (List[str]): FAMC family IDs (as child).
    """
    # Age constraints
    max_age: int = 122
    max_mother_age: int = 66
    max_father_age: int = 93
    min_mother_age: int = 11
    min_father_age: int = 12

    __slots__ = ['xref_id',
                 'name', 'firstname', 'surname', 'maidenname',
                 'sex','title',
                 'event_type_list',
                 'allow_new_event_types',
                 '__life_event_set',
                 'father', 'mother', 'children', 'partners', 
                 'age', 'photos_all', 'photo', 
                 'location', 'latlon', 
                 'family_spouse', 'family_child']
    def __init__(self, xref_id : str):
        """
        Initialize a Person instance with all relationship, event, and metadata fields.

        Args:
            xref_id (str): GEDCOM cross-reference ID.
        """
        self.xref_id : str = xref_id

        self.name : Optional[str] = None
        self.firstname : Optional[str] = None
        self.surname : Optional[str] = None
        self.maidenname : Optional[str] = None

        self.sex : Optional[str] = None
        self.title : Optional[str] = None

        self.event_type_list : List[str] = ['birth', 'death', 'marriage', 'baptism', 'residence', 'military', 'arrival', 'departure']
        self.allow_new_event_types : bool = False
        self.__life_event_set : LifeEventSet = LifeEventSet(event_types=self.event_type_list, allow_new_event_types=self.allow_new_event_types)

        self.father : Person = None
        self.mother : Person = None
        
        self.children : List[str] = []
        self.partners : List[str] = []

        self.age : Optional[Union[int, str]] = None           # This can be age number or including the cause of death
        self.photos_all = []         # URL or file path to photos
        self.photo : Optional[str] = None        # URL or file path to primary photo

        self.location = None
        self.latlon : LatLon = None

        self.family_spouse : List[str] = []
        self.family_child : List[str] = []

    def add_events(self, event_type: str, life_events: Union[LifeEvent, List[LifeEvent], Marriage, List[Marriage]]):
        """
        Adds one or more life events to the person based on the event type.

        Args:
            life_events (LifeEvent or List[LifeEvent]): One or more life events to add.
            event_type (str): Type of event ('birth', 'marriage', 'death', 'baptism', 'residence', 'military', 'arrival', 'departure').
        """
        event_type = event_type.lower()
        self.__life_event_set.add_events(event_type, life_events)

    def add_event(self, event_type: str, life_event: Optional[Union[LifeEvent, Marriage]]):
        """
        Adds a single life event to the person based on the event type.

        Args:
            life_event (LifeEvent): A life event to add.
            event_type (str): Type of event ('birth', 'death', 'baptism', 'residence', 'military', 'arrival', 'departure').
        """
        if not isinstance(life_event, (LifeEvent, Marriage, type(None))):
            logger.warning(f"Invalid life event provided: {life_event}")
            return
        self.add_events(event_type, [life_event])

    def get_events(self, event_type: str, date_order: bool = False) -> Union[LifeEvent, List[LifeEvent]]:
        """
        Returns a list of life events for the specified event type.

        Args:
            event_type (str): Type of event ('birth', 'marriage', 'death', 'baptism', 'residence', 'military', 'arrival', 'departure').
        Returns:
            List[LifeEvent]: List of life events of the specified type.
        """
        event_type = event_type.lower()
        return self.__life_event_set.get_events(event_type, date_order=date_order)

    def get_event(self, event_type: str) -> Optional[LifeEvent]:
        """
        Returns the first life event for the specified event type.

        Args:
            event_type (str): Type of event ('birth', 'death', 'baptism', 'residence', 'military', 'arrival', 'departure').
        Returns:
            Optional[LifeEvent]: The first life event of the specified type, or None if not found.
        """
        events = self.get_events(event_type)
        return events[0] if events else None

    def iter_life_events(self):
        """
        Generator that yields all life events for this person.
        Allows external code to iterate and optionally update events (e.g., geolocate).
        Yields:
            LifeEvent or Marriage: Each life event instance for this person.
        """
        for event_type in self.event_type_list:
            events = self.__life_event_set.get_events(event_type)
            for event in events:
                yield event

    def __str__(self) -> str:
        """
        Returns a string representation of the person (xref and name).
        """
        return f"Person(id={self.xref_id}, name={self.name})"

    def __repr__(self) -> str:
        """
        Returns a detailed string representation of the person for debugging.
        """
        return f"[ {self.xref_id} : {self.name} - {self.father} & {self.mother} - {self.latlon} ]"

    def ref_year(self) -> list[str, int]:
        """
        Returns a reference year string for the person.

        Returns:
            str: Reference year string.
        """
        year_num: int = None
        description = 'Unknown'
        birth_event = self.get_event('birth')
        death_event = self.get_event('death')
        if birth_event and birth_event.date:
            year_num = birth_event.date.year_num
            description = f'Born {year_num}' if year_num else 'Born Unknown'
        elif death_event and death_event.date:
            year_num = death_event.date.year_num
            description = f'Died {year_num}' if year_num else 'Died Unknown'
        return description, year_num
    
    def get_best_location_and_type(self) -> tuple[Optional[Location], Optional[str]]:
        """
        Returns the best known location for the person and its type.

        Returns:
            tuple[Optional[Location], Optional[str]]: Best known location and its type.
        """
        best_location: Optional[Location] = None
        location_type: Optional[str] = None
        birth_event = self.get_event('birth')
        death_event = self.get_event('death')
        if birth_event and birth_event.location and birth_event.location.latlon and birth_event.location.latlon.hasLocation():
            best_location = birth_event.location
            location_type = 'Birth'
        elif death_event and death_event.location and death_event.location.latlon and death_event.location.latlon.hasLocation():
            best_location = death_event.location
            location_type = 'Death'
        else:
            # Check other events for a location
            for event_type in self.event_type_list:
                events = self.get_events(event_type)
                for event in events:
                    if isinstance(event, Marriage):
                        event = event.event
                    if event.location and event.location.latlon and event.location.latlon.hasLocation():
                        best_location = event.location
                        location_type = event_type.capitalize()
                        break
                if best_location:
                    break
        return best_location, location_type
    
    def bestlocation(self):
        """
        Returns the best known location for the person as [latlon, description].
        """
        best = ["Unknown", ""]

        best_location, location_type = self.get_best_location_and_type()

        if best_location and best_location.latlon and best_location.latlon.hasLocation():
            best = [
                str(best_location.latlon),
                f"{best_location.address} ({location_type.capitalize()})" if best_location.address else "",
            ]

        return best

    def bestLatLon(self):
        """
        Returns the best known LatLon for the person (birth, then death, else None).
        """
        best = LatLon(None, None)
        
        best_location, location_type = self.get_best_location_and_type()

        if best_location and best_location.latlon:
            best = best_location.latlon
            
        return best

    def _check_birth_death_problems(self, born: Optional[int], died: Optional[int], max_age: int) -> list[str]:
        """
        Check for problems between birth and death years.
        
        Args:
            born (Optional[int]): Birth year.
            died (Optional[int]): Death year.
            max_age (int): Maximum plausible age.
        Returns:
            list[str]: List of problems found.
        """
        problems = []
        if born and died:
            if died < born:
                problems.append("Died before Born")
            if died - born > max_age:
                problems.append(f"Too old {died - born} > {max_age}")
        return problems

    def _check_parent_child_ages(self, people: Dict[str, 'Person'], born: Optional[int], died: Optional[int],
                                 max_mother_age: int, min_mother_age: int,
                                 max_father_age: int, min_father_age: int) -> list[str]:
        """
        Check for age-related problems between parents and children.
        Args:
            people (Dict[str, Person]): Dictionary of people by xref ID.
            born (Optional[int]): Birth year of the parent.
            died (Optional[int]): Death year of the parent.
            max_mother_age (int): Maximum plausible age for mothers.
            min_mother_age (int): Minimum plausible age for mothers.
            max_father_age (int): Maximum plausible age for fathers.
            min_father_age (int): Minimum plausible age for fathers.
        Returns:
            list[str]: List of problems found.
        """
        problems = []
        if not self.children:
            return problems
        for childId in self.children:
            child = people.get(childId)
            birth_event = child.get_event('birth') if child else None
            if not child or not (birth_event and birth_event.date and birth_event.date.year_num):
                continue
            child_birth_year = birth_event.date.year_num
            if born:
                parent_at_age = child_birth_year - born
                if self.sex == "F":
                    if parent_at_age > max_mother_age:
                        problems.append(f"Mother too old {parent_at_age} > {max_mother_age} for {child.name} [{child.xref_id}]")
                    if parent_at_age < min_mother_age:
                        problems.append(f"Mother too young {parent_at_age} < {min_mother_age} for {child.name} [{child.xref_id}]")
                    if died and died < child_birth_year:
                        problems.append(f"Mother after death for {child.name} [{child.xref_id}]")
                elif self.sex == "M":
                    if parent_at_age > max_father_age:
                        problems.append(f"Father too old {parent_at_age} > {max_father_age} for {child.name} [{child.xref_id}]")
                    if parent_at_age < min_father_age:
                        problems.append(f"Father too young {parent_at_age} < {min_father_age} for {child.name} [{child.xref_id}]")
                    if died and died + 1 < child_birth_year:
                        problems.append(f"Father after death for {child.name} [{child.xref_id}]")
                else:
                    if parent_at_age > max(max_father_age, max_mother_age):
                        problems.append(f"Parent too old {parent_at_age} > {max(max_father_age,max_mother_age)} for {child.name} [{child.xref_id}]")
                    if parent_at_age < min(min_mother_age, min_father_age):
                        problems.append(f"Parent too young {parent_at_age} < {min(max_father_age,max_mother_age)} for {child.name} [{child.xref_id}]")
        return problems

    def check_age_problems(self, people: Dict[str, 'Person']) -> list[str]:
        """
        Check for age-related problems in the person's life events.
        Args:
            people (Dict[str, Person]): Dictionary of people by xref ID.
        Returns:
            list[str]: List of problems found.
        """
        birth_event = self.get_event('birth')
        death_event = self.get_event('death')
        born = birth_event.date.year_num if birth_event and birth_event.date and birth_event.date.year_num else None
        died = death_event.date.year_num if death_event and death_event.date and death_event.date.year_num else None

        problems = []
        problems += self._check_birth_death_problems(born, died, self.max_age)
        problems += self._check_parent_child_ages(people, born, died, self.max_mother_age, self.min_mother_age, self.max_father_age, self.min_father_age)
        return problems

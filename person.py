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
import re
from typing import Dict, Union, Optional, List

from ged4py.model import Record, NameRec
from ged4py.date import DateValue
from .lat_lon import LatLon
from .location import Location
from .gedcom_date import GedcomDate
from .partner import Partner
from .marriage import Marriage
from .life_event import LifeEvent

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
        birth (LifeEvent): Birth event.
        death (LifeEvent): Death event.
        baptism (List[LifeEvent]): Baptism events.
        marriages (List[LifeEvent]): Marriage events.
        residences (List[LifeEvent]): Residence events.
        military (List[LifeEvent]): Military service events.
        arrivals (List[LifeEvent]): Arrival events.
        departures (List[LifeEvent]): Departure events.
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
                 'birth', 'death',
                 'baptism', 'marriages', 'residences', 'military',
                 'arrivals', 'departures',
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

        self.birth : LifeEvent = None
        self.death : LifeEvent = None

        self.baptism : List[LifeEvent] = []
        self.marriages : List[Marriage] = []
        self.residences : List[LifeEvent] = []
        self.military : List[LifeEvent] = []

        self.arrivals : List[LifeEvent] = []
        self.departures : List[LifeEvent] = []

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
        if self.birth and self.birth.date:
            year_num = self.birth.date.year_num
            description = f'Born {year_num}' if year_num else 'Born Unknown'
        elif self.death and self.death.date:
            year_num = self.death.date.year_num
            description = f'Died {year_num}' if year_num else 'Died Unknown'
        return description, year_num
    
    def bestlocation(self):
        """
        Returns the best known location for the person as [latlon, description].
        """
        best = ["Unknown", ""]
        if self.birth and self.birth.location:
            best = [
                str(self.birth.location.latlon),
                f"{self.birth.place} (Born)" if self.birth.place else "",
            ]
        elif self.death and self.death.location:
            best = [
                str(self.death.location.latlon),
                f"{self.death.place} (Died)" if self.death.place else "",
            ]
        return best

    def bestLatLon(self):
        """
        Returns the best known LatLon for the person (birth, then death, else None).
        """
        best = LatLon(None, None)
        if (
            self.birth
            and self.birth.location
            and self.birth.location.latlon
            and self.birth.location.latlon.hasLocation()
        ):
            best = self.birth.location.latlon
        elif (
            self.death
            and self.death.location
            and self.death.location.latlon
            and self.death.location.latlon.hasLocation()
        ):
            best = self.death.location.latlon
        return best

    def _check_birth_death_problems(self, born: Optional[int], died: Optional[int], max_age: int) -> list[str]:
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
        problems = []
        if not self.children:
            return problems
        for childId in self.children:
            child = people.get(childId)
            if not child or not (child.birth and child.birth.date and child.birth.date.year_num):
                continue
            child_birth_year = child.birth.date.year_num
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
        """
        born = self.birth.date.year_num if self.birth and self.birth.date and self.birth.date.year_num else None
        died = self.death.date.year_num if self.death and self.death.date and self.death.date.year_num else None

        problems = []
        problems += self._check_birth_death_problems(born, died, self.max_age)
        problems += self._check_parent_child_ages(people, born, died, self.max_mother_age, self.min_mother_age, self.max_father_age, self.min_father_age)
        return problems

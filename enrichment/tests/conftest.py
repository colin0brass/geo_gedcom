# /Users/osborne/git/gedcom-to-visualmap/gedcom-to-map/geo_gedcom/enrichment/tests/conftest.py
"""
Pytest fixtures for enrichment tests.
"""
from __future__ import annotations

import pytest
from datetime import date as _date
from typing import Dict, List

from geo_gedcom.person import Person
from geo_gedcom.life_event import LifeEvent
from geo_gedcom.enrichment.model import EnrichedPerson, DateRange, InferredEvent, Issue, Provenance
from geo_gedcom.enrichment.config import EnrichmentConfig


@pytest.fixture
def mock_person():
    """Create a mock Person object for testing."""
    def _create_person(xref_id: str, name: str = "Test Person", 
                      birth_date=None, birth_place=None,
                      death_date=None, death_place=None,
                      burial_date=None, burial_place=None) -> Person:
        person = Person(xref_id=xref_id)
        person.name = name
        
        if birth_date or birth_place:
            birth_event = LifeEvent(
                place=birth_place or "",
                date=birth_date,
                what="BIRT"
            )
            person.add_event('birth', birth_event)
        
        if death_date or death_place:
            death_event = LifeEvent(
                place=death_place or "",
                date=death_date,
                what="DEAT"
            )
            person.add_event('death', death_event)
        
        if burial_date or burial_place:
            burial_event = LifeEvent(
                place=burial_place or "",
                date=burial_date,
                what="BURI"
            )
            person.add_event('burial', burial_event)
        
        return person
    
    return _create_person


@pytest.fixture
def enriched_person(mock_person):
    """Create an EnrichedPerson for testing."""
    def _create_enriched(xref_id: str = "I1", **kwargs) -> EnrichedPerson:
        person = mock_person(xref_id, **kwargs)
        return EnrichedPerson(person=person)
    
    return _create_enriched


@pytest.fixture
def default_config():
    """Default enrichment configuration."""
    return EnrichmentConfig()


@pytest.fixture
def sample_family(mock_person):
    """Create a sample family with parents and children."""
    father = mock_person("I1", "John Doe", birth_date="1 JAN 1950")
    mother = mock_person("I2", "Jane Doe", birth_date="1 FEB 1952")
    child1 = mock_person("I3", "Alice Doe", birth_date="15 MAR 1975")
    child2 = mock_person("I4", "Bob Doe", birth_date="20 JUL 1977")
    
    # Set relationships
    father.children = ["I3", "I4"]
    mother.children = ["I3", "I4"]
    child1.father = father
    child1.mother = mother
    child2.father = father
    child2.mother = mother
    father.partners = ["I2"]
    mother.partners = ["I1"]
    
    return {
        "I1": father,
        "I2": mother,
        "I3": child1,
        "I4": child2
    }
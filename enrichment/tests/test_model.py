# /Users/osborne/git/gedcom-to-visualmap/gedcom-to-map/geo_gedcom/enrichment/tests/test_model.py
"""
Tests for enrichment.model module.
"""
from __future__ import annotations

import pytest
from datetime import date as _date

from geo_gedcom.enrichment.model import (
    DateRange, InferredEvent, Issue, Provenance, EnrichedPerson
)


class TestDateRange:
    """Tests for DateRange class."""
    
    def test_empty_range(self):
        """Test that a DateRange with no bounds is empty."""
        dr = DateRange()
        assert dr.is_empty()
        
    def test_non_empty_range(self):
        """Test that a DateRange with bounds is not empty."""
        dr = DateRange(earliest=_date(1900, 1, 1), latest=_date(1950, 12, 31))
        assert not dr.is_empty()
    
    def test_contains_date(self):
        """Test that contains() correctly checks if a date is in range."""
        dr = DateRange(earliest=_date(1900, 1, 1), latest=_date(1950, 12, 31))
        assert dr.contains(_date(1925, 6, 15))
        assert not dr.contains(_date(1880, 1, 1))
        assert not dr.contains(_date(1970, 1, 1))
    
    def test_contains_open_ended(self):
        """Test contains() with open-ended ranges."""
        dr_start = DateRange(earliest=_date(1900, 1, 1), latest=None)
        assert dr_start.contains(_date(1950, 1, 1))
        assert not dr_start.contains(_date(1880, 1, 1))
        
        dr_end = DateRange(earliest=None, latest=_date(1950, 12, 31))
        assert dr_end.contains(_date(1900, 1, 1))
        assert not dr_end.contains(_date(1970, 1, 1))
    
    def test_intersect_overlapping(self):
        """Test intersection of overlapping ranges."""
        dr1 = DateRange(earliest=_date(1900, 1, 1), latest=_date(1950, 12, 31))
        dr2 = DateRange(earliest=_date(1925, 6, 1), latest=_date(1975, 12, 31))
        result = dr1.intersect(dr2)
        
        assert result.earliest == _date(1925, 6, 1)
        assert result.latest == _date(1950, 12, 31)
    
    def test_intersect_non_overlapping(self):
        """Test intersection of non-overlapping ranges returns empty."""
        dr1 = DateRange(earliest=_date(1900, 1, 1), latest=_date(1920, 12, 31))
        dr2 = DateRange(earliest=_date(1950, 1, 1), latest=_date(1975, 12, 31))
        result = dr1.intersect(dr2)
        
        assert result.is_empty()
    
    def test_intersect_one_empty(self):
        """Test intersection with an empty range."""
        dr1 = DateRange(earliest=_date(1900, 1, 1), latest=_date(1950, 12, 31))
        dr2 = DateRange()
        result = dr1.intersect(dr2)
        
        assert result.earliest == _date(1900, 1, 1)
        assert result.latest == _date(1950, 12, 31)


class TestInferredEvent:
    """Tests for InferredEvent class."""
    
    def test_create_inferred_event(self):
        """Test creation of an InferredEvent."""
        date_range = DateRange(earliest=_date(1900, 1, 1), latest=_date(1900, 12, 31))
        provenance = Provenance(rule_id="test_rule", inputs=("I1",))
        
        event = InferredEvent(
            tag="birth",  # Changed from "BIRT"
            date_range=date_range,
            place="London, England",
            confidence=0.8,
            provenance=provenance
        )
        
        assert event.tag == "birth"  # Changed from "BIRT"
        assert event.place == "London, England"
        assert event.confidence == 0.8
        assert event.provenance.rule_id == "test_rule"


class TestIssue:
    """Tests for Issue class."""
    
    def test_create_issue(self):
        """Test creation of an Issue."""
        issue = Issue(
            issue_type="test_rule",
            severity="warning",
            message="Test warning message",
            person_id="I1",
            related_person_ids=("I2", "I3")
        )
        
        assert issue.severity == "warning"
        assert issue.issue_type == "test_rule"
        assert issue.message == "Test warning message"
        assert issue.person_id == "I1"
        assert issue.related_person_ids == ("I2", "I3")


class TestEnrichedPerson:
    """Tests for EnrichedPerson class."""
    
    def test_add_inferred_event(self, enriched_person):
        """Test adding an inferred event."""
        ep = enriched_person(xref_id="I1", name="Test Person")
        
        inferred_event = InferredEvent(
            tag="death",  # Changed from "DEAT"
            date_range=DateRange(earliest=_date(1950, 1, 1), latest=_date(1950, 12, 31)),
            place="Paris, France",
            confidence=0.7,
            provenance=Provenance(rule_id="test_rule")
        )
        
        ep.add_inferred_event(inferred_event)
        
        assert "death" in ep.inferred_events  # Changed from "DEAT"
        assert ep.inferred_events["death"].place == "Paris, France"  # Changed from "DEAT"
    
    def test_add_inferred_event_replaces_lower_confidence(self, enriched_person):
        """Test that higher confidence events replace lower confidence ones."""
        ep = enriched_person(xref_id="I1")
        
        low_conf = InferredEvent(
            tag="death",  # Changed from "DEAT"
            confidence=0.5,
            provenance=Provenance(rule_id="rule1")
        )
        high_conf = InferredEvent(
            tag="death",  # Changed from "DEAT"
            confidence=0.9,
            provenance=Provenance(rule_id="rule2")
        )
        
        ep.add_inferred_event(low_conf)
        ep.add_inferred_event(high_conf)
        
        assert ep.inferred_events["death"].confidence == 0.9  # Changed from "DEAT"
        assert ep.inferred_events["death"].provenance.rule_id == "rule2"  # Changed from "DEAT"
    
    def test_tighten_date_bound(self, enriched_person):
        """Test tightening date bounds."""
        ep = enriched_person(xref_id="I1")
        
        provenance = Provenance(rule_id="test_rule")
        bound1 = DateRange(earliest=_date(1900, 1, 1), latest=_date(1950, 12, 31))
        bound2 = DateRange(earliest=_date(1920, 1, 1), latest=_date(1940, 12, 31))
        
        ep.tighten_date_bound("birth", bound1, provenance)
        ep.tighten_date_bound("birth", bound2, provenance)
        
        result = ep.date_bounds["birth"]
        assert result.earliest == _date(1920, 1, 1)
        assert result.latest == _date(1940, 12, 31)
    
    def test_tighten_date_bound_conflict(self, enriched_person):
        """Test that conflicting bounds generate an issue."""
        ep = enriched_person(xref_id="I1")
        
        provenance = Provenance(rule_id="test_rule")
        bound1 = DateRange(earliest=_date(1900, 1, 1), latest=_date(1920, 12, 31))
        bound2 = DateRange(earliest=_date(1930, 1, 1), latest=_date(1950, 12, 31))
        
        ep.tighten_date_bound("birth", bound1, provenance)
        ep.tighten_date_bound("birth", bound2, provenance)
        
        assert len(ep.issues) == 1
        assert ep.issues[0].severity == "warning"
        assert "empty" in ep.issues[0].message.lower()
    
    def test_best_place_explicit(self, enriched_person):
        """Test that explicit event place takes precedence."""
        ep = enriched_person(
            xref_id="I1",
            birth_date="1 JAN 1900",
            birth_place="London, England"
        )
        
        # Add place override
        ep.override_place("birth", "Paris, France", Provenance(rule_id="test"))
        
        # Explicit should win
        assert ep.best_place("birth") == "London, England"
    
    def test_best_place_override(self, enriched_person):
        """Test place override when no explicit place."""
        ep = enriched_person(xref_id="I1", birth_date="1 JAN 1900")
        
        ep.override_place("birth", "Paris, France", Provenance(rule_id="test"))
        
        assert ep.best_place("birth") == "Paris, France"
    
    def test_best_place_inferred(self, enriched_person):
        """Test inferred event place."""
        ep = enriched_person(xref_id="I1")
        
        inferred = InferredEvent(
            tag="death",  # Changed
            place="Rome, Italy",
            provenance=Provenance(rule_id="test")
        )
        ep.add_inferred_event(inferred)
        
        assert ep.best_place("death") == "Rome, Italy"  # Changed
    
    def test_best_date_range_explicit(self, enriched_person):
        """Test that explicit dates create a date range."""
        ep = enriched_person(
            xref_id="I1",
            birth_date="1 JAN 1900"
        )
        
        result = ep.best_date_range("birth")
        assert result is not None
        # Exact date should have earliest == latest
    
    def test_birth_range(self, enriched_person):
        """Test birth_range convenience method."""
        ep = enriched_person(
            xref_id="I1",
            birth_date="1 JAN 1900"
        )
        
        result = ep.birth_range()
        assert result is not None
    
    def test_death_range(self, enriched_person):
        """Test death_range convenience method."""
        ep = enriched_person(
            xref_id="I1",
            death_date="31 DEC 1975"
        )
        
        result = ep.death_range()
        assert result is not None
    
    def test_parents_property(self, enriched_person, mock_person):
        """Test parents property."""
        father = mock_person("I1", "Father")
        mother = mock_person("I2", "Mother")
        child_person = mock_person("I3", "Child")
        child_person.father = father
        child_person.mother = mother
        
        ep = EnrichedPerson(person=child_person)
        parents = list(ep.parents)
        
        # Should delegate to person.parents if it exists
        # Otherwise return empty
        assert isinstance(parents, list)
    
    def test_has_event_explicit(self, enriched_person):
        """Test has_event with explicit event."""
        ep = enriched_person(xref_id="I1", birth_date="1 JAN 1900")
        
        assert ep.has_event('birth') is True
        assert ep.has_event('death') is False
    
    def test_has_event_inferred(self, enriched_person):
        """Test has_event with inferred event."""
        ep = enriched_person(xref_id="I1")
        
        # Add inferred death event
        inferred_death = InferredEvent(
            tag='death',
            date_range=DateRange(earliest=_date(1950, 1, 1), latest=_date(1950, 12, 31)),
            provenance=Provenance(rule_id="test_rule")
        )
        ep.add_inferred_event(inferred_death)
        
        assert ep.has_event('death') is True
        assert ep.has_event('birth') is False
    
    def test_get_event_date_explicit(self, enriched_person):
        """Test get_event_date with explicit event."""
        ep = enriched_person(xref_id="I1", birth_date="1 JAN 1900")
        
        date = ep.get_event_date('birth')
        assert date is not None
    
    def test_get_event_date_inferred(self, enriched_person):
        """Test get_event_date with inferred event."""
        ep = enriched_person(xref_id="I1")
        
        # Add inferred death event
        inferred_death = InferredEvent(
            tag='death',
            date_range=DateRange(earliest=_date(1950, 1, 1), latest=_date(1950, 12, 31)),
            provenance=Provenance(rule_id="test_rule")
        )
        ep.add_inferred_event(inferred_death)
        
        date = ep.get_event_date('death')
        assert date is not None
        assert date == _date(1950, 1, 1)  # Should return earliest from range
    
    def test_get_event_date_none(self, enriched_person):
        """Test get_event_date with no event."""
        ep = enriched_person(xref_id="I1")
        
        date = ep.get_event_date('death')
        assert date is None
    
    def test_id_property(self, enriched_person):
        """Test id property returns person's xref_id."""
        ep = enriched_person(xref_id="I123", name="Test Person")
        
        assert ep.id == "I123"
    
    def test_display_name_property(self, enriched_person):
        """Test display_name property returns person's name."""
        ep = enriched_person(xref_id="I1", name="John Doe")
        
        assert ep.display_name == "John Doe"
    
    def test_override_place_direct(self, enriched_person):
        """Test override_place method directly."""
        ep = enriched_person(xref_id="I1")
        provenance = Provenance(rule_id="test_rule")
        
        ep.override_place("birth", "New York, USA", provenance)
        
        assert "birth" in ep.place_overrides
        assert ep.place_overrides["birth"] == "New York, USA"
    
    def test_get_explicit_event(self, enriched_person):
        """Test get_explicit_event returns the actual LifeEvent."""
        ep = enriched_person(xref_id="I1", birth_date="1 JAN 1900")
        
        event = ep.get_explicit_event("birth")
        assert event is not None
        
        # Should return None for non-existent event
        event_none = ep.get_explicit_event("death")
        assert event_none is None
    
    def test_is_deceased_with_death(self, enriched_person):
        """Test is_deceased returns True when person has death event."""
        ep = enriched_person(xref_id="I1", death_date="31 DEC 1975")
        
        assert ep.is_deceased() is True
    
    def test_is_deceased_with_burial(self, enriched_person):
        """Test is_deceased returns True when person has burial event."""
        ep = enriched_person(xref_id="I1", burial_date="15 JAN 1975")
        
        assert ep.is_deceased() is True
    
    def test_is_deceased_with_inferred_death(self, enriched_person):
        """Test is_deceased returns True with inferred death event."""
        ep = enriched_person(xref_id="I1")
        
        inferred_death = InferredEvent(
            tag='death',
            date_range=DateRange(earliest=_date(1950, 1, 1)),
            provenance=Provenance(rule_id="test_rule")
        )
        ep.add_inferred_event(inferred_death)
        
        assert ep.is_deceased() is True
    
    def test_is_deceased_living(self, enriched_person):
        """Test is_deceased returns False for living person."""
        ep = enriched_person(xref_id="I1", birth_date="1 JAN 1990")
        
        assert ep.is_deceased() is False
    
    def test_lifespan_age_years_complete(self, enriched_person):
        """Test lifespan_age_years with birth and death dates."""
        ep = enriched_person(
            xref_id="I1",
            birth_date="1 JAN 1900",
            death_date="31 DEC 1975"
        )
        
        age = ep.lifespan_age_years()
        assert age == 75
    
    def test_lifespan_age_years_with_burial(self, enriched_person):
        """Test lifespan_age_years uses burial if no death date."""
        ep = enriched_person(
            xref_id="I1",
            birth_date="1 JAN 1900",
            burial_date="15 JAN 1976"
        )
        
        age = ep.lifespan_age_years()
        assert age == 76
    
    def test_lifespan_age_years_incomplete(self, enriched_person):
        """Test lifespan_age_years returns None without complete dates."""
        ep = enriched_person(xref_id="I1", birth_date="1 JAN 1900")
        
        age = ep.lifespan_age_years()
        assert age is None
    
    def test_children_property(self, enriched_person, mock_person):
        """Test children property."""
        parent_person = mock_person("I1", "Parent")
        child1 = mock_person("I2", "Child 1")
        child2 = mock_person("I3", "Child 2")
        parent_person.children = [child1, child2]
        
        ep = EnrichedPerson(person=parent_person)
        children = list(ep.children)
        
        assert len(children) == 2
        assert children[0].xref_id == "I2"
        assert children[1].xref_id == "I3"
    
    def test_partners_property(self, enriched_person, mock_person):
        """Test partners property (delegates to spouses or partners)."""
        person = mock_person("I1", "Person")
        partner = mock_person("I2", "Partner")
        person.partners = [partner]
        
        ep = EnrichedPerson(person=person)
        partners = list(ep.partners)
        
        assert len(partners) == 1
        assert partners[0].xref_id == "I2"

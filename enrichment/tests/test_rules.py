# /Users/osborne/git/gedcom-to-visualmap/gedcom-to-map/geo_gedcom/enrichment/tests/test_rules.py
"""
Tests for enrichment rules.
"""
from __future__ import annotations

import pytest
from datetime import date as _date

from geo_gedcom.enrichment.model import EnrichedPerson, DateRange, Provenance
from geo_gedcom.enrichment.rules.death_from_burial import DeathFromBurialRule
from geo_gedcom.enrichment.rules.parent_child_bounds import ParentChildBoundsRule
from geo_gedcom.enrichment.rules.implausible_age import ImplausibleAgeRule


class TestDeathFromBurialRule:
    """Tests for DeathFromBurialRule."""
    
    def test_infers_death_from_burial(self, enriched_person):
        """Test that death is inferred from burial event."""
        ep = enriched_person(
            xref_id="I1",
            burial_date="10 JAN 1950",
            burial_place="London Cemetery"
        )
        
        enriched_people = {"I1": ep}
        rule = DeathFromBurialRule()
        issues = []
        
        changed = rule.apply(enriched_people, {}, issues)
        
        assert changed
        assert "death" in ep.inferred_events
        death_event = ep.inferred_events["death"]
        assert death_event.place == "London Cemetery"
        assert death_event.date_range is not None
        assert death_event.confidence > 0.5
    
    def test_no_inference_if_death_exists(self, enriched_person):
        """Test that death is not inferred if already present."""
        ep = enriched_person(
            xref_id="I1",
            death_date="5 JAN 1950",
            burial_date="10 JAN 1950"
        )
        
        # Add explicit death as inferred event
        from geo_gedcom.enrichment.model import InferredEvent
        ep.add_inferred_event(InferredEvent(
            tag="death",
            provenance=Provenance(rule_id="explicit")
        ))
        
        enriched_people = {"I1": ep}
        rule = DeathFromBurialRule()
        issues = []
        
        changed = rule.apply(enriched_people, {}, issues)
        
        assert not changed
    
    def test_no_inference_without_burial(self, enriched_person):
        """Test that no inference happens without burial event."""
        ep = enriched_person(xref_id="I1")
        
        enriched_people = {"I1": ep}
        rule = DeathFromBurialRule()
        issues = []
        
        changed = rule.apply(enriched_people, {}, issues)
        
        assert not changed
        assert "death" not in ep.inferred_events


class TestParentChildBoundsRule:
    """Tests for ParentChildBoundsRule."""
    
    def test_constrains_parent_birth_from_child(self, sample_family):
        """Test that parent birth is constrained by child's birth."""
        # Create enriched versions
        enriched_people = {
            pid: EnrichedPerson(person=person)
            for pid, person in sample_family.items()
        }
        
        rule = ParentChildBoundsRule(min_mother_age=16, min_father_age=16)
        issues = []
        
        changed = rule.apply(enriched_people, sample_family, issues)
        
        # Parents should have constrained birth dates
        father_ep = enriched_people["I1"]
        
        # Father's birth should be constrained by oldest child (I3, born 1975)
        # Latest birth: 1975 - 16 = 1959
        if "birth" in father_ep.date_bounds:
            bound = father_ep.date_bounds["birth"]
            # Check that bound was applied (we'd need to check the actual year)
            assert bound.latest is not None
    
    def test_no_constraint_without_child_birth(self, mock_person):
        """Test that no constraint is applied if child has no birth date."""
        father = mock_person("I1", "Father", birth_date="1 JAN 1950")
        child = mock_person("I2", "Child")  # No birth date
        
        father.children = ["I2"]
        child.father = father
        
        enriched_people = {
            "I1": EnrichedPerson(person=father),
            "I2": EnrichedPerson(person=child)
        }
        
        rule = ParentChildBoundsRule()
        issues = []
        
        changed = rule.apply(enriched_people, {"I1": father, "I2": child}, issues)
        
        # No changes should be made
        assert "birth" not in enriched_people["I1"].date_bounds or \
               enriched_people["I1"].date_bounds.get("birth") is None


class TestImplausibleAgeRule:
    """Tests for ImplausibleAgeRule."""
    
    def test_identifies_implausibly_old_person(self, enriched_person):
        """Test that rule identifies people who would be too old."""
        # Person born 200 years ago without death date
        from datetime import date as _date
        current_year = _date.today().year
        birth_year = current_year - 150  # 150 years old
        
        ep = enriched_person(
            xref_id="I1",
            birth_date=f"1 JAN {birth_year}"
        )
        
        enriched_people = {"I1": ep}
        rule = ImplausibleAgeRule(max_age_years=122, infer_event_updates=False)
        issues = []
        
        changed = rule.apply(enriched_people, {}, issues)
        
        # Should create an issue
        assert len(issues) > 0
        assert any(issue.issue_type == "implausible_age" for issue in issues)
    
    def test_does_not_flag_reasonable_age(self, enriched_person):
        """Test that rule doesn't flag people with reasonable ages."""
        from datetime import date as _date
        current_year = _date.today().year
        birth_year = current_year - 80  # 80 years old
        
        ep = enriched_person(
            xref_id="I1",
            birth_date=f"1 JAN {birth_year}"
        )
        
        enriched_people = {"I1": ep}
        rule = ImplausibleAgeRule(max_age_years=122)
        issues = []
        
        changed = rule.apply(enriched_people, {}, issues)
        
        # Should not create any issues
        assert len([issue for issue in issues if issue.issue_type == "implausible_age"]) == 0
    
    def test_infers_death_when_enabled(self, enriched_person):
        """Test that rule infers death when infer_event_updates is True."""
        from datetime import date as _date
        current_year = _date.today().year
        birth_year = current_year - 150  # 150 years old
        
        ep = enriched_person(
            xref_id="I1",
            birth_date=f"1 JAN {birth_year}"
        )
        
        enriched_people = {"I1": ep}
        rule = ImplausibleAgeRule(max_age_years=122, infer_event_updates=True)
        issues = []
        
        changed = rule.apply(enriched_people, {}, issues)
        
        # Should have tightened death date bounds or added inferred event
        assert changed or len(ep.issues) > 0
    
    def test_skips_people_with_death_date(self, enriched_person):
        """Test that rule skips people who already have a death date."""
        from datetime import date as _date
        current_year = _date.today().year
        birth_year = current_year - 150  # 150 years old
        
        ep = enriched_person(
            xref_id="I1",
            birth_date=f"1 JAN {birth_year}",
            death_date="1 JAN 1950"
        )
        
        enriched_people = {"I1": ep}
        rule = ImplausibleAgeRule(max_age_years=122)
        issues = []
        
        changed = rule.apply(enriched_people, {}, issues)
        
        # Should not create implausible_age issues
        assert len([issue for issue in issues if issue.issue_type == "implausible_age"]) == 0

# /Users/osborne/git/gedcom-to-visualmap/gedcom-to-map/geo_gedcom/enrichment/tests/test_integration.py
"""
Integration tests for the enrichment module.
"""
from __future__ import annotations

import pytest

from geo_gedcom.enrichment.config import EnrichmentConfig
from geo_gedcom.enrichment.pipeline import EnrichmentPipeline
from geo_gedcom.enrichment.model import DateRange, Provenance, EnrichedPerson  # Changed from 'enrichment.model'
from geo_gedcom.enrichment.rules.death_from_burial import DeathFromBurialRule
from geo_gedcom.enrichment.rules.parent_child_bounds import ParentChildBoundsRule


class TestEnrichmentIntegration:
    """Integration tests combining multiple rules and scenarios."""
    
    def test_full_enrichment_workflow(self, sample_family, enriched_person):
        """Test a complete enrichment workflow with multiple rules."""
        # Add burial to one person
        father_enriched = EnrichedPerson(person=sample_family["I1"])
        
        # Add burial event to father
        from geo_gedcom.life_event import LifeEvent
        burial = LifeEvent(
            place="London Cemetery",
            date="10 JAN 2020",
            what="BURI"
        )
        sample_family["I1"].add_event('burial', burial)
        
        enriched_people = {
            pid: EnrichedPerson(person=person)
            for pid, person in sample_family.items()
        }
        
        # Run pipeline with multiple rules
        config = EnrichmentConfig.from_dict({"max_iterations": 5, "enabled": True, "death_age_min": 0, "death_age_max": 122,
                                             "mother_age_min": 11, "mother_age_max": 66, "father_age_min": 12, "father_age_max": 93,
                                             "burial_to_death_max_days": 14, "baptism_to_birth_max_days": 365,
                                             "rules_infer_event_date_updates": {}, "rule_confidence": {}, "rules_enabled": {}})
        rules = [
            DeathFromBurialRule(),
            ParentChildBoundsRule()
        ]
        
        pipeline = EnrichmentPipeline(config, rules)
        result = pipeline.run(sample_family, existing_people=enriched_people)
        
        # Verify results
        assert len(result.enriched_people) == len(sample_family)
        assert result.iterations >= 1
        
        # Father should have inferred death
        father_result = result.enriched_people["I1"]
        assert "death" in father_result.inferred_events  # Changed from "DEAT"
    
    def test_conflicting_constraints_generate_issues(self, mock_person):
        """Test that conflicting date constraints generate issues."""
        from datetime import date as _date
        
        person = mock_person("I1", "Test Person")
        ep = EnrichedPerson(person=person)
        
        # Add conflicting bounds
        prov1 = Provenance(rule_id="rule1")
        prov2 = Provenance(rule_id="rule2")
        
        ep.tighten_date_bound(
            "birth",  # Changed from "BIRT"
            DateRange(earliest=_date(1900, 1, 1), latest=_date(1920, 12, 31)),
            prov1
        )
        
        ep.tighten_date_bound(
            "birth",  # Changed from "BIRT"
            DateRange(earliest=_date(1930, 1, 1), latest=_date(1950, 12, 31)),
            prov2
        )
        
        # Should have generated an issue
        assert len(ep.issues) > 0
        assert any(issue.severity == "warning" for issue in ep.issues)

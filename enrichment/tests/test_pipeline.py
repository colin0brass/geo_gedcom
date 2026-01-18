# /Users/osborne/git/gedcom-to-visualmap/gedcom-to-map/geo_gedcom/enrichment/tests/test_pipeline.py
"""
Tests for enrichment pipeline.
"""
from __future__ import annotations

import pytest

from geo_gedcom.enrichment.config import EnrichmentConfig
from geo_gedcom.enrichment.pipeline import EnrichmentPipeline
from geo_gedcom.enrichment.model import EnrichedPerson
from geo_gedcom.enrichment.rules.death_from_burial import DeathFromBurialRule


class TestEnrichmentPipeline:
    """Tests for EnrichmentPipeline."""
    
    def test_pipeline_runs_rules(self, sample_family):
        """Test that pipeline runs rules and returns results."""
        config = EnrichmentConfig.from_dict({"max_iterations": 2, "enabled": True, "death_age_min": 0, "death_age_max": 122,
                                             "mother_age_min": 11, "mother_age_max": 66, "father_age_min": 12, "father_age_max": 93,
                                             "burial_to_death_max_days": 14, "baptism_to_birth_max_days": 365,
                                             "rules_infer_event_date_updates": {}, "rule_confidence": {}, "rules_enabled": {}})
        rules = [DeathFromBurialRule()]
        
        pipeline = EnrichmentPipeline(config, rules)
        result = pipeline.run(sample_family)
        
        assert result is not None
        assert isinstance(result.enriched_people, dict)
        assert len(result.enriched_people) == len(sample_family)
        assert result.iterations >= 1
    
    def test_pipeline_respects_max_iterations(self, sample_family):
        """Test that pipeline respects max_iterations setting."""
        config = EnrichmentConfig.from_dict({"max_iterations": 1, "enabled": True, "death_age_min": 0, "death_age_max": 122,
                                             "mother_age_min": 11, "mother_age_max": 66, "father_age_min": 12, "father_age_max": 93,
                                             "burial_to_death_max_days": 14, "baptism_to_birth_max_days": 365,
                                             "rules_infer_event_date_updates": {}, "rule_confidence": {}, "rules_enabled": {}})
        rules = [DeathFromBurialRule()]
        
        pipeline = EnrichmentPipeline(config, rules)
        result = pipeline.run(sample_family)
        
        assert result.iterations <= 1
    
    def test_pipeline_stops_when_stable(self, sample_family):
        """Test that pipeline stops when no more changes occur."""
        config = EnrichmentConfig.from_dict({"max_iterations": 10, "enabled": True, "death_age_min": 0, "death_age_max": 122,
                                             "mother_age_min": 11, "mother_age_max": 66, "father_age_min": 12, "father_age_max": 93,
                                             "burial_to_death_max_days": 14, "baptism_to_birth_max_days": 365,
                                             "rules_infer_event_date_updates": {}, "rule_confidence": {}, "rules_enabled": {}})
        rules = [DeathFromBurialRule()]
        
        pipeline = EnrichmentPipeline(config, rules)
        result = pipeline.run(sample_family)
        
        # Should stop before max_iterations since rule makes no changes after first run
        assert result.iterations < 10
    
    def test_pipeline_tracks_rule_runs(self, sample_family):
        """Test that pipeline tracks how many times each rule runs."""
        config = EnrichmentConfig.from_dict({"max_iterations": 3, "enabled": True, "death_age_min": 0, "death_age_max": 122,
                                             "mother_age_min": 11, "mother_age_max": 66, "father_age_min": 12, "father_age_max": 93,
                                             "burial_to_death_max_days": 14, "baptism_to_birth_max_days": 365,
                                             "rules_infer_event_date_updates": {}, "rule_confidence": {}, "rules_enabled": {}})
        rule = DeathFromBurialRule()
        rules = [rule]
        
        pipeline = EnrichmentPipeline(config, rules)
        result = pipeline.run(sample_family)
        
        assert rule.rule_id in result.rule_runs
        assert result.rule_runs[rule.rule_id] >= 1
    
    def test_pipeline_with_disabled_rule(self, sample_family):
        """Test that disabled rules are not executed."""
        config = EnrichmentConfig.from_dict({"max_iterations": 2, "enabled": True, "death_age_min": 0, "death_age_max": 122,
                                             "mother_age_min": 11, "mother_age_max": 66, "father_age_min": 12, "father_age_max": 93,
                                             "burial_to_death_max_days": 14, "baptism_to_birth_max_days": 365,
                                             "rules_infer_event_date_updates": {}, "rule_confidence": {},
                                             "rules_enabled": {"death_from_burial": False}})
        rule = DeathFromBurialRule()
        rules = [rule]
        
        pipeline = EnrichmentPipeline(config, rules)
        result = pipeline.run(sample_family)
        
        # Rule should not have run
        assert rule.rule_id not in result.rule_runs or result.rule_runs[rule.rule_id] == 0


class TestEnrichmentConfig:
    """Tests for EnrichmentConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = EnrichmentConfig()
        
        assert config.enabled is True
        assert config.max_iterations > 0
        assert config.death_age_max == 122
    
    def test_rule_enabled_default(self):
        """Test that rules are enabled by default."""
        config = EnrichmentConfig()
        assert config.rule_enabled("some_rule") is True
    
    def test_rule_explicitly_disabled(self):
        """Test that explicitly disabled rules return False."""
        config = EnrichmentConfig.from_dict({"max_iterations": 3, "enabled": True, "death_age_min": 0, "death_age_max": 122,
                                             "mother_age_min": 11, "mother_age_max": 66, "father_age_min": 12, "father_age_max": 93,
                                             "burial_to_death_max_days": 14, "baptism_to_birth_max_days": 365,
                                             "rules_infer_event_date_updates": {}, "rule_confidence": {},
                                             "rules_enabled": {"test_rule": False}})
        assert config.rule_enabled("test_rule") is False
    
    def test_rule_explicitly_enabled(self):
        """Test that explicitly enabled rules return True."""
        config = EnrichmentConfig.from_dict({"max_iterations": 3, "enabled": True, "death_age_min": 0, "death_age_max": 122,
                                             "mother_age_min": 11, "mother_age_max": 66, "father_age_min": 12, "father_age_max": 93,
                                             "burial_to_death_max_days": 14, "baptism_to_birth_max_days": 365,
                                             "rules_infer_event_date_updates": {}, "rule_confidence": {},
                                             "rules_enabled": {"test_rule": True}})
        assert config.rule_enabled("test_rule") is True

"""
Tests for built-in statistics collectors.
"""
from __future__ import annotations

import pytest

from geo_gedcom.statistics.collectors import (
    DemographicsCollector,
    EventCompletenessCollector,
    GeographicCollector
)
from geo_gedcom.statistics import StatisticsPipeline, Stats


class TestDemographicsCollector:
    """Tests for DemographicsCollector."""
    
    def test_basic_demographics(self, sample_people):
        """Test basic demographic statistics."""
        collector = DemographicsCollector()
        stats = Stats()
        
        result = collector.collect(sample_people, stats)
        
        assert result.get_value('demographics', 'total_people') == 3
        # Note: Actual living/deceased counts depend on Person implementation
    
    def test_birth_year_statistics(self, sample_people_with_dates):
        """Test birth year statistics."""
        collector = DemographicsCollector()
        stats = Stats()
        
        result = collector.collect(sample_people_with_dates, stats)
        
        birth_dist = result.get_value('demographics', 'birth_year_distribution')
        assert birth_dist is not None
        assert result.get_value('demographics', 'earliest_birth_year') is not None


class TestEventCompletenessCollector:
    """Tests for EventCompletenessCollector."""
    
    def test_event_counts(self, sample_people_with_dates):
        """Test event counting."""
        collector = EventCompletenessCollector()
        stats = Stats()
        
        result = collector.collect(sample_people_with_dates, stats)
        
        event_counts = result.get_value('events', 'event_counts')
        assert event_counts is not None
        assert result.get_value('events', 'total_people') == 3


class TestGeographicCollector:
    """Tests for GeographicCollector."""
    
    def test_place_collection(self, sample_people_with_places):
        """Test place statistics."""
        collector = GeographicCollector()
        stats = Stats()
        
        result = collector.collect(sample_people_with_places, stats)
        
        unique_places = result.get_value('geographic', 'unique_places')
        # Should have at least some places if data has them
        assert unique_places is not None


class TestIntegration:
    """Integration tests with full pipeline."""
    
    def test_full_pipeline(self, sample_people_with_dates):
        """Test running full pipeline with all collectors."""
        pipeline = StatisticsPipeline()
        
        stats = pipeline.run(sample_people_with_dates)
        
        # Should have data from all three collectors
        assert stats.get_value('demographics', 'total_people') is not None
        assert stats.get_value('events', 'total_people') is not None


# Fixtures

@pytest.fixture
def sample_people():
    """Create sample people for testing."""
    from geo_gedcom.person import Person
    
    people = []
    for i in range(1, 4):
        person = Person(xref_id=f"I{i}")
        person.name = f"Person {i}"
        people.append(person)
    
    return people


@pytest.fixture
def sample_people_with_dates(enriched_person):
    """Create sample people with birth/death dates."""
    people = [
        enriched_person('I1', name='Person 1', birth_date='1 JAN 1900', death_date='31 DEC 1975'),
        enriched_person('I2', name='Person 2', birth_date='15 MAR 1925', death_date='10 JUN 2000'),
        enriched_person('I3', name='Person 3', birth_date='20 JUL 1950'),
    ]
    
    return [p.person for p in people]


@pytest.fixture
def sample_people_with_places(enriched_person):
    """Create sample people with birth places."""
    people = [
        enriched_person('I1', name='Person 1', birth_date='1 JAN 1900', birth_place='London, England'),
        enriched_person('I2', name='Person 2', birth_date='15 MAR 1925', birth_place='Paris, France'),
        enriched_person('I3', name='Person 3', birth_date='20 JUL 1950', birth_place='New York, USA'),
    ]
    
    return [p.person for p in people]


@pytest.fixture
def enriched_person():
    """Fixture for creating EnrichedPerson objects."""
    from geo_gedcom.enrichment.tests.conftest import mock_person as _mock_person
    from geo_gedcom.enrichment.model import EnrichedPerson
    from geo_gedcom.person import Person
    from geo_gedcom.life_event import LifeEvent
    
    def _create_enriched(xref_id: str = "I1", **kwargs) -> EnrichedPerson:
        person = Person(xref_id=xref_id)
        person.name = kwargs.get('name', 'Test Person')
        
        # Add birth event
        if 'birth_date' in kwargs or 'birth_place' in kwargs:
            birth_event = LifeEvent(
                place=kwargs.get('birth_place', ''),
                date=kwargs.get('birth_date'),
                what="BIRT"
            )
            person.add_event('birth', birth_event)
        
        # Add death event
        if 'death_date' in kwargs or 'death_place' in kwargs:
            death_event = LifeEvent(
                place=kwargs.get('death_place', ''),
                date=kwargs.get('death_date'),
                what="DEAT"
            )
            person.add_event('death', death_event)
        
        return EnrichedPerson(person=person)
    
    return _create_enriched

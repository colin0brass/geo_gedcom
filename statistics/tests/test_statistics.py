"""
Tests for Statistics convenience wrapper class.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from geo_gedcom.statistics import Statistics
from geo_gedcom.person import Person


class TestStatistics:
    """Tests for Statistics wrapper class."""
    
    def test_init_with_people(self, sample_people):
        """Test initializing with people dictionary."""
        stats = Statistics(people=sample_people)
        
        assert stats.results is not None
        assert stats.get_value('demographics', 'total_people') == 3
    
    def test_init_with_gedcom_parser(self, mock_gedcom_parser):
        """Test initializing with gedcom_parser."""
        stats = Statistics(gedcom_parser=mock_gedcom_parser)
        
        assert stats.results is not None
        assert stats.get_value('demographics', 'total_people') == 2
    
    def test_get_value(self, sample_people):
        """Test get_value convenience method."""
        stats = Statistics(people=sample_people)
        
        total = stats.get_value('demographics', 'total_people')
        assert total == 3
        
        # Non-existent value
        missing = stats.get_value('demographics', 'nonexistent', default=0)
        assert missing == 0
    
    def test_get_category(self, sample_people):
        """Test get_category convenience method."""
        stats = Statistics(people=sample_people)
        
        demographics = stats.get_category('demographics')
        assert isinstance(demographics, dict)
        assert 'total_people' in demographics
    
    def test_to_dict(self, sample_people):
        """Test to_dict export."""
        stats = Statistics(people=sample_people)
        
        data = stats.to_dict()
        assert isinstance(data, dict)
        assert 'demographics' in data
    
    def test_analyze_method(self, sample_people):
        """Test analyze method with new data."""
        stats = Statistics(people={})
        
        # Should have no results initially
        assert stats.get_value('demographics', 'total_people', 0) == 0
        
        # Analyze with new people
        results = stats.analyze(sample_people)
        assert results is not None
        assert stats.get_value('demographics', 'total_people') == 3
    
    def test_config_dict(self, sample_people):
        """Test initialization with config dictionary."""
        config_dict = {
            'collectors': {
                'demographics': True,
                'event_completeness': False,
                'geographic': False
            }
        }
        
        stats = Statistics(people=sample_people, config_dict=config_dict)
        
        # Should still have demographics
        assert stats.get_value('demographics', 'total_people') == 3
    
    def test_empty_initialization(self):
        """Test initialization with no people."""
        stats = Statistics()
        
        assert stats.results is None
        assert stats.get_value('demographics', 'total_people') is None


# Fixtures

@pytest.fixture
def sample_people():
    """Create sample people dictionary."""
    people = {}
    for i in range(1, 4):
        person = Person(xref_id=f"I{i}")
        person.name = f"Person {i}"
        people[f"I{i}"] = person
    
    return people


@pytest.fixture
def mock_gedcom_parser():
    """Create a mock gedcom parser with people."""
    class MockParser:
        def __init__(self):
            self.people = {
                'I1': Person(xref_id='I1'),
                'I2': Person(xref_id='I2')
            }
            self.people['I1'].name = "Test Person 1"
            self.people['I2'].name = "Test Person 2"
    
    return MockParser()

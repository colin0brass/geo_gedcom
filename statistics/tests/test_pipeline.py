"""
Tests for statistics.pipeline module.
"""
from __future__ import annotations

import pytest
from dataclasses import dataclass
from typing import Any, Iterable

from geo_gedcom.statistics.base import StatisticsCollector, register_collector
from geo_gedcom.statistics.model import Stats
from geo_gedcom.statistics.pipeline import StatisticsPipeline, StatisticsConfig


# Mock collector for testing (not a test class, so doesn't start with "Test")
@dataclass
class MockCollector(StatisticsCollector):
    """Mock collector for testing."""
    collector_id: str = "mock_collector"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats) -> Stats:
        stats = Stats()
        stats.add_value('test', 'count', len(list(people)))
        return stats


class TestStatisticsConfig:
    """Tests for StatisticsConfig class."""
    
    def test_default_enabled(self):
        """Test that collectors are enabled by default."""
        config = StatisticsConfig()
        
        assert config.is_enabled('any_collector') is True
    
    def test_explicitly_disabled(self):
        """Test explicitly disabling a collector."""
        config = StatisticsConfig(collectors={'test_collector': False})
        
        assert config.is_enabled('test_collector') is False
    
    def test_explicitly_enabled(self):
        """Test explicitly enabling a collector."""
        config = StatisticsConfig(collectors={'test_collector': True})
        
        assert config.is_enabled('test_collector') is True
    
    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {'collectors': {'test_collector': False, 'other_collector': True}}
        
        config = StatisticsConfig.from_dict(data)
        
        assert config.is_enabled('test_collector') is False
        assert config.is_enabled('other_collector') is True


class TestStatisticsPipeline:
    """Tests for StatisticsPipeline class."""
    
    def test_run_pipeline_with_collector(self, mock_person):
        """Test running pipeline with a mock collector."""
        people = [
            mock_person('I1', 'Person 1'),
            mock_person('I2', 'Person 2'),
            mock_person('I3', 'Person 3'),
        ]
        
        collector = MockCollector()
        pipeline = StatisticsPipeline(collectors=[collector])
        
        stats = pipeline.run(people)
        
        assert stats.get_value('test', 'count') == 3
    
    def test_pipeline_respects_enabled_flag(self, mock_person):
        """Test that disabled collectors are not run."""
        people = [mock_person('I1', 'Person 1')]
        
        collector = MockCollector(enabled=False)
        pipeline = StatisticsPipeline(collectors=[collector])
        
        stats = pipeline.run(people)
        
        # Should have no results since collector was disabled
        assert stats.get_value('test', 'count') is None
    
    def test_pipeline_with_config(self, mock_person):
        """Test pipeline with configuration."""
        people = [mock_person('I1', 'Person 1')]
        
        config = StatisticsConfig(collectors={'mock_collector': False})
        collector = MockCollector(enabled=config.is_enabled('mock_collector'))
        pipeline = StatisticsPipeline(collectors=[collector], config=config)
        
        stats = pipeline.run(people)
        
        # Collector should be disabled
        assert stats.get_value('test', 'count') is None


@pytest.fixture
def mock_person():
    """Create a mock Person for testing."""
    from geo_gedcom.person import Person
    
    def _create_person(xref_id: str, name: str = "Test Person") -> Person:
        person = Person(xref_id=xref_id)
        person.name = name
        return person
    
    return _create_person

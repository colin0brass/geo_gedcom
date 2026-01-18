"""
Tests for statistics.model module.
"""
from __future__ import annotations

import pytest

from geo_gedcom.statistics.model import Stats


class TestStats:
    """Tests for Stats class."""
    
    def test_add_and_get_value(self):
        """Test adding and retrieving values."""
        stats = Stats()
        
        stats.add_value('demographics', 'total_people', 100)
        
        assert stats.get_value('demographics', 'total_people') == 100
    
    def test_get_nonexistent_value(self):
        """Test getting a nonexistent value returns None."""
        stats = Stats()
        
        assert stats.get_value('demographics', 'total_people') is None
    
    def test_get_value_with_default(self):
        """Test getting value with default."""
        stats = Stats()
        
        assert stats.get_value('demographics', 'total_people', 0) == 0
    
    def test_get_category(self):
        """Test getting all values in a category."""
        stats = Stats()
        
        stats.add_value('demographics', 'total_people', 100)
        stats.add_value('demographics', 'living', 60)
        stats.add_value('demographics', 'deceased', 40)
        
        category = stats.get_category('demographics')
        
        assert len(category) == 3
        assert category['total_people'] == 100
        assert category['living'] == 60
        assert category['deceased'] == 40
    
    def test_merge(self):
        """Test merging two Stats objects."""
        stats1 = Stats()
        stats1.add_value('demographics', 'total_people', 100)
        stats1.add_value('events', 'birth_count', 80)
        
        stats2 = Stats()
        stats2.add_value('demographics', 'living', 60)
        stats2.add_value('geographic', 'unique_places', 25)
        
        stats1.merge(stats2)
        
        assert stats1.get_value('demographics', 'total_people') == 100
        assert stats1.get_value('demographics', 'living') == 60
        assert stats1.get_value('events', 'birth_count') == 80
        assert stats1.get_value('geographic', 'unique_places') == 25
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        stats = Stats()
        stats.add_value('demographics', 'total_people', 100)
        stats.add_value('events', 'birth_count', 80)
        
        result = stats.to_dict()
        
        assert isinstance(result, dict)
        assert result['demographics']['total_people'] == 100
        assert result['events']['birth_count'] == 80
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            'demographics': {'total_people': 100, 'living': 60},
            'events': {'birth_count': 80}
        }
        
        stats = Stats.from_dict(data)
        
        assert stats.get_value('demographics', 'total_people') == 100
        assert stats.get_value('demographics', 'living') == 60
        assert stats.get_value('events', 'birth_count') == 80

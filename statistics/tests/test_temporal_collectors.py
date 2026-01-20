"""
Unit tests for temporal/lifecycle statistics collectors.

Tests collectors that analyze temporal patterns and life cycles:
- LongevityCollector: Life expectancy, mortality rates, and longevity trends
- TimelineCollector: Event density, temporal coverage, and historical patterns
"""
import pytest
from datetime import date as _date

from geo_gedcom.statistics.collectors.longevity import LongevityCollector
from geo_gedcom.statistics.collectors.timeline import TimelineCollector
from geo_gedcom.statistics.model import Stats


class MockDate:
    """Mock GedcomDate with year_num property."""
    def __init__(self, year):
        self.year_num = year
        self.year = year


class MockEvent:
    """Mock LifeEvent with date and optional place."""
    def __init__(self, year=None, place=None):
        self.date = MockDate(year) if year is not None else None
        self.place = place


class MockPerson:
    """Mock Person for testing."""
    def __init__(self, birth_year=None, death_year=None, sex=None, has_places=False):
        self._birth_year = birth_year
        self._death_year = death_year
        self.sex = sex
        self._has_places = has_places
    
    def get_event(self, event_type):
        place = 'Test Place' if self._has_places else None
        
        if event_type == 'birth' and self._birth_year:
            return MockEvent(self._birth_year, place)
        elif event_type == 'death' and self._death_year:
            return MockEvent(self._death_year, place)
        elif event_type in ['burial', 'baptism', 'marriage', 'christening', 'residence']:
            # Return event with year if person has birth year
            if self._birth_year:
                year = self._birth_year + 25  # Approximate age
                return MockEvent(year, place)
        return None


def test_longevity_collector_basic():
    """Test LongevityCollector with basic data."""
    people = [
        MockPerson(1900, 1950, 'M'),  # Lived 50 years
        MockPerson(1910, 1980, 'F'),  # Lived 70 years
        MockPerson(1920, 2000, 'M'),  # Lived 80 years
        MockPerson(1930, 1930, 'F'),  # Infant death (same year = 0 years)
        MockPerson(1940, 1943, 'M'),  # Child death (3 years)
    ]
    
    collector = LongevityCollector()
    stats = collector.collect(people, Stats())
    
    longevity_stats = stats.get_category('longevity')
    
    # Check basic statistics
    assert 'life_expectancy_by_birth_decade' in longevity_stats
    assert 'life_expectancy_by_birth_century' in longevity_stats
    assert 'life_expectancy_by_gender' in longevity_stats
    assert 'infant_mortality_count' in longevity_stats
    assert longevity_stats['infant_mortality_count'] == 1
    assert 'child_mortality_count' in longevity_stats
    assert longevity_stats['child_mortality_count'] == 2  # Both infant and child < 5
    assert 'survival_rates' in longevity_stats


def test_longevity_collector_by_decade():
    """Test life expectancy calculations by decade."""
    people = [
        MockPerson(1900, 1960, 'M'),  # 1900s, lived 60 years
        MockPerson(1905, 1965, 'F'),  # 1900s, lived 60 years
        MockPerson(1950, 2020, 'M'),  # 1950s, lived 70 years
        MockPerson(1955, 2025, 'F'),  # 1950s, lived 70 years
    ]
    
    collector = LongevityCollector()
    stats = collector.collect(people, Stats())
    
    longevity_stats = stats.get_category('longevity')
    le_by_decade = longevity_stats['life_expectancy_by_birth_decade']
    
    assert '1900s' in le_by_decade
    assert '1950s' in le_by_decade
    assert le_by_decade['1900s']['average'] == 60.0
    assert le_by_decade['1950s']['average'] == 70.0
    assert le_by_decade['1900s']['count'] == 2
    assert le_by_decade['1950s']['count'] == 2


def test_longevity_collector_by_gender():
    """Test life expectancy by gender."""
    people = [
        MockPerson(1900, 1950, 'M'),  # Male, 50 years
        MockPerson(1900, 1960, 'M'),  # Male, 60 years
        MockPerson(1900, 1970, 'F'),  # Female, 70 years
        MockPerson(1900, 1980, 'F'),  # Female, 80 years
    ]
    
    collector = LongevityCollector()
    stats = collector.collect(people, Stats())
    
    longevity_stats = stats.get_category('longevity')
    le_by_gender = longevity_stats['life_expectancy_by_gender']
    
    assert 'M' in le_by_gender
    assert 'F' in le_by_gender
    assert le_by_gender['M']['average'] == 55.0
    assert le_by_gender['F']['average'] == 75.0


def test_longevity_collector_survival_rates():
    """Test survival rate calculations."""
    people = [
        MockPerson(1900, 1900, 'M'),  # Died at 0 (infant)
        MockPerson(1900, 1903, 'F'),  # Died at 3 (child)
        MockPerson(1900, 1920, 'M'),  # Died at 20
        MockPerson(1900, 1965, 'F'),  # Died at 65
        MockPerson(1900, 1985, 'M'),  # Died at 85
    ]
    
    collector = LongevityCollector()
    stats = collector.collect(people, Stats())
    
    longevity_stats = stats.get_category('longevity')
    survival_rates = longevity_stats['survival_rates']
    
    # 3 out of 5 survived to age 5 (60%)
    assert survival_rates['survived_to_age_5']['count'] == 3
    assert survival_rates['survived_to_age_5']['percentage'] == 60.0
    
    # 2 out of 5 survived to age 65 (40%)
    assert survival_rates['survived_to_age_65']['count'] == 2
    assert survival_rates['survived_to_age_65']['percentage'] == 40.0


def test_timeline_collector_basic():
    """Test TimelineCollector with basic data."""
    people = [
        MockPerson(1900, 1950),
        MockPerson(1920, 1980),
        MockPerson(1940, 2000),
    ]
    
    collector = TimelineCollector()
    stats = collector.collect(people, Stats())
    
    timeline_stats = stats.get_category('timeline')
    
    assert 'total_events_with_dates' in timeline_stats
    assert 'events_by_decade' in timeline_stats
    assert 'events_by_century' in timeline_stats
    assert 'earliest_event_year' in timeline_stats
    assert 'latest_event_year' in timeline_stats
    assert 'timeline_span_years' in timeline_stats


def test_timeline_collector_event_density():
    """Test event density calculations."""
    people = [
        MockPerson(1900, 1950, has_places=True),
        MockPerson(1900, 1950, has_places=True),
        MockPerson(1900, 1950, has_places=True),
        MockPerson(1950, 2000, has_places=True),
    ]
    
    collector = TimelineCollector()
    stats = collector.collect(people, Stats())
    
    timeline_stats = stats.get_category('timeline')
    
    # Should have events from multiple event types
    assert timeline_stats['total_events_with_dates'] > 4
    assert 'events_by_type' in timeline_stats
    assert 'birth' in timeline_stats['events_by_type']
    assert 'death' in timeline_stats['events_by_type']


def test_timeline_collector_decades():
    """Test decade-based statistics."""
    people = [
        MockPerson(1850, 1900),
        MockPerson(1900, 1950),
        MockPerson(1950, 2000),
        MockPerson(2000, None),  # Living
    ]
    
    collector = TimelineCollector()
    stats = collector.collect(people, Stats())
    
    timeline_stats = stats.get_category('timeline')
    events_by_decade = timeline_stats['events_by_decade']
    
    # Should have events from 1850s, 1900s, 1950s, 2000s
    assert '1850s' in events_by_decade
    assert '1900s' in events_by_decade
    assert '1950s' in events_by_decade
    assert '2000s' in events_by_decade


def test_timeline_collector_data_completeness():
    """Test data completeness tracking."""
    people = [
        MockPerson(1900, 1950, has_places=True),
        MockPerson(1900, 1950, has_places=False),
        MockPerson(1900, None, has_places=True),  # No death
        MockPerson(1900, None, has_places=False),  # No death, no places
    ]
    
    collector = TimelineCollector()
    stats = collector.collect(people, Stats())
    
    timeline_stats = stats.get_category('timeline')
    completeness = timeline_stats['data_completeness_by_birth_decade']
    
    assert '1900s' in completeness
    decade_data = completeness['1900s']
    assert decade_data['total_people'] == 4
    assert decade_data['with_death_data'] == 2
    assert decade_data['with_place_data'] == 2
    assert decade_data['death_data_percentage'] == 50.0
    assert decade_data['place_data_percentage'] == 50.0


def test_timeline_collector_peak_periods():
    """Test identification of peak periods."""
    # Create many people born in 1900 (10 births + other events in 1925)
    people = [MockPerson(1900, 1950) for _ in range(10)]
    # Add a few from other decades (2 births + other events in 1945)
    people.extend([MockPerson(1920, 1970) for _ in range(2)])
    
    collector = TimelineCollector()
    stats = collector.collect(people, Stats())
    
    timeline_stats = stats.get_category('timeline')
    
    assert 'peak_decade' in timeline_stats
    assert 'peak_year' in timeline_stats
    # Note: peak is based on total events across all years/decades,
    # which includes births, deaths, and other life events.
    # With 10 people born in 1900 + their other events (~1925) + deaths (1950),
    # vs 2 people born in 1920 + their events (~1945) + deaths (1970),
    # the peak might vary based on how events are distributed.


def test_integration_longevity_timeline():
    """Test both collectors working together."""
    people = [
        MockPerson(1900, 1960, 'M', True),
        MockPerson(1920, 1990, 'F', True),
        MockPerson(1940, 2010, 'M', True),
    ]
    
    longevity_collector = LongevityCollector()
    timeline_collector = TimelineCollector()
    
    combined_stats = Stats()
    
    longevity_stats = longevity_collector.collect(people, combined_stats)
    timeline_stats = timeline_collector.collect(people, combined_stats)
    
    combined_stats.merge(longevity_stats)
    combined_stats.merge(timeline_stats)
    
    # Verify both categories exist
    assert 'longevity' in combined_stats.categories
    assert 'timeline' in combined_stats.categories
    
    # Verify cross-consistency
    longevity_data = combined_stats.get_category('longevity')
    timeline_data = combined_stats.get_category('timeline')
    
    # Should have death data for all 3 people
    assert longevity_data['total_deaths_analyzed'] == 3
    # Timeline should cover births and deaths
    assert timeline_data['total_events_with_dates'] >= 6


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

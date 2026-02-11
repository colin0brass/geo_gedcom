"""
Unit tests for demographic statistics collectors.

Tests collectors that gather demographic and personal information:
- GenderCollector: Gender distribution and name analysis by gender
- NamesCollector: Name frequency and diversity analysis
- AgesCollector: Age distribution and lifespan statistics
- BirthsCollector: Birth patterns, zodiac signs, and temporal trends
"""
import pytest
from datetime import date as _date

from geo_gedcom.statistics.collectors.gender import GenderCollector
from geo_gedcom.statistics.collectors.names import NamesCollector
from geo_gedcom.statistics.collectors.ages import AgesCollector
from geo_gedcom.statistics.collectors.births import BirthsCollector
from geo_gedcom.statistics.model import Stats


# Mock classes for testing
class MockDate:
    """Mock GedcomDate with year_num property."""
    def __init__(self, year, month=None, day=None):
        self.year_num = year
        self.year = year
        self.month = month
        self.day = day


class MockEvent:
    """Mock LifeEvent with date."""
    def __init__(self, year=None, month=None, day=None):
        self.date = MockDate(year, month, day) if year is not None else None


class MockPerson:
    """Mock Person for testing."""
    def __init__(self, name='John /Smith/', sex='M', birth_year=1950, 
                 birth_month=None, birth_day=None, death_year=None):
        self.name = name
        self.sex = sex
        self.firstname = name.split('/')[0].strip() if '/' in name else name.split()[0]
        self._birth_year = birth_year
        self._birth_month = birth_month
        self._birth_day = birth_day
        self._death_year = death_year
    
    def get_event(self, event_type):
        if event_type == 'birth' and self._birth_year:
            return MockEvent(self._birth_year, self._birth_month, self._birth_day)
        elif event_type == 'death' and self._death_year:
            return MockEvent(self._death_year)
        return None


def test_gender_collector():
    """Test GenderCollector."""
    people = [
        MockPerson('John /Smith/', 'M', 1950),
        MockPerson('Jane /Doe/', 'F', 1955),
        MockPerson('Bob /Johnson/', 'M', 1960, death_year=2020),
        MockPerson('Alice /Williams/', 'F', 1965, death_year=2015),
        MockPerson('Unknown /Person/', None, 1970),
    ]
    
    collector = GenderCollector()
    stats = collector.collect(people, Stats())
    
    gender_stats = stats.get_category('gender')
    
    assert gender_stats['male'] == 2
    assert gender_stats['female'] == 2
    assert gender_stats['unknown'] == 1
    assert gender_stats['total'] == 5
    assert 'most_common_male_names' in gender_stats
    assert 'most_common_female_names' in gender_stats


def test_names_collector():
    """Test NamesCollector."""
    people = [
        MockPerson('John William /Smith/', 'M', 1950),
        MockPerson('Jane Marie /Doe/', 'F', 1955),
        MockPerson('John Robert /Johnson/', 'M', 1960),
        MockPerson('Alice /Williams/', 'F', 1965),
    ]
    
    collector = NamesCollector()
    stats = collector.collect(people, Stats())
    
    names_stats = stats.get_category('names')
    
    assert 'most_common_first_names' in names_stats
    assert names_stats['most_common_first_names']['John'] == 2
    assert 'most_common_middle_names' in names_stats
    assert 'unique_first_names' in names_stats


def test_ages_collector():
    """Test AgesCollector."""
    current_year = _date.today().year
    
    people = [
        MockPerson('Young /Person/', 'M', current_year - 25),  # 25 years old
        MockPerson('Middle /Age/', 'F', current_year - 50),    # 50 years old
        MockPerson('Old /Person/', 'M', current_year - 80),    # 80 years old
        MockPerson('Deceased /One/', 'F', 1950, death_year=2020),  # Lived 70 years
        MockPerson('Deceased /Two/', 'M', 1940, death_year=2010),  # Lived 70 years
    ]
    
    collector = AgesCollector()
    stats = collector.collect(people, Stats())
    
    ages_stats = stats.get_category('ages')
    
    assert 'living_people_count' in ages_stats
    assert ages_stats['living_people_count'] == 3
    assert 'average_age_living' in ages_stats
    assert 'oldest_living_people' in ages_stats
    assert 'youngest_living_people' in ages_stats
    assert 'deceased_people_count' in ages_stats


def test_births_collector():
    """Test BirthsCollector."""
    people = [
        MockPerson('Jan /Person/', 'M', 1950, birth_month=1, birth_day=15),
        MockPerson('Feb /Person/', 'F', 1955, birth_month=2, birth_day=20),
        MockPerson('Mar /Person/', 'M', 1960, birth_month=3, birth_day=21),  # Aries
        MockPerson('Jul /Person/', 'F', 1965, birth_month=7, birth_day=23),  # Leo
        MockPerson('No Month /Person/', 'M', 1970),  # No month
    ]
    
    collector = BirthsCollector()
    stats = collector.collect(people, Stats())
    
    births_stats = stats.get_category('births')
    
    assert 'birth_months' in births_stats
    assert 'birth_decades' in births_stats
    assert 'birth_centuries' in births_stats
    assert 'zodiac_signs' in births_stats
    assert 'birth_seasons' in births_stats
    assert births_stats['earliest_birth_year'] == 1950
    assert births_stats['latest_birth_year'] == 1970


def test_births_collector_filters_implausible_dates():
    """Test BirthsCollector filters out implausibly early dates."""
    people = [
        MockPerson('Ancient /Person/', 'M', 1),  # Year 1 AD - should be filtered
        MockPerson('Medieval /Person/', 'F', 800),  # Year 800 - should be filtered
        MockPerson('Recent /Person/', 'M', 1800),  # Year 1800 - should be kept
        MockPerson('Modern /Person/', 'F', 1950),  # Year 1950 - should be kept
    ]
    
    collector = BirthsCollector()
    stats = collector.collect(people, Stats())
    
    births_stats = stats.get_category('births')
    
    # earliest_birth_year should be 1800 (filtered out 1 and 800)
    assert births_stats['earliest_birth_year'] == 1800
    # latest_birth_year should still include all dates
    assert births_stats['latest_birth_year'] == 1950


def test_births_collector_no_credible_dates():
    """Test BirthsCollector when all dates are implausible."""
    people = [
        MockPerson('Ancient /One/', 'M', 1),  # Year 1 AD
        MockPerson('Ancient /Two/', 'F', 500),  # Year 500
    ]
    
    collector = BirthsCollector()
    stats = collector.collect(people, Stats())
    
    births_stats = stats.get_category('births')
    
    # Should not have earliest_birth_year key if all dates filtered
    assert 'earliest_birth_year' not in births_stats
    # Should still have latest_birth_year
    assert births_stats['latest_birth_year'] == 500


def test_births_collector_custom_threshold():
    """Test BirthsCollector with custom earliest_credible_birth_year threshold."""
    people = [
        MockPerson('Medieval /Person/', 'M', 800),   # Year 800
        MockPerson('Renaissance /Person/', 'F', 1400),  # Year 1400
        MockPerson('Modern /Person/', 'M', 1900),    # Year 1900
    ]
    
    # Test with threshold of 1500 (should filter out 800 and 1400)
    collector = BirthsCollector(earliest_credible_birth_year=1500)
    stats = collector.collect(people, Stats())
    births_stats = stats.get_category('births')
    
    assert births_stats['earliest_birth_year'] == 1900
    assert births_stats['latest_birth_year'] == 1900
    
    # Test with threshold of 500 (should only filter out dates before 500)
    collector_500 = BirthsCollector(earliest_credible_birth_year=500)
    stats_500 = collector_500.collect(people, Stats())
    births_stats_500 = stats_500.get_category('births')
    
    assert births_stats_500['earliest_birth_year'] == 800
    assert births_stats_500['latest_birth_year'] == 1900


def test_all_collectors_integration():
    """Test all collectors together."""
    people = [
        MockPerson('John William /Smith/', 'M', 1950, birth_month=6, birth_day=15, death_year=2020),
        MockPerson('Jane Marie /Doe/', 'F', 1955, birth_month=12, birth_day=25),
        MockPerson('Bob /Johnson/', 'M', 1960, birth_month=3, birth_day=21),
    ]
    
    collectors = [
        GenderCollector(),
        NamesCollector(),
        AgesCollector(),
        BirthsCollector(),
    ]
    
    combined_stats = Stats()
    for collector in collectors:
        stats = collector.collect(people, combined_stats)
        combined_stats.merge(stats)
    
    # Verify we have data from all collectors
    assert 'gender' in combined_stats.categories
    assert 'names' in combined_stats.categories
    assert 'ages' in combined_stats.categories
    assert 'births' in combined_stats.categories
    
    # Verify some cross-collector consistency
    gender_total = combined_stats.get_value('gender', 'total')
    assert gender_total == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

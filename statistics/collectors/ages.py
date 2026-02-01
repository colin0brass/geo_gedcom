"""
Age statistics collector.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date as _date
import logging
from typing import Any, Iterable, Optional, List, Tuple

from geo_gedcom.statistics.base import StatisticsCollector, register_collector
from geo_gedcom.statistics.model import Stats
from geo_gedcom.enrichment.date_utils import year_num

logger = logging.getLogger(__name__)


@register_collector
@dataclass
class AgesCollector(StatisticsCollector):
    """
    Collects age-related statistics from the dataset.
    
    Statistics collected:
        - Age distribution for living people
        - Oldest and youngest living people
        - Life expectancy statistics (from demographics)
        - Age at death distribution
        - Lifespan categories
    """
    collector_id: str = "ages"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats, collector_num: int = None, total_collectors: int = None) -> Stats:
        """Collect age statistics."""
        stats = Stats()
        
        # Convert to list for progress tracking
        people_list = list(people)
        total_people = len(people_list)
        
        # Build collector prefix
        prefix = f"Statistics ({collector_num}/{total_collectors}): " if collector_num and total_collectors else "Statistics: "
        
        # Set up progress tracking
        self._report_step(info=f"{prefix}Analyzing ages", target=total_people, reset_counter=True, plus_step=0)
        
        current_year = _date.today().year
        
        living_ages = []
        living_people_info = []  # (age, name, birth_year)
        
        deceased_ages_at_death = []
        lifespans = []
        lifespan_people = []  # (lifespan, name, birth_year, death_year)
        
        for idx, person in enumerate(people_list):
            # Check for stop request and report progress every 100 people
            if idx % 100 == 0:
                if self._stop_requested("Ages collection stopped"):
                    break
                self._report_step(plus_step=100)
            birth_year = self._get_birth_year(person)
            death_year = self._get_death_year(person)
            is_deceased = self._is_deceased(person)
            name = self._get_name(person)
            
            if birth_year:
                if is_deceased:
                    if death_year:
                        # Calculate age at death
                        age_at_death = death_year - birth_year
                        if 0 <= age_at_death <= 120:
                            deceased_ages_at_death.append(age_at_death)
                            lifespans.append(age_at_death)
                            lifespan_people.append((age_at_death, name, birth_year, death_year))
                else:
                    # Living person - calculate current age
                    age = current_year - birth_year
                    if 0 <= age <= 120:
                        living_ages.append(age)
                        living_people_info.append((age, name, birth_year))
        
        # Living people statistics
        if living_ages:
            stats.add_value('ages', 'living_people_count', len(living_ages))
            stats.add_value('ages', 'average_age_living', round(sum(living_ages) / len(living_ages), 1))
            stats.add_value('ages', 'median_age_living', self._median(living_ages))
            stats.add_value('ages', 'youngest_living_age', min(living_ages))
            stats.add_value('ages', 'oldest_living_age', max(living_ages))
            
            # Age distribution
            age_distribution = Counter(living_ages)
            stats.add_value('ages', 'living_age_distribution', dict(sorted(age_distribution.items())))
            
            # Age ranges
            age_ranges = self._categorize_ages(living_ages)
            stats.add_value('ages', 'living_age_ranges', age_ranges)
            
            # Oldest living people (top 10)
            oldest_living = sorted(living_people_info, key=lambda x: x[0], reverse=True)[:10]
            stats.add_value('ages', 'oldest_living_people', [
                {'name': name, 'age': age, 'birth_year': birth_year}
                for age, name, birth_year in oldest_living
            ])
            
            # Youngest living people (top 10)
            youngest_living = sorted(living_people_info, key=lambda x: x[0])[:10]
            stats.add_value('ages', 'youngest_living_people', [
                {'name': name, 'age': age, 'birth_year': birth_year}
                for age, name, birth_year in youngest_living
            ])
        
        # Age at death statistics
        if deceased_ages_at_death:
            stats.add_value('ages', 'deceased_people_count', len(deceased_ages_at_death))
            stats.add_value('ages', 'average_age_at_death', round(sum(deceased_ages_at_death) / len(deceased_ages_at_death), 1))
            stats.add_value('ages', 'median_age_at_death', self._median(deceased_ages_at_death))
            
            # Age at death distribution
            age_at_death_distribution = Counter(deceased_ages_at_death)
            stats.add_value('ages', 'age_at_death_distribution', dict(sorted(age_at_death_distribution.items())))
            
            # Age at death ranges
            age_at_death_ranges = self._categorize_ages(deceased_ages_at_death)
            stats.add_value('ages', 'age_at_death_ranges', age_at_death_ranges)
        
        # Lifespan statistics
        if lifespans:
            # People who lived the longest
            longest_lived = sorted(lifespan_people, key=lambda x: x[0], reverse=True)[:10]
            stats.add_value('ages', 'lived_longest', [
                {'name': name, 'lifespan': lifespan, 'birth_year': birth_year, 'death_year': death_year}
                for lifespan, name, birth_year, death_year in longest_lived
            ])
            
            # People who lived the shortest (filter out infant deaths < 1 year)
            adult_deaths = [(ls, n, b, d) for ls, n, b, d in lifespan_people if ls >= 10]
            if adult_deaths:
                shortest_lived = sorted(adult_deaths, key=lambda x: x[0])[:10]
                stats.add_value('ages', 'lived_shortest', [
                    {'name': name, 'lifespan': lifespan, 'birth_year': birth_year, 'death_year': death_year}
                    for lifespan, name, birth_year, death_year in shortest_lived
                ])
        
        logger.info(f"Ages: {len(living_ages)} living, {len(deceased_ages_at_death)} deceased with age data")
        
        return stats
    
    def _get_birth_year(self, person: Any) -> Optional[int]:
        """Extract birth year from person."""
        if hasattr(person, 'get_event_date'):
            birth_date = person.get_event_date('birth')
            if birth_date:
                return year_num(birth_date)
        
        if hasattr(person, 'get_event'):
            birth = person.get_event('birth')
            if birth and birth.date:
                return year_num(birth.date)
        
        return None
    
    def _get_death_year(self, person: Any) -> Optional[int]:
        """Extract death year from person."""
        if hasattr(person, 'get_event_date'):
            death_date = person.get_event_date('death')
            if death_date:
                return year_num(death_date)
            burial_date = person.get_event_date('burial')
            if burial_date:
                return year_num(burial_date)
        
        if hasattr(person, 'get_event'):
            death = person.get_event('death')
            if death and death.date:
                return year_num(death.date)
            burial = person.get_event('burial')
            if burial and burial.date:
                return year_num(burial.date)
        
        return None
    
    def _is_deceased(self, person: Any) -> bool:
        """Check if person is deceased."""
        if hasattr(person, 'is_deceased'):
            return person.is_deceased()
        
        if hasattr(person, 'has_event'):
            return person.has_event('death') or person.has_event('burial')
        
        if hasattr(person, 'get_event'):
            death = person.get_event('death')
            burial = person.get_event('burial')
            return death is not None or burial is not None
        
        return False
    
    def _get_name(self, person: Any) -> str:
        """Get person's name."""
        name = getattr(person, 'name', None) or getattr(person, 'display_name', None)
        if name:
            # Clean GEDCOM format
            return name.replace('/', '').strip()
        return 'Unknown'
    
    def _median(self, values: List[int]) -> float:
        """Calculate median of a list of values."""
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            return sorted_values[n // 2]
    
    def _categorize_ages(self, ages: List[int]) -> dict:
        """
        Categorize ages into ranges.
        
        Returns:
            Dictionary with age range labels and counts
        """
        ranges = {
            '0-9': 0,
            '10-19': 0,
            '20-29': 0,
            '30-39': 0,
            '40-49': 0,
            '50-59': 0,
            '60-69': 0,
            '70-79': 0,
            '80-89': 0,
            '90-99': 0,
            '100+': 0
        }
        
        for age in ages:
            if age < 10:
                ranges['0-9'] += 1
            elif age < 20:
                ranges['10-19'] += 1
            elif age < 30:
                ranges['20-29'] += 1
            elif age < 40:
                ranges['30-39'] += 1
            elif age < 50:
                ranges['40-49'] += 1
            elif age < 60:
                ranges['50-59'] += 1
            elif age < 70:
                ranges['60-69'] += 1
            elif age < 80:
                ranges['70-79'] += 1
            elif age < 90:
                ranges['80-89'] += 1
            elif age < 100:
                ranges['90-99'] += 1
            else:
                ranges['100+'] += 1
        
        return ranges

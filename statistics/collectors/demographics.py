"""
Demographics statistics collector.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date as _date
import logging
from typing import Any, Iterable, List, Optional

from geo_gedcom.statistics.base import StatisticsCollector, register_collector
from geo_gedcom.statistics.model import Stats
from geo_gedcom.enrichment.date_utils import year_num

logger = logging.getLogger(__name__)


@register_collector
@dataclass
class DemographicsCollector(StatisticsCollector):
    """
    Collects demographic statistics from the dataset.
    
    Statistics collected:
        - Total people count
        - Living vs deceased counts
        - Birth year distribution
        - Death year distribution
        - Average lifespan
        - Most common surnames
    """
    collector_id: str = "demographics"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats, collector_num: int = None, total_collectors: int = None) -> Stats:
        """Collect demographic statistics."""
        stats = Stats()
        
        # Convert to list for counting and progress tracking
        people_list = list(people)
        total_people = len(people_list)
        
        total_count = 0
        living_count = 0
        deceased_count = 0
        
        birth_years = []
        death_years = []
        lifespans = []
        surnames = []
        
        # Build collector prefix
        prefix = f"Statistics ({collector_num}/{total_collectors}): " if collector_num and total_collectors else "Statistics: "
        
        # Set up progress tracking
        self._report_step(info=f"{prefix}Analyzing demographics", target=total_people, reset_counter=True, plus_step=0)
        
        for idx, person in enumerate(people_list):
            # Check for stop request every 100 people
            if idx % 100 == 0:
                if self._stop_requested("Demographics collection stopped"):
                    logger.info(f"Demographics stopped after {idx} people")
                    break
                self._report_step(plus_step=100)
            
            total_count += 1
            
            # Check if person is deceased
            is_deceased = self._is_deceased(person)
            if is_deceased:
                deceased_count += 1
            else:
                living_count += 1
            
            # Birth year
            birth_year = self._get_birth_year(person)
            if birth_year:
                birth_years.append(birth_year)
            
            # Death year
            death_year = self._get_death_year(person)
            if death_year:
                death_years.append(death_year)
            
            # Lifespan
            if birth_year and death_year:
                lifespan = death_year - birth_year
                if 0 <= lifespan <= 120:  # Sanity check
                    lifespans.append(lifespan)
            
            # Surname
            surname = self._get_surname(person)
            if surname:
                surnames.append(surname)
        
        # Add basic counts
        stats.add_value('demographics', 'total_people', total_count)
        stats.add_value('demographics', 'living', living_count)
        stats.add_value('demographics', 'deceased', deceased_count)
        
        # Birth year statistics
        if birth_years:
            birth_year_dist = Counter(birth_years)
            stats.add_value('demographics', 'birth_year_distribution', dict(birth_year_dist.most_common(50)))
            stats.add_value('demographics', 'earliest_birth_year', min(birth_years))
            stats.add_value('demographics', 'latest_birth_year', max(birth_years))
            stats.add_value('demographics', 'people_with_birth_year', len(birth_years))
        
        # Death year statistics
        if death_years:
            death_year_dist = Counter(death_years)
            stats.add_value('demographics', 'death_year_distribution', dict(death_year_dist.most_common(50)))
            stats.add_value('demographics', 'earliest_death_year', min(death_years))
            stats.add_value('demographics', 'latest_death_year', max(death_years))
            stats.add_value('demographics', 'people_with_death_year', len(death_years))
        
        # Lifespan statistics
        if lifespans:
            avg_lifespan = sum(lifespans) / len(lifespans)
            stats.add_value('demographics', 'average_lifespan', round(avg_lifespan, 1))
            stats.add_value('demographics', 'min_lifespan', min(lifespans))
            stats.add_value('demographics', 'max_lifespan', max(lifespans))
            stats.add_value('demographics', 'median_lifespan', self._median(lifespans))
        
        # Surname statistics
        if surnames:
            surname_counts = Counter(surnames)
            stats.add_value('demographics', 'unique_surnames', len(surname_counts))
            stats.add_value('demographics', 'most_common_surnames', dict(surname_counts.most_common(20)))
        
        logger.info(f"Demographics: {total_count} people, {living_count} living, {deceased_count} deceased")
        
        return stats
    
    def _is_deceased(self, person: Any) -> bool:
        """
        Check if person is deceased.
        
        Checks multiple sources:
        1. EnrichedPerson.is_deceased() method
        2. Person.has_event() for 'death' or 'burial'
        3. Person.get_event() for death/burial events
        
        Args:
            person: Person or EnrichedPerson object
            
        Returns:
            True if person is deceased, False otherwise
        """
        # Check for EnrichedPerson
        if hasattr(person, 'is_deceased'):
            return person.is_deceased()
        
        # Check for death event
        if hasattr(person, 'has_event'):
            return person.has_event('death') or person.has_event('burial')
        
        # Check for death attribute
        if hasattr(person, 'get_event'):
            death = person.get_event('death')
            burial = person.get_event('burial')
            return death is not None or burial is not None
        
        return False
    
    def _get_birth_year(self, person: Any) -> Optional[int]:
        """
        Extract birth year from person.
        
        Tries multiple approaches:
        1. EnrichedPerson.get_event_date('birth')
        2. Person.get_event('birth').date
        
        Args:
            person: Person or EnrichedPerson object
            
        Returns:
            Birth year as integer, or None if not available
        """
        # Try EnrichedPerson method
        if hasattr(person, 'get_event_date'):
            birth_date = person.get_event_date('birth')
            if birth_date:
                return year_num(birth_date)
        
        # Try Person.get_event
        if hasattr(person, 'get_event'):
            birth = person.get_event('birth')
            if birth and birth.date:
                return year_num(birth.date)
        
        return None
    
    def _get_death_year(self, person: Any) -> Optional[int]:
        """
        Extract death year from person.
        
        Tries death event first, falls back to burial if death not available.
        Works with both EnrichedPerson and Person objects.
        
        Args:
            person: Person or EnrichedPerson object
            
        Returns:
            Death year as integer, or None if not available
        """
        # Try EnrichedPerson method
        if hasattr(person, 'get_event_date'):
            death_date = person.get_event_date('death')
            if death_date:
                return year_num(death_date)
            burial_date = person.get_event_date('burial')
            if burial_date:
                return year_num(burial_date)
        
        # Try Person.get_event
        if hasattr(person, 'get_event'):
            death = person.get_event('death')
            if death and death.date:
                return year_num(death.date)
            burial = person.get_event('burial')
            if burial and burial.date:
                return year_num(burial.date)
        
        return None
    
    def _get_surname(self, person: Any) -> Optional[str]:
        """
        Extract surname from person name.
        
        Handles two formats:
        1. GEDCOM format: "FirstName /Surname/"
        2. Space-separated: "FirstName Surname" (takes last word)
        
        Args:
            person: Person or EnrichedPerson object
            
        Returns:
            Surname string, or None if not extractable
        """
        name = getattr(person, 'name', None) or getattr(person, 'display_name', None)
        if not name:
            return None
        
        # Handle GEDCOM format: "FirstName /Surname/"
        if '/' in name:
            parts = name.split('/')
            if len(parts) >= 2:
                return parts[1].strip()
        
        # Handle space-separated format
        parts = name.split()
        if len(parts) >= 2:
            return parts[-1]
        
        return None
    
    def _median(self, values: List[int]) -> float:
        """
        Calculate median of a list of values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Median value (average of two middle values if even length)
        """
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            return sorted_values[n // 2]

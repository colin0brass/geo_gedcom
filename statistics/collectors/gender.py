"""
Gender statistics collector.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import logging
from typing import Any, Iterable, Optional

from geo_gedcom.statistics.base import StatisticsCollector, register_collector
from geo_gedcom.statistics.model import Stats

logger = logging.getLogger(__name__)


@register_collector
@dataclass
class GenderCollector(StatisticsCollector):
    """
    Collects gender statistics from the dataset.
    
    Statistics collected:
        - Gender distribution (Male/Female/Unknown)
        - Most common first names by gender
        - Living vs deceased by gender
    """
    collector_id: str = "gender"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats) -> Stats:
        """Collect gender statistics."""
        stats = Stats()
        
        male_count = 0
        female_count = 0
        unknown_count = 0
        
        male_first_names = []
        female_first_names = []
        
        male_living = 0
        male_deceased = 0
        female_living = 0
        female_deceased = 0
        
        for person in people:
            sex = self._get_sex(person)
            
            if sex == 'M':
                male_count += 1
                # Get first name
                first_name = self._get_first_name(person)
                if first_name:
                    male_first_names.append(first_name)
                # Check if deceased
                if self._is_deceased(person):
                    male_deceased += 1
                else:
                    male_living += 1
                    
            elif sex == 'F':
                female_count += 1
                # Get first name
                first_name = self._get_first_name(person)
                if first_name:
                    female_first_names.append(first_name)
                # Check if deceased
                if self._is_deceased(person):
                    female_deceased += 1
                else:
                    female_living += 1
            else:
                unknown_count += 1
        
        total = male_count + female_count + unknown_count
        
        # Add gender distribution
        stats.add_value('gender', 'male', male_count)
        stats.add_value('gender', 'female', female_count)
        stats.add_value('gender', 'unknown', unknown_count)
        stats.add_value('gender', 'total', total)
        
        if total > 0:
            stats.add_value('gender', 'male_percentage', round(100 * male_count / total, 1))
            stats.add_value('gender', 'female_percentage', round(100 * female_count / total, 1))
            stats.add_value('gender', 'unknown_percentage', round(100 * unknown_count / total, 1))
        
        # Most common first names by gender
        if male_first_names:
            male_name_counts = Counter(male_first_names)
            stats.add_value('gender', 'most_common_male_names', dict(male_name_counts.most_common(20)))
        
        if female_first_names:
            female_name_counts = Counter(female_first_names)
            stats.add_value('gender', 'most_common_female_names', dict(female_name_counts.most_common(20)))
        
        # Living vs deceased by gender
        stats.add_value('gender', 'male_living', male_living)
        stats.add_value('gender', 'male_deceased', male_deceased)
        stats.add_value('gender', 'female_living', female_living)
        stats.add_value('gender', 'female_deceased', female_deceased)
        
        logger.info(f"Gender: {male_count} male, {female_count} female, {unknown_count} unknown")
        
        return stats
    
    def _get_sex(self, person: Any) -> Optional[str]:
        """
        Get sex/gender from person.
        
        Args:
            person: Person or EnrichedPerson object
            
        Returns:
            'M', 'F', or None
        """
        return getattr(person, 'sex', None)
    
    def _get_first_name(self, person: Any) -> Optional[str]:
        """
        Extract first name from person.
        
        Args:
            person: Person or EnrichedPerson object
            
        Returns:
            First name string, or None if not available
        """
        # Try firstname attribute first
        firstname = getattr(person, 'firstname', None)
        if firstname and firstname != 'Unknown':
            return firstname
        
        # Fall back to parsing name
        name = getattr(person, 'name', None) or getattr(person, 'display_name', None)
        if not name or name == 'Unknown':
            return None
        
        # Handle GEDCOM format: "FirstName /Surname/"
        if '/' in name:
            parts = name.split('/')
            if len(parts) >= 1 and parts[0].strip():
                first_part = parts[0].strip()
                # Take first word only
                return first_part.split()[0] if first_part else None
        
        # Handle space-separated format
        parts = name.split()
        if parts:
            return parts[0]
        
        return None
    
    def _is_deceased(self, person: Any) -> bool:
        """
        Check if person is deceased.
        
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

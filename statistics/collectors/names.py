"""
Name statistics collector.
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
class NamesCollector(StatisticsCollector):
    """
    Collects name statistics from the dataset.
    
    Statistics collected:
        - Most common first names (overall)
        - Most common middle names
        - Unique name counts
        - Name diversity metrics
    """
    collector_id: str = "names"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats) -> Stats:
        """Collect name statistics."""
        stats = Stats()
        
        first_names = []
        middle_names = []
        full_names = []
        
        for person in people:
            # Get full name
            full_name = self._get_full_name(person)
            if full_name and full_name != 'Unknown':
                full_names.append(full_name)
            
            # Get first name
            first_name = self._get_first_name(person)
            if first_name and first_name != 'Unknown':
                first_names.append(first_name)
            
            # Get middle names
            middle = self._get_middle_names(person)
            if middle:
                middle_names.extend(middle)
        
        # First name statistics
        if first_names:
            first_name_counts = Counter(first_names)
            stats.add_value('names', 'most_common_first_names', dict(first_name_counts.most_common(30)))
            stats.add_value('names', 'unique_first_names', len(first_name_counts))
            stats.add_value('names', 'total_first_names', len(first_names))
        
        # Middle name statistics
        if middle_names:
            middle_name_counts = Counter(middle_names)
            stats.add_value('names', 'most_common_middle_names', dict(middle_name_counts.most_common(20)))
            stats.add_value('names', 'unique_middle_names', len(middle_name_counts))
            stats.add_value('names', 'people_with_middle_names', len(middle_names))
        
        # Full name statistics
        if full_names:
            stats.add_value('names', 'unique_full_names', len(set(full_names)))
            stats.add_value('names', 'total_full_names', len(full_names))
            
            # Find duplicates
            full_name_counts = Counter(full_names)
            duplicates = {name: count for name, count in full_name_counts.items() if count > 1}
            if duplicates:
                stats.add_value('names', 'duplicate_names', dict(sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:20]))
        
        logger.info(f"Names: {len(first_names)} first names, {len(middle_names)} middle names")
        
        return stats
    
    def _get_full_name(self, person: Any) -> Optional[str]:
        """
        Get full name from person.
        
        Args:
            person: Person or EnrichedPerson object
            
        Returns:
            Full name string, or None if not available
        """
        name = getattr(person, 'name', None) or getattr(person, 'display_name', None)
        if name and name != 'Unknown':
            # Clean GEDCOM format (remove slashes)
            return name.replace('/', '').strip()
        return None
    
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
            # If firstname has multiple words, take just the first
            parts = firstname.split()
            return parts[0] if parts else None
        
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
    
    def _get_middle_names(self, person: Any) -> list[str]:
        """
        Extract middle names from person.
        
        Args:
            person: Person or EnrichedPerson object
            
        Returns:
            List of middle names (may be empty)
        """
        # Try firstname attribute (may contain first + middle)
        firstname = getattr(person, 'firstname', None)
        if firstname and firstname != 'Unknown':
            parts = firstname.split()
            if len(parts) > 1:
                return parts[1:]  # Everything after first name
        
        # Fall back to parsing name
        name = getattr(person, 'name', None) or getattr(person, 'display_name', None)
        if not name or name == 'Unknown':
            return []
        
        # Handle GEDCOM format: "FirstName MiddleName /Surname/"
        if '/' in name:
            parts = name.split('/')
            if len(parts) >= 1 and parts[0].strip():
                name_parts = parts[0].strip().split()
                if len(name_parts) > 1:
                    return name_parts[1:]  # Everything after first name
        
        return []

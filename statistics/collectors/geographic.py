"""
Geographic statistics collector.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import logging
from typing import Any, Iterable, Optional

from geo_gedcom.statistics.base import StatisticsCollector, register_collector
from geo_gedcom.statistics.model import Stats

logger = logging.getLogger(__name__)


@register_collector
@dataclass
class GeographicCollector(StatisticsCollector):
    """
    Collects geographic statistics from the dataset.
    
    Statistics collected:
        - Most common birth places
        - Most common death places
        - Place distribution by event type
        - Country/region distribution
    """
    collector_id: str = "geographic"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats, collector_num: int = None, total_collectors: int = None) -> Stats:
        """Collect geographic statistics."""
        stats = Stats()
        
        # Convert to list for progress tracking
        people_list = list(people)
        total_people = len(people_list)
        
        # Build collector prefix
        prefix = f"Statistics ({collector_num}/{total_collectors}): " if collector_num and total_collectors else "Statistics: "
        
        # Set up progress tracking
        self._report_step(info=f"{prefix}Analyzing geography", target=total_people, reset_counter=True, plus_step=0)
        
        birth_places = []
        death_places = []
        all_places = []
        
        for idx, person in enumerate(people_list):
            # Check for stop request and report progress every 100 people
            if idx % 100 == 0:
                if self._stop_requested("Geographic collection stopped"):
                    break
                self._report_step(plus_step=100)
            # Birth place
            birth_place = self._get_place(person, 'birth')
            if birth_place:
                birth_places.append(birth_place)
                all_places.append(birth_place)
            
            # Death place
            death_place = self._get_place(person, 'death')
            if death_place:
                death_places.append(death_place)
                all_places.append(death_place)
            
            # Burial place
            burial_place = self._get_place(person, 'burial')
            if burial_place:
                all_places.append(burial_place)
        
        # Birth place statistics
        if birth_places:
            birth_place_counts = Counter(birth_places)
            stats.add_value('geographic', 'most_common_birth_places', dict(birth_place_counts.most_common(20)))
            stats.add_value('geographic', 'unique_birth_places', len(birth_place_counts))
        
        # Death place statistics
        if death_places:
            death_place_counts = Counter(death_places)
            stats.add_value('geographic', 'most_common_death_places', dict(death_place_counts.most_common(20)))
            stats.add_value('geographic', 'unique_death_places', len(death_place_counts))
        
        # All places
        if all_places:
            all_place_counts = Counter(all_places)
            stats.add_value('geographic', 'most_common_places', dict(all_place_counts.most_common(30)))
            stats.add_value('geographic', 'unique_places', len(all_place_counts))
            
            # Extract countries (last component of place name)
            countries = [self._extract_country(place) for place in all_places]
            countries = [c for c in countries if c]
            if countries:
                country_counts = Counter(countries)
                stats.add_value('geographic', 'countries', dict(country_counts.most_common(20)))
        
        logger.info(f"Geographic: {len(all_places)} place references across {len(set(all_places))} unique places")
        
        return stats
    
    def _get_place(self, person: Any, event_type: str) -> Optional[str]:
        """
        Get place for an event.
        
        Tries EnrichedPerson.best_place() first, then Person.get_event().place.
        
        Args:
            person: Person or EnrichedPerson object
            event_type: Event type to retrieve place for
            
        Returns:
            Place name if found, None otherwise
        """
        # Try EnrichedPerson
        if hasattr(person, 'best_place'):
            place = person.best_place(event_type)
            if place:
                return place
        
        # Try Person.get_event
        if hasattr(person, 'get_event'):
            event = person.get_event(event_type)
            if event and hasattr(event, 'place') and event.place:
                return event.place
        
        return None
    
    def _extract_country(self, place: str) -> Optional[str]:
        """
        Extract country from place string.
        
        Assumes comma-separated format where the last component is the country.
        Example: "New York, New York, USA" -> "USA"
        
        Args:
            place: Place string (typically comma-separated)
            
        Returns:
            Country name (last component), or None if not extractable
        """
        if not place:
            return None
        
        parts = [p.strip() for p in place.split(',')]
        if parts:
            return parts[-1]  # Last component is typically the country
        
        return None

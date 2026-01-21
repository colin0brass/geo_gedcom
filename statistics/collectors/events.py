"""
Event statistics collector.
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
class EventCompletenessCollector(StatisticsCollector):
    """
    Collects statistics about event data completeness.
    
    Statistics collected:
        - Event type frequencies
        - Completeness rates (with dates, with places)
        - Missing data counts
    """
    collector_id: str = "event_completeness"
    
    COMMON_EVENTS = ['birth', 'death', 'burial', 'baptism', 'marriage', 'christening']
    
    def collect(self, people: Iterable[Any], existing_stats: Stats) -> Stats:
        """Collect event completeness statistics."""
        stats = Stats()
        
        event_counts = Counter()
        events_with_dates = Counter()
        events_with_places = Counter()
        
        people_with_birth = 0
        people_with_death = 0
        people_with_burial = 0
        
        total_people = 0
        
        for person in people:
            total_people += 1
            
            # Check each common event type
            for event_type in self.COMMON_EVENTS:
                event = self._get_event(person, event_type)
                
                if event:
                    event_counts[event_type] += 1
                    
                    if event_type == 'birth':
                        people_with_birth += 1
                    elif event_type == 'death':
                        people_with_death += 1
                    elif event_type == 'burial':
                        people_with_burial += 1
                    
                    # Check for date
                    has_date = self._has_date(event, person, event_type)
                    if has_date:
                        events_with_dates[event_type] += 1
                    
                    # Check for place
                    has_place = self._has_place(event, person, event_type)
                    if has_place:
                        events_with_places[event_type] += 1
        
        # Add event counts
        stats.add_value('events', 'total_people', total_people)
        stats.add_value('events', 'event_counts', dict(event_counts))
        
        # Add completeness statistics
        completeness = {}
        for event_type in self.COMMON_EVENTS:
            count = event_counts.get(event_type, 0)
            if count > 0:
                with_date = events_with_dates.get(event_type, 0)
                with_place = events_with_places.get(event_type, 0)
                
                completeness[event_type] = {
                    'total': count,
                    'with_date': with_date,
                    'with_place': with_place,
                    'date_percentage': round(100 * with_date / count, 1),
                    'place_percentage': round(100 * with_place / count, 1),
                }
        
        stats.add_value('events', 'completeness', completeness)
        
        # Add coverage statistics
        stats.add_value('events', 'people_with_birth', people_with_birth)
        stats.add_value('events', 'people_with_death', people_with_death)
        stats.add_value('events', 'people_with_burial', people_with_burial)
        stats.add_value('events', 'birth_coverage_percentage', round(100 * people_with_birth / total_people, 1))
        stats.add_value('events', 'death_coverage_percentage', round(100 * people_with_death / total_people, 1))
        
        logger.info(f"Events: {sum(event_counts.values())} total events across {len(event_counts)} types")
        
        return stats
    
    def _get_event(self, person: Any, event_type: str) -> Optional[Any]:
        """
        Get an event from a person.
        
        Tries EnrichedPerson.get_explicit_event() first, then Person.get_event().
        For marriage events, retrieves from partnerships/families.
        
        Args:
            person: Person or EnrichedPerson object
            event_type: Event type to retrieve (e.g., 'birth', 'death', 'marriage')
            
        Returns:
            Event object if found, None otherwise
        """
        # Marriage events need special handling
        if event_type == 'marriage':
            # Try to get marriage events from partnerships
            if hasattr(person, 'get_events'):
                marriages = person.get_events('marriage')
                if marriages:
                    marriage_list = marriages if isinstance(marriages, list) else [marriages]
                    if marriage_list:
                        # Return the first marriage's event (we just need to check if any exist)
                        first_marriage = marriage_list[0]
                        # Extract event from Marriage object
                        if hasattr(first_marriage, 'event'):
                            return first_marriage.event
                        return first_marriage
            
            # Try Person.get_event for marriage
            if hasattr(person, 'get_event'):
                marriage = person.get_event('marriage')
                if marriage:
                    # Extract event from Marriage object
                    if hasattr(marriage, 'event'):
                        return marriage.event
                    return marriage
            
            return None
        
        # For non-marriage events, use standard approach
        # Try EnrichedPerson
        if hasattr(person, 'get_explicit_event'):
            return person.get_explicit_event(event_type)
        
        # Try Person
        if hasattr(person, 'get_event'):
            return person.get_event(event_type)
        
        return None
    
    def _has_date(self, event: Any, person: Any, event_type: str) -> bool:
        """
        Check if event has a date.
        
        Checks both the event object's date attribute and EnrichedPerson's get_event_date().
        
        Args:
            event: Event object (may be None)
            person: Person or EnrichedPerson object
            event_type: Event type to check
            
        Returns:
            True if event has a date, False otherwise
        """
        # Check event object
        if event and hasattr(event, 'date') and event.date:
            return True
        
        # Check EnrichedPerson
        if hasattr(person, 'get_event_date'):
            date = person.get_event_date(event_type)
            return date is not None
        
        return False
    
    def _has_place(self, event: Any, person: Any, event_type: str) -> bool:
        """
        Check if event has a place.
        
        Checks both the event object's place attribute and EnrichedPerson's best_place().
        
        Args:
            event: Event object (may be None)
            person: Person or EnrichedPerson object
            event_type: Event type to check
            
        Returns:
            True if event has a place, False otherwise
        """
        # Check event object
        if event and hasattr(event, 'place') and event.place:
            return True
        
        # Check EnrichedPerson
        if hasattr(person, 'best_place'):
            place = person.best_place(event_type)
            return place is not None and place != ""
        
        return False

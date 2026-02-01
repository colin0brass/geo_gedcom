"""
Timeline and event density statistics collector.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import logging
from typing import Any, Iterable, Optional, Dict, List

from geo_gedcom.statistics.base import StatisticsCollector, register_collector
from geo_gedcom.statistics.model import Stats
from geo_gedcom.enrichment.date_utils import year_num

logger = logging.getLogger(__name__)


@register_collector
@dataclass
class TimelineCollector(StatisticsCollector):
    """
    Collects timeline and event density statistics from the dataset.
    
    Statistics collected:
        - Events per decade/century
        - Most "eventful" years
        - Historical period coverage
        - Data completeness trends over time
        - Event type distribution over time
    """
    collector_id: str = "timeline"
    
    # Common event types to track
    EVENT_TYPES = ['birth', 'death', 'burial', 'baptism', 'marriage', 'christening', 'residence']
    
    def collect(self, people: Iterable[Any], existing_stats: Stats, collector_num: int = None, total_collectors: int = None) -> Stats:
        """Collect timeline and event density statistics."""
        stats = Stats()
        
        # Convert to list for progress tracking
        people_list = list(people)
        total_people = len(people_list)
        
        # Build collector prefix
        prefix = f"Statistics ({collector_num}/{total_collectors}): " if collector_num and total_collectors else "Statistics: "
        
        # Set up progress tracking
        self._report_step(info=f"{prefix}Analyzing timeline", target=total_people, reset_counter=True, plus_step=0)
        
        # Event tracking
        events_by_year = Counter()
        events_by_decade = Counter()
        events_by_century = Counter()
        events_by_type_year = defaultdict(Counter)
        events_by_type_decade = defaultdict(Counter)
        
        # Data completeness over time
        people_by_birth_decade = Counter()
        people_with_death_by_birth_decade = Counter()
        people_with_places_by_birth_decade = Counter()
        
        # Year range tracking
        all_years = []
        
        for idx, person in enumerate(people_list):
            # Check for stop request and report progress every 100 people
            if idx % 100 == 0:
                if self._stop_requested("Timeline collection stopped"):
                    break
                self._report_step(plus_step=100)
            birth_year = self._get_birth_year(person)
            
            if birth_year:
                birth_decade = (birth_year // 10) * 10
                people_by_birth_decade[birth_decade] += 1
                
                # Check if has death data
                if self._get_death_year(person):
                    people_with_death_by_birth_decade[birth_decade] += 1
                
                # Check if has place data
                if self._has_place_data(person):
                    people_with_places_by_birth_decade[birth_decade] += 1
            
            # Collect all events and their dates
            for event_type in self.EVENT_TYPES:
                event_year = self._get_event_year(person, event_type)
                
                if event_year:
                    all_years.append(event_year)
                    events_by_year[event_year] += 1
                    
                    decade = (event_year // 10) * 10
                    events_by_decade[decade] += 1
                    
                    century = ((event_year - 1) // 100) + 1
                    events_by_century[century] += 1
                    
                    # Track by type
                    events_by_type_year[event_type][event_year] += 1
                    events_by_type_decade[event_type][decade] += 1
        
        # Events per year statistics
        if events_by_year:
            stats.add_value('timeline', 'total_events_with_dates', sum(events_by_year.values()))
            stats.add_value('timeline', 'years_with_events', len(events_by_year))
            stats.add_value('timeline', 'most_eventful_years', dict(events_by_year.most_common(20)))
            
            # Find peak decade
            peak_year = events_by_year.most_common(1)[0]
            stats.add_value('timeline', 'peak_year', {
                'year': peak_year[0],
                'events': peak_year[1]
            })
        
        # Events per decade
        if events_by_decade:
            decade_data = {f"{decade}s": count for decade, count in sorted(events_by_decade.items())}
            stats.add_value('timeline', 'events_by_decade', decade_data)
            
            # Find peak decade
            peak_decade = events_by_decade.most_common(1)[0]
            stats.add_value('timeline', 'peak_decade', {
                'decade': f"{peak_decade[0]}s",
                'events': peak_decade[1]
            })
        
        # Events per century
        if events_by_century:
            century_data = {self._ordinal(c) + ' century': count 
                          for c, count in sorted(events_by_century.items())}
            stats.add_value('timeline', 'events_by_century', century_data)
        
        # Historical period coverage
        if all_years:
            stats.add_value('timeline', 'earliest_event_year', min(all_years))
            stats.add_value('timeline', 'latest_event_year', max(all_years))
            stats.add_value('timeline', 'timeline_span_years', max(all_years) - min(all_years))
            
            # Decades covered
            decades_covered = len(set((year // 10) * 10 for year in all_years))
            stats.add_value('timeline', 'decades_covered', decades_covered)
            
            # Centuries covered
            centuries_covered = len(set(((year - 1) // 100) + 1 for year in all_years))
            stats.add_value('timeline', 'centuries_covered', centuries_covered)
        
        # Event type distribution over time
        event_type_trends = {}
        for event_type in self.EVENT_TYPES:
            if events_by_type_decade[event_type]:
                decade_counts = {f"{decade}s": count 
                               for decade, count in sorted(events_by_type_decade[event_type].items())}
                event_type_trends[event_type] = {
                    'total': sum(events_by_type_decade[event_type].values()),
                    'by_decade': decade_counts
                }
        
        if event_type_trends:
            stats.add_value('timeline', 'events_by_type', event_type_trends)
        
        # Data completeness trends over time
        if people_by_birth_decade:
            completeness = {}
            for decade in sorted(people_by_birth_decade.keys()):
                total = people_by_birth_decade[decade]
                with_death = people_with_death_by_birth_decade.get(decade, 0)
                with_places = people_with_places_by_birth_decade.get(decade, 0)
                
                completeness[f"{decade}s"] = {
                    'total_people': total,
                    'with_death_data': with_death,
                    'with_place_data': with_places,
                    'death_data_percentage': round(100 * with_death / total, 1) if total > 0 else 0,
                    'place_data_percentage': round(100 * with_places / total, 1) if total > 0 else 0
                }
            
            stats.add_value('timeline', 'data_completeness_by_birth_decade', completeness)
        
        # Event density analysis (events per year on average)
        if all_years and len(all_years) > 0:
            year_span = max(all_years) - min(all_years) + 1
            avg_events_per_year = len(all_years) / year_span
            stats.add_value('timeline', 'average_events_per_year', round(avg_events_per_year, 2))
            
            # Find gaps (years with no events)
            all_years_set = set(all_years)
            year_range = range(min(all_years), max(all_years) + 1)
            gaps = [year for year in year_range if year not in all_years_set]
            
            stats.add_value('timeline', 'years_with_no_events', len(gaps))
            stats.add_value('timeline', 'data_coverage_percentage', 
                          round(100 * len(all_years_set) / year_span, 1))
        
        # Decade activity comparison
        if events_by_decade and len(events_by_decade) >= 2:
            decades = sorted(events_by_decade.keys())
            most_active = max(events_by_decade.items(), key=lambda x: x[1])
            least_active = min(events_by_decade.items(), key=lambda x: x[1])
            
            stats.add_value('timeline', 'most_active_decade', {
                'decade': f"{most_active[0]}s",
                'events': most_active[1]
            })
            stats.add_value('timeline', 'least_active_decade', {
                'decade': f"{least_active[0]}s",
                'events': least_active[1]
            })
        
        logger.info(f"Timeline: {len(all_years)} events across {len(events_by_year)} years")
        
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
        
        if hasattr(person, 'get_event'):
            death = person.get_event('death')
            if death and death.date:
                return year_num(death.date)
        
        return None
    
    def _get_event_year(self, person: Any, event_type: str) -> Optional[int]:
        """
        Extract year from a specific event type.
        
        Args:
            person: Person or EnrichedPerson object
            event_type: Event type to extract year from
            
        Returns:
            Event year as integer, or None if not available
        """
        if hasattr(person, 'get_event_date'):
            event_date = person.get_event_date(event_type)
            if event_date:
                return year_num(event_date)
        
        if hasattr(person, 'get_event'):
            event = person.get_event(event_type)
            if event and hasattr(event, 'date') and event.date:
                return year_num(event.date)
        
        return None
    
    def _has_place_data(self, person: Any) -> bool:
        """
        Check if person has any place data.
        
        Args:
            person: Person or EnrichedPerson object
            
        Returns:
            True if person has place data for any event
        """
        # Check common events for place data
        for event_type in ['birth', 'death', 'burial', 'residence']:
            if hasattr(person, 'best_place'):
                place = person.best_place(event_type)
                if place:
                    return True
            
            if hasattr(person, 'get_event'):
                event = person.get_event(event_type)
                if event and hasattr(event, 'place') and event.place:
                    return True
        
        return False
    
    def _ordinal(self, n: int) -> str:
        """Convert number to ordinal string (1st, 2nd, 3rd, etc.)."""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

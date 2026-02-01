"""
Divorce statistics collector.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date as _date
import logging
from typing import Any, Iterable, Optional, Dict, List

from geo_gedcom.statistics.base import StatisticsCollector, register_collector
from geo_gedcom.statistics.model import Stats
from geo_gedcom.enrichment.date_utils import year_num

logger = logging.getLogger(__name__)


@register_collector
@dataclass
class DivorceCollector(StatisticsCollector):
    """
    Collects divorce statistics from the dataset.
    
    Statistics collected:
        - Number of divorces per person
        - Age at divorce distribution
        - Marriage duration before divorce
        - Divorce trends over time
        - Oldest/youngest when divorced
    """
    collector_id: str = "divorce"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats, collector_num: int = None, total_collectors: int = None) -> Stats:
        """Collect divorce statistics."""
        stats = Stats()
        
        # Convert to list for processing
        people_list = list(people)
        total_people = len(people_list)
        
        # Build collector prefix
        prefix = f"Statistics ({collector_num}/{total_collectors}): " if collector_num and total_collectors else "Statistics: "
        
        # Set up progress tracking
        self._report_step(info=f"{prefix}Analyzing divorces", target=total_people, reset_counter=True, plus_step=0)
        
        # Divorce counts
        divorce_counts = Counter()
        divorces_by_person = defaultdict(int)
        
        # Divorce ages
        divorce_ages_male = []
        divorce_ages_female = []
        all_divorce_ages = []
        divorce_ages_with_info = []  # (age, name, divorce_year)
        
        # Marriage durations before divorce
        marriage_durations = []
        marriage_durations_with_info = []  # (duration, person1_name, person2_name, marriage_year, divorce_year)
        
        # Divorce years
        divorce_years = []
        divorce_decades = Counter()
        divorce_centuries = Counter()
        
        # Track processed divorces to avoid duplicates
        processed_divorces = set()
        
        total_divorces = 0
        people_with_divorces = 0
        
        for idx, person in enumerate(people_list):
            # Check for stop request and report progress every 100 people
            if idx % 100 == 0:
                if self._stop_requested("Divorce collection stopped"):
                    break
                self._report_step(plus_step=100)
            
            person_id = self._get_id(person)
            birth_year = self._get_birth_year(person)
            sex = self._get_sex(person)
            name = self._get_name(person)
            
            # Get divorce events
            divorces = self._get_divorces(person)
            if not divorces:
                continue
            
            divorce_count = len(divorces)
            if divorce_count > 0:
                people_with_divorces += 1
                divorces_by_person[person_id] = divorce_count
                divorce_counts[divorce_count] += 1
            
            for divorce_event in divorces:
                divorce_year = self._get_divorce_year(divorce_event)
                
                # Track divorce years
                if divorce_year:
                    divorce_years.append(divorce_year)
                    decade = (divorce_year // 10) * 10
                    divorce_decades[decade] += 1
                    century = ((divorce_year - 1) // 100) + 1
                    divorce_centuries[century] += 1
                
                # Calculate age at divorce
                if birth_year and divorce_year:
                    age_at_divorce = divorce_year - birth_year
                    if 0 <= age_at_divorce <= 100:
                        all_divorce_ages.append(age_at_divorce)
                        divorce_ages_with_info.append((age_at_divorce, name, divorce_year))
                        if sex == 'M':
                            divorce_ages_male.append(age_at_divorce)
                        elif sex == 'F':
                            divorce_ages_female.append(age_at_divorce)
                
                # Get associated marriage to calculate duration
                # Try to find the marriage event for this person
                marriages = self._get_marriages(person)
                for marriage in marriages:
                    marriage_event = self._get_marriage_event(marriage)
                    marriage_year = self._get_marriage_year(marriage_event) if marriage_event else None
                    
                    # Check if this marriage has the divorce event
                    marriage_divorces = self._get_marriage_divorces(marriage)
                    if divorce_event in marriage_divorces:
                        partner = self._get_partner(marriage, person)
                        if partner and marriage_year and divorce_year:
                            # Create unique divorce ID to avoid duplicates
                            partner_id = self._get_id(partner)
                            divorce_id = tuple(sorted([person_id, partner_id])) + (divorce_year,)
                            
                            if divorce_id not in processed_divorces:
                                processed_divorces.add(divorce_id)
                                total_divorces += 1
                                
                                # Calculate marriage duration
                                duration = divorce_year - marriage_year
                                if duration >= 0:
                                    marriage_durations.append(duration)
                                    partner_name = self._get_name(partner)
                                    marriage_durations_with_info.append((
                                        duration, name, partner_name, marriage_year, divorce_year
                                    ))
        
        # Overall statistics
        stats.add_value('divorce', 'total_divorces', total_divorces)
        stats.add_value('divorce', 'people_with_divorces', people_with_divorces)
        stats.add_value('divorce', 'total_people', len(people_list))
        
        if people_with_divorces > 0:
            divorce_rate = round((people_with_divorces / len(people_list)) * 100, 2)
            stats.add_value('divorce', 'divorce_rate_percentage', divorce_rate)
        
        # Divorce count distribution
        if divorce_counts:
            stats.add_value('divorce', 'divorce_count_distribution', dict(sorted(divorce_counts.items())))
            
            # People who divorced the most
            if divorces_by_person:
                max_divorces = max(divorces_by_person.values())
                most_divorced = [
                    {'person_id': pid, 'name': self._get_name_by_id(people_list, pid), 'divorce_count': count}
                    for pid, count in divorces_by_person.items()
                    if count == max_divorces
                ]
                stats.add_value('divorce', 'divorced_the_most', {
                    'count': max_divorces,
                    'people': most_divorced[:10]  # Top 10
                })
        
        # Age at divorce statistics
        if all_divorce_ages:
            stats.add_value('divorce', 'divorce_ages_count', len(all_divorce_ages))
            stats.add_value('divorce', 'average_age_at_divorce', round(sum(all_divorce_ages) / len(all_divorce_ages), 1))
            stats.add_value('divorce', 'median_age_at_divorce', self._median(all_divorce_ages))
            stats.add_value('divorce', 'youngest_divorce_age', min(all_divorce_ages))
            stats.add_value('divorce', 'oldest_divorce_age', max(all_divorce_ages))
            
            # Age distribution
            age_distribution = Counter(all_divorce_ages)
            stats.add_value('divorce', 'divorce_age_distribution', dict(sorted(age_distribution.items())))
            
            # Age ranges
            age_ranges = self._categorize_ages(all_divorce_ages)
            stats.add_value('divorce', 'divorce_age_ranges', age_ranges)
            
            # Oldest/Youngest when divorced (with details)
            oldest_divorces = sorted(divorce_ages_with_info, key=lambda x: x[0], reverse=True)[:10]
            stats.add_value('divorce', 'oldest_when_divorced', [
                {'name': name, 'age': age, 'divorce_year': year}
                for age, name, year in oldest_divorces
            ])
            
            youngest_divorces = sorted(divorce_ages_with_info, key=lambda x: x[0])[:10]
            stats.add_value('divorce', 'youngest_when_divorced', [
                {'name': name, 'age': age, 'divorce_year': year}
                for age, name, year in youngest_divorces
            ])
        
        # Gender-specific age statistics
        if divorce_ages_male:
            stats.add_value('divorce', 'average_divorce_age_male', round(sum(divorce_ages_male) / len(divorce_ages_male), 1))
            stats.add_value('divorce', 'median_divorce_age_male', self._median(divorce_ages_male))
        
        if divorce_ages_female:
            stats.add_value('divorce', 'average_divorce_age_female', round(sum(divorce_ages_female) / len(divorce_ages_female), 1))
            stats.add_value('divorce', 'median_divorce_age_female', self._median(divorce_ages_female))
        
        # Marriage duration before divorce
        if marriage_durations:
            stats.add_value('divorce', 'marriages_ending_in_divorce', len(marriage_durations))
            stats.add_value('divorce', 'average_marriage_duration_before_divorce', round(sum(marriage_durations) / len(marriage_durations), 1))
            stats.add_value('divorce', 'median_marriage_duration_before_divorce', self._median(marriage_durations))
            stats.add_value('divorce', 'shortest_marriage_ending_in_divorce', min(marriage_durations))
            stats.add_value('divorce', 'longest_marriage_ending_in_divorce', max(marriage_durations))
            
            # Duration distribution
            duration_distribution = Counter(marriage_durations)
            stats.add_value('divorce', 'divorce_duration_distribution', dict(sorted(duration_distribution.items())))
            
            # Duration ranges
            duration_ranges = self._categorize_durations(marriage_durations)
            stats.add_value('divorce', 'divorce_duration_ranges', duration_ranges)
            
            # Longest marriages ending in divorce (with details)
            longest_marriages = sorted(marriage_durations_with_info, key=lambda x: x[0], reverse=True)[:10]
            stats.add_value('divorce', 'longest_marriages_ending_in_divorce', [
                {
                    'duration': duration,
                    'person1': name1,
                    'person2': name2,
                    'marriage_year': marriage_year,
                    'divorce_year': divorce_year
                }
                for duration, name1, name2, marriage_year, divorce_year in longest_marriages
            ])
            
            # Shortest marriages ending in divorce (with details)
            shortest_marriages = sorted(marriage_durations_with_info, key=lambda x: x[0])[:10]
            stats.add_value('divorce', 'shortest_marriages_ending_in_divorce', [
                {
                    'duration': duration,
                    'person1': name1,
                    'person2': name2,
                    'marriage_year': marriage_year,
                    'divorce_year': divorce_year
                }
                for duration, name1, name2, marriage_year, divorce_year in shortest_marriages
            ])
        
        # Temporal trends
        if divorce_years:
            stats.add_value('divorce', 'earliest_divorce_year', min(divorce_years))
            stats.add_value('divorce', 'latest_divorce_year', max(divorce_years))
            
            # By decade
            if divorce_decades:
                stats.add_value('divorce', 'divorces_by_decade', {
                    f"{decade}s": count
                    for decade, count in sorted(divorce_decades.items())
                })
                
                # Peak decade
                peak_decade = max(divorce_decades.items(), key=lambda x: x[1])
                stats.add_value('divorce', 'peak_divorce_decade', {
                    'decade': f"{peak_decade[0]}s",
                    'count': peak_decade[1]
                })
            
            # By century
            if divorce_centuries:
                stats.add_value('divorce', 'divorces_by_century', {
                    self._century_name(century): count
                    for century, count in sorted(divorce_centuries.items())
                })
        
        return stats
    
    def _get_divorces(self, person: Any) -> List[Any]:
        """Get divorce events for a person."""
        divorces = []
        
        # Try to get divorce events from marriages
        if hasattr(person, 'get_events'):
            marriages = person.get_events('marriage')
            for marriage in marriages:
                # Check if the marriage has a divorce event
                marriage_divorces = self._get_marriage_divorces(marriage)
                divorces.extend(marriage_divorces)
        
        return divorces
    
    def _get_marriage_divorces(self, marriage: Any) -> List[Any]:
        """Get divorce events associated with a marriage."""
        divorces = []
        
        # Check if marriage has a divorce event attribute
        if hasattr(marriage, 'divorce'):
            if marriage.divorce:
                divorces.append(marriage.divorce)
        
        # Check if marriage has a get_event method for divorce
        if hasattr(marriage, 'get_event'):
            divorce = marriage.get_event('divorce')
            if divorce and divorce not in divorces:
                divorces.append(divorce)
        
        return divorces
    
    def _get_divorce_year(self, divorce_event: Any) -> Optional[int]:
        """Extract divorce year from divorce event."""
        if hasattr(divorce_event, 'date'):
            return year_num(divorce_event.date)
        return None
    
    def _get_marriages(self, person: Any) -> List[Any]:
        """Get marriage events for a person."""
        if hasattr(person, 'get_events'):
            return person.get_events('marriage') or []
        return []
    
    def _get_marriage_event(self, marriage: Any) -> Optional[Any]:
        """Get the marriage event from a marriage object."""
        if hasattr(marriage, 'event'):
            return marriage.event
        return marriage
    
    def _get_marriage_year(self, marriage_event: Any) -> Optional[int]:
        """Extract marriage year from marriage event."""
        if hasattr(marriage_event, 'date'):
            return year_num(marriage_event.date)
        return None
    
    def _get_partner(self, marriage: Any, person: Any) -> Optional[Any]:
        """Get the partner from a marriage."""
        if hasattr(marriage, 'partner'):
            return marriage.partner(person)
        if hasattr(marriage, 'people_list'):
            partners = [p for p in marriage.people_list if p != person]
            return partners[0] if partners else None
        return None
    
    def _get_id(self, person: Any) -> str:
        """Get person ID."""
        if hasattr(person, 'xref_id'):
            return person.xref_id
        if hasattr(person, 'id'):
            return person.id
        return str(id(person))
    
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
    
    def _get_sex(self, person: Any) -> Optional[str]:
        """Get person's sex."""
        return getattr(person, 'sex', None)
    
    def _get_name(self, person: Any) -> str:
        """Get person's name."""
        if hasattr(person, 'name'):
            return person.name
        return f"Unknown ({self._get_id(person)})"
    
    def _get_name_by_id(self, people_list: List[Any], person_id: str) -> str:
        """Get person name by ID."""
        for person in people_list:
            if self._get_id(person) == person_id:
                return self._get_name(person)
        return f"Unknown ({person_id})"
    
    def _median(self, values: List[float]) -> float:
        """Calculate median value."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        return sorted_values[n // 2]
    
    def _categorize_ages(self, ages: List[int]) -> Dict[str, int]:
        """Categorize ages into ranges."""
        ranges = {
            'Under 20': 0,
            '20-29': 0,
            '30-39': 0,
            '40-49': 0,
            '50-59': 0,
            '60+': 0
        }
        
        for age in ages:
            if age < 20:
                ranges['Under 20'] += 1
            elif age < 30:
                ranges['20-29'] += 1
            elif age < 40:
                ranges['30-39'] += 1
            elif age < 50:
                ranges['40-49'] += 1
            elif age < 60:
                ranges['50-59'] += 1
            else:
                ranges['60+'] += 1
        
        return ranges
    
    def _categorize_durations(self, durations: List[int]) -> Dict[str, int]:
        """Categorize marriage durations into ranges."""
        ranges = {
            'Less than 1 year': 0,
            '1-5 years': 0,
            '6-10 years': 0,
            '11-20 years': 0,
            '21-30 years': 0,
            '31+ years': 0
        }
        
        for duration in durations:
            if duration < 1:
                ranges['Less than 1 year'] += 1
            elif duration <= 5:
                ranges['1-5 years'] += 1
            elif duration <= 10:
                ranges['6-10 years'] += 1
            elif duration <= 20:
                ranges['11-20 years'] += 1
            elif duration <= 30:
                ranges['21-30 years'] += 1
            else:
                ranges['31+ years'] += 1
        
        return ranges
    
    def _century_name(self, century: int) -> str:
        """Convert century number to name."""
        if century == 21:
            return '21st Century'
        elif century == 20:
            return '20th Century'
        elif century == 19:
            return '19th Century'
        elif century == 18:
            return '18th Century'
        else:
            return f'{century}th Century'

"""
Marriage statistics collector.
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
class MarriageCollector(StatisticsCollector):
    """
    Collects marriage statistics from the dataset.
    
    Statistics collected:
        - Number of marriages per person
        - Marriage age distribution
        - Marriage duration statistics
        - Age differences between spouses
        - Marriage trends over time
    """
    collector_id: str = "marriage"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats, collector_num: int = None, total_collectors: int = None) -> Stats:
        """Collect marriage statistics."""
        stats = Stats()
        
        # Convert to list and dict for lookups
        people_list = list(people)
        total_people = len(people_list)
        people_dict = {self._get_id(p): p for p in people_list}
        
        # Build collector prefix
        prefix = f"Statistics ({collector_num}/{total_collectors}): " if collector_num and total_collectors else "Statistics: "
        
        # Set up progress tracking
        self._report_step(info=f"{prefix}Analyzing marriages", target=total_people, reset_counter=True, plus_step=0)
        
        # Marriage counts
        marriage_counts = Counter()
        marriages_by_person = defaultdict(int)
        
        # Marriage ages
        marriage_ages_male = []
        marriage_ages_female = []
        all_marriage_ages = []
        
        # Marriage durations
        marriage_durations = []
        marriage_durations_with_info = []  # (duration, person1_name, person2_name)
        
        # Age differences
        age_differences = []
        husband_older_cases = []
        wife_older_cases = []
        
        # Marriage years
        marriage_years = []
        marriage_decades = Counter()
        marriage_centuries = Counter()
        
        # Track processed marriages to avoid duplicates
        processed_marriages = set()
        
        for idx, person in enumerate(people_list):
            # Check for stop request and report progress every 100 people
            if idx % 100 == 0:
                if self._stop_requested("Marriage collection stopped"):
                    break
                self._report_step(plus_step=100)
            
            person_id = self._get_id(person)
            birth_year = self._get_birth_year(person)
            death_year = self._get_death_year(person)
            sex = self._get_sex(person)
            name = self._get_name(person)
            
            # Get marriage events
            marriages = self._get_marriages(person)
            if not marriages:
                continue
            
            marriage_count = len(marriages)
            marriages_by_person[person_id] = marriage_count
            marriage_counts[marriage_count] += 1
            
            for marriage in marriages:
                # Get marriage event details
                marriage_event = self._get_marriage_event(marriage)
                marriage_year = self._get_marriage_year(marriage_event) if marriage_event else None
                
                # Track marriage years
                if marriage_year:
                    marriage_years.append(marriage_year)
                    decade = (marriage_year // 10) * 10
                    marriage_decades[decade] += 1
                    century = ((marriage_year - 1) // 100) + 1
                    marriage_centuries[century] += 1
                
                # Calculate age at marriage
                if birth_year and marriage_year:
                    age_at_marriage = marriage_year - birth_year
                    if 0 <= age_at_marriage <= 100:
                        all_marriage_ages.append(age_at_marriage)
                        if sex == 'M':
                            marriage_ages_male.append(age_at_marriage)
                        elif sex == 'F':
                            marriage_ages_female.append(age_at_marriage)
                
                # Get partner and calculate age difference
                partner = self._get_partner(marriage, person)
                if partner:
                    partner_id = self._get_id(partner)
                    
                    # Create unique marriage ID to avoid duplicates
                    marriage_id = tuple(sorted([person_id, partner_id]))
                    if marriage_id in processed_marriages:
                        continue
                    processed_marriages.add(marriage_id)
                    
                    partner_birth_year = self._get_birth_year(partner)
                    partner_death_year = self._get_death_year(partner)
                    partner_sex = self._get_sex(partner)
                    partner_name = self._get_name(partner)
                    
                    # Age difference
                    if birth_year and partner_birth_year:
                        age_diff = abs(birth_year - partner_birth_year)
                        age_differences.append(age_diff)
                        
                        # Track who is older
                        if sex == 'M' and partner_sex == 'F':
                            if birth_year < partner_birth_year:  # Husband older
                                years_older = partner_birth_year - birth_year
                                if years_older > 10:
                                    husband_older_cases.append({
                                        'husband': name,
                                        'wife': partner_name,
                                        'age_difference': years_older
                                    })
                            elif partner_birth_year < birth_year:  # Wife older
                                years_older = birth_year - partner_birth_year
                                if years_older > 5:
                                    wife_older_cases.append({
                                        'husband': name,
                                        'wife': partner_name,
                                        'age_difference': years_older
                                    })
                        elif sex == 'F' and partner_sex == 'M':
                            if partner_birth_year < birth_year:  # Husband older
                                years_older = birth_year - partner_birth_year
                                if years_older > 10:
                                    husband_older_cases.append({
                                        'husband': partner_name,
                                        'wife': name,
                                        'age_difference': years_older
                                    })
                            elif birth_year < partner_birth_year:  # Wife older
                                years_older = partner_birth_year - birth_year
                                if years_older > 5:
                                    wife_older_cases.append({
                                        'husband': partner_name,
                                        'wife': name,
                                        'age_difference': years_older
                                    })
                    
                    # Marriage duration
                    if marriage_year:
                        # End year is earliest death year, or current year if both alive
                        end_year = None
                        if death_year and partner_death_year:
                            end_year = min(death_year, partner_death_year)
                        elif death_year:
                            end_year = death_year
                        elif partner_death_year:
                            end_year = partner_death_year
                        
                        if end_year:
                            duration = end_year - marriage_year
                            if 0 <= duration <= 100:
                                marriage_durations.append(duration)
                                marriage_durations_with_info.append((duration, name, partner_name))
        
        # Total marriages statistics
        total_people = len(people_list)
        people_with_marriages = len(marriages_by_person)
        total_marriages = sum(marriage_counts.values())
        
        stats.add_value('marriage', 'total_people', total_people)
        stats.add_value('marriage', 'people_with_marriages', people_with_marriages)
        stats.add_value('marriage', 'people_never_married', total_people - people_with_marriages)
        stats.add_value('marriage', 'total_marriages_recorded', len(processed_marriages))
        
        # Marriage count distribution
        if marriage_counts:
            stats.add_value('marriage', 'marriages_per_person_distribution', dict(sorted(marriage_counts.items())))
            
            # People married most
            max_marriages = max(marriages_by_person.values()) if marriages_by_person else 0
            most_married = [(self._get_name(people_dict[pid]), count) 
                          for pid, count in marriages_by_person.items() if count == max_marriages]
            if most_married:
                stats.add_value('marriage', 'most_marriages', max_marriages)
                stats.add_value('marriage', 'people_married_most', [
                    {'name': name, 'marriages': count} for name, count in most_married[:10]
                ])
        
        # Marriage age statistics
        if all_marriage_ages:
            stats.add_value('marriage', 'average_marriage_age', round(sum(all_marriage_ages) / len(all_marriage_ages), 1))
            stats.add_value('marriage', 'median_marriage_age', self._median(all_marriage_ages))
            stats.add_value('marriage', 'youngest_marriage_age', min(all_marriage_ages))
            stats.add_value('marriage', 'oldest_marriage_age', max(all_marriage_ages))
        
        if marriage_ages_male:
            stats.add_value('marriage', 'average_marriage_age_male', round(sum(marriage_ages_male) / len(marriage_ages_male), 1))
            stats.add_value('marriage', 'median_marriage_age_male', self._median(marriage_ages_male))
        
        if marriage_ages_female:
            stats.add_value('marriage', 'average_marriage_age_female', round(sum(marriage_ages_female) / len(marriage_ages_female), 1))
            stats.add_value('marriage', 'median_marriage_age_female', self._median(marriage_ages_female))
        
        # Marriage duration statistics
        if marriage_durations:
            stats.add_value('marriage', 'average_marriage_duration', round(sum(marriage_durations) / len(marriage_durations), 1))
            stats.add_value('marriage', 'median_marriage_duration', self._median(marriage_durations))
            stats.add_value('marriage', 'shortest_marriage_duration', min(marriage_durations))
            stats.add_value('marriage', 'longest_marriage_duration', max(marriage_durations))
            
            # Longest marriages
            longest = sorted(marriage_durations_with_info, key=lambda x: x[0], reverse=True)[:10]
            stats.add_value('marriage', 'longest_marriages', [
                {'duration': dur, 'person1': p1, 'person2': p2} for dur, p1, p2 in longest
            ])
            
            # Shortest marriages (excluding very short ones < 1 year)
            valid_short = [(d, p1, p2) for d, p1, p2 in marriage_durations_with_info if d >= 1]
            if valid_short:
                shortest = sorted(valid_short, key=lambda x: x[0])[:10]
                stats.add_value('marriage', 'shortest_marriages', [
                    {'duration': dur, 'person1': p1, 'person2': p2} for dur, p1, p2 in shortest
                ])
        
        # Age difference statistics
        if age_differences:
            stats.add_value('marriage', 'average_age_difference', round(sum(age_differences) / len(age_differences), 1))
            stats.add_value('marriage', 'median_age_difference', self._median(age_differences))
            stats.add_value('marriage', 'max_age_difference', max(age_differences))
        
        if husband_older_cases:
            sorted_cases = sorted(husband_older_cases, key=lambda x: x['age_difference'], reverse=True)
            stats.add_value('marriage', 'husband_much_older_cases', sorted_cases[:10])
        
        if wife_older_cases:
            sorted_cases = sorted(wife_older_cases, key=lambda x: x['age_difference'], reverse=True)
            stats.add_value('marriage', 'wife_much_older_cases', sorted_cases[:10])
        
        # Marriage trends over time
        if marriage_decades:
            decade_data = {f"{decade}s": count for decade, count in sorted(marriage_decades.items())}
            stats.add_value('marriage', 'marriages_by_decade', decade_data)
        
        if marriage_centuries:
            century_data = {self._ordinal(c) + ' century': count 
                          for c, count in sorted(marriage_centuries.items())}
            stats.add_value('marriage', 'marriages_by_century', century_data)
        
        if marriage_years:
            stats.add_value('marriage', 'earliest_marriage_year', min(marriage_years))
            stats.add_value('marriage', 'latest_marriage_year', max(marriage_years))
        
        logger.info(f"Marriage: {len(processed_marriages)} marriages, {people_with_marriages}/{total_people} married")
        
        return stats
    
    def _get_id(self, person: Any) -> str:
        """Get person ID."""
        return getattr(person, 'xref_id', None) or getattr(person, 'id', str(id(person)))
    
    def _get_name(self, person: Any) -> str:
        """Get person's name."""
        name = getattr(person, 'name', None) or getattr(person, 'display_name', None)
        if name:
            return name.replace('/', '').strip()
        return 'Unknown'
    
    def _get_sex(self, person: Any) -> Optional[str]:
        """Get sex/gender from person."""
        return getattr(person, 'sex', None)
    
    def _get_birth_year(self, person: Any) -> Optional[int]:
        """Extract birth year from person."""
        if hasattr(person, 'get_event_date'):
            birth_date = person.get_event_date('birth')
            if birth_date:
                return year_num(birth_date)
        
        if hasattr(person, 'get_event'):
            birth = person.get_event('birth')
            if birth and hasattr(birth, 'date') and birth.date:
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
            if death and hasattr(death, 'date') and death.date:
                return year_num(death.date)
        
        return None
    
    def _get_marriages(self, person: Any) -> List[Any]:
        """Get list of marriage events for person."""
        if hasattr(person, 'get_events'):
            marriages = person.get_events('marriage')
            if marriages:
                return marriages if isinstance(marriages, list) else [marriages]
        
        if hasattr(person, 'get_event'):
            marriage = person.get_event('marriage')
            if marriage:
                return [marriage]
        
        return []
    
    def _get_marriage_event(self, marriage: Any) -> Optional[Any]:
        """Extract the event from a Marriage object."""
        return getattr(marriage, 'event', None)
    
    def _get_marriage_year(self, event: Any) -> Optional[int]:
        """Extract year from marriage event."""
        if event and hasattr(event, 'date') and event.date:
            return year_num(event.date)
        return None
    
    def _get_partner(self, marriage: Any, person: Any) -> Optional[Any]:
        """Get the partner from a marriage."""
        if hasattr(marriage, 'partner'):
            return marriage.partner(person)
        if hasattr(marriage, 'people_list'):
            partners = [p for p in marriage.people_list if p != person]
            return partners[0] if partners else None
        return None
    
    def _median(self, values: List[int]) -> float:
        """Calculate median of a list of values."""
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            return sorted_values[n // 2]
    
    def _ordinal(self, n: int) -> str:
        """Convert number to ordinal string (1st, 2nd, 3rd, etc.)."""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

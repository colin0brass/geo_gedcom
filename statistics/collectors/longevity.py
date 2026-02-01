"""
Longevity patterns statistics collector.
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
class LongevityCollector(StatisticsCollector):
    """
    Collects longevity and mortality pattern statistics from the dataset.
    
    Statistics collected:
        - Life expectancy by birth decade
        - Life expectancy by birth century
        - Life expectancy by gender over time
        - Infant mortality rate
        - Child mortality rate
        - Survival rates by time period
    """
    collector_id: str = "longevity"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats, collector_num: int = None, total_collectors: int = None) -> Stats:
        """Collect longevity pattern statistics."""
        stats = Stats()
        
        # Convert to list for progress tracking
        people_list = list(people)
        total_people = len(people_list)
        
        # Build collector prefix
        prefix = f"Statistics ({collector_num}/{total_collectors}): " if collector_num and total_collectors else "Statistics: "
        
        # Set up progress tracking
        self._report_step(info=f"{prefix}Analyzing longevity", target=total_people, reset_counter=True, plus_step=0)
        
        # Data structures for analysis
        lifespans_by_decade = defaultdict(list)
        lifespans_by_century = defaultdict(list)
        lifespans_by_gender = {'M': [], 'F': [], 'Unknown': []}
        lifespans_by_decade_gender = defaultdict(lambda: {'M': [], 'F': []})
        
        infant_deaths = 0  # < 1 year
        child_deaths = 0   # < 5 years
        total_deaths = 0
        
        births_by_decade = Counter()
        deaths_by_decade = Counter()
        
        for idx, person in enumerate(people_list):
            # Check for stop request and report progress every 100 people
            if idx % 100 == 0:
                if self._stop_requested("Longevity collection stopped"):
                    break
                self._report_step(plus_step=100)
            birth_year = self._get_birth_year(person)
            death_year = self._get_death_year(person)
            sex = self._get_sex(person)
            
            # Track births by decade
            if birth_year:
                birth_decade = (birth_year // 10) * 10
                births_by_decade[birth_decade] += 1
            
            # Calculate lifespan if both dates available
            if birth_year and death_year:
                lifespan = death_year - birth_year
                
                # Validate lifespan
                if 0 <= lifespan <= 120:
                    total_deaths += 1
                    
                    # Infant and child mortality
                    if lifespan < 1:
                        infant_deaths += 1
                    if lifespan < 5:
                        child_deaths += 1
                    
                    # By birth decade
                    birth_decade = (birth_year // 10) * 10
                    lifespans_by_decade[birth_decade].append(lifespan)
                    
                    # By birth century
                    birth_century = ((birth_year - 1) // 100) + 1
                    lifespans_by_century[birth_century].append(lifespan)
                    
                    # By gender
                    gender_key = sex if sex in ['M', 'F'] else 'Unknown'
                    lifespans_by_gender[gender_key].append(lifespan)
                    
                    # By decade and gender
                    if sex in ['M', 'F']:
                        lifespans_by_decade_gender[birth_decade][sex].append(lifespan)
                    
                    # Track deaths by decade
                    death_decade = (death_year // 10) * 10
                    deaths_by_decade[death_decade] += 1
        
        # Calculate life expectancy by birth decade
        if lifespans_by_decade:
            le_by_decade = {}
            for decade, lifespans in sorted(lifespans_by_decade.items()):
                if lifespans:
                    le_by_decade[f"{decade}s"] = {
                        'average': round(sum(lifespans) / len(lifespans), 1),
                        'median': self._median(lifespans),
                        'min': min(lifespans),
                        'max': max(lifespans),
                        'count': len(lifespans)
                    }
            stats.add_value('longevity', 'life_expectancy_by_birth_decade', le_by_decade)
        
        # Calculate life expectancy by birth century
        if lifespans_by_century:
            le_by_century = {}
            for century, lifespans in sorted(lifespans_by_century.items()):
                if lifespans:
                    le_by_century[self._ordinal(century) + ' century'] = {
                        'average': round(sum(lifespans) / len(lifespans), 1),
                        'median': self._median(lifespans),
                        'min': min(lifespans),
                        'max': max(lifespans),
                        'count': len(lifespans)
                    }
            stats.add_value('longevity', 'life_expectancy_by_birth_century', le_by_century)
        
        # Calculate life expectancy by gender
        le_by_gender = {}
        for gender, lifespans in lifespans_by_gender.items():
            if lifespans:
                le_by_gender[gender] = {
                    'average': round(sum(lifespans) / len(lifespans), 1),
                    'median': self._median(lifespans),
                    'count': len(lifespans)
                }
        if le_by_gender:
            stats.add_value('longevity', 'life_expectancy_by_gender', le_by_gender)
        
        # Calculate life expectancy by decade and gender (trends over time)
        if lifespans_by_decade_gender:
            trends = {}
            for decade in sorted(lifespans_by_decade_gender.keys()):
                decade_data = lifespans_by_decade_gender[decade]
                trends[f"{decade}s"] = {}
                
                if decade_data['M']:
                    trends[f"{decade}s"]['Male'] = round(sum(decade_data['M']) / len(decade_data['M']), 1)
                if decade_data['F']:
                    trends[f"{decade}s"]['Female'] = round(sum(decade_data['F']) / len(decade_data['F']), 1)
            
            if trends:
                stats.add_value('longevity', 'life_expectancy_trends_by_gender', trends)
        
        # Mortality rates
        if total_deaths > 0:
            stats.add_value('longevity', 'infant_mortality_count', infant_deaths)
            stats.add_value('longevity', 'infant_mortality_rate', round(100 * infant_deaths / total_deaths, 2))
            stats.add_value('longevity', 'child_mortality_count', child_deaths)
            stats.add_value('longevity', 'child_mortality_rate', round(100 * child_deaths / total_deaths, 2))
            stats.add_value('longevity', 'total_deaths_analyzed', total_deaths)
        
        # Survival analysis - percentage who reached certain ages
        if total_deaths > 0:
            survived_to_5 = sum(1 for ls_list in lifespans_by_decade.values() for ls in ls_list if ls >= 5)
            survived_to_18 = sum(1 for ls_list in lifespans_by_decade.values() for ls in ls_list if ls >= 18)
            survived_to_65 = sum(1 for ls_list in lifespans_by_decade.values() for ls in ls_list if ls >= 65)
            survived_to_80 = sum(1 for ls_list in lifespans_by_decade.values() for ls in ls_list if ls >= 80)
            
            survival_rates = {
                'survived_to_age_5': {
                    'count': survived_to_5,
                    'percentage': round(100 * survived_to_5 / total_deaths, 1)
                },
                'survived_to_age_18': {
                    'count': survived_to_18,
                    'percentage': round(100 * survived_to_18 / total_deaths, 1)
                },
                'survived_to_age_65': {
                    'count': survived_to_65,
                    'percentage': round(100 * survived_to_65 / total_deaths, 1)
                },
                'survived_to_age_80': {
                    'count': survived_to_80,
                    'percentage': round(100 * survived_to_80 / total_deaths, 1)
                }
            }
            stats.add_value('longevity', 'survival_rates', survival_rates)
        
        # Birth and death trends
        if births_by_decade:
            stats.add_value('longevity', 'births_by_decade', dict(sorted(births_by_decade.items())))
        if deaths_by_decade:
            stats.add_value('longevity', 'deaths_by_decade', dict(sorted(deaths_by_decade.items())))
        
        # Calculate overall trends
        if lifespans_by_decade and len(lifespans_by_decade) >= 2:
            decades = sorted(lifespans_by_decade.keys())
            early_decades = decades[:len(decades)//2]
            late_decades = decades[len(decades)//2:]
            
            early_lifespans = [ls for d in early_decades for ls in lifespans_by_decade[d]]
            late_lifespans = [ls for d in late_decades for ls in lifespans_by_decade[d]]
            
            if early_lifespans and late_lifespans:
                early_avg = sum(early_lifespans) / len(early_lifespans)
                late_avg = sum(late_lifespans) / len(late_lifespans)
                improvement = late_avg - early_avg
                
                stats.add_value('longevity', 'longevity_improvement', {
                    'early_period_avg': round(early_avg, 1),
                    'late_period_avg': round(late_avg, 1),
                    'improvement_years': round(improvement, 1),
                    'improvement_percentage': round(100 * improvement / early_avg, 1) if early_avg > 0 else 0
                })
        
        logger.info(f"Longevity: {total_deaths} deaths analyzed, infant mortality {infant_deaths}/{total_deaths}")
        
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
    
    def _get_sex(self, person: Any) -> Optional[str]:
        """Get sex/gender from person."""
        return getattr(person, 'sex', None)
    
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

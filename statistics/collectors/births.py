"""
Birth statistics collector.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import logging
from typing import Any, Iterable, Optional, Dict

from geo_gedcom.statistics.base import StatisticsCollector, register_collector
from geo_gedcom.statistics.model import Stats
from geo_gedcom.enrichment.date_utils import year_num, coerce_to_single_date

logger = logging.getLogger(__name__)


# Month number to name mapping
MONTH_NAMES = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

# Zodiac sign calculation
ZODIAC_SIGNS = [
    ((1, 20), 'Capricorn'),
    ((2, 19), 'Aquarius'),
    ((3, 21), 'Pisces'),
    ((4, 20), 'Aries'),
    ((5, 21), 'Taurus'),
    ((6, 21), 'Gemini'),
    ((7, 23), 'Cancer'),
    ((8, 23), 'Leo'),
    ((9, 23), 'Virgo'),
    ((10, 23), 'Libra'),
    ((11, 22), 'Scorpio'),
    ((12, 22), 'Sagittarius'),
    ((12, 31), 'Capricorn')
]


@register_collector
@dataclass
class BirthsCollector(StatisticsCollector):
    """
    Collects birth-related statistics from the dataset.
    
    Statistics collected:
        - Birth months distribution
        - Birth decades and centuries
        - Zodiac signs distribution
        - Seasonal patterns
    """
    collector_id: str = "births"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats) -> Stats:
        """Collect birth statistics."""
        stats = Stats()
        
        birth_months = []
        birth_years = []
        birth_decades = []
        birth_centuries = []
        zodiac_signs = []
        
        people_with_month = 0
        people_with_day = 0
        
        for person in people:
            # Get birth date details
            birth_date = self._get_birth_date(person)
            birth_year = self._get_birth_year(person)
            
            if birth_year:
                birth_years.append(birth_year)
                
                # Calculate decade and century
                decade = (birth_year // 10) * 10
                birth_decades.append(decade)
                
                century = ((birth_year - 1) // 100) + 1
                birth_centuries.append(century)
            
            if birth_date:
                # Extract month
                month = self._get_month(birth_date)
                if month:
                    birth_months.append(month)
                    people_with_month += 1
                    
                    # Extract day for zodiac
                    day = self._get_day(birth_date)
                    if day:
                        people_with_day += 1
                        zodiac = self._calculate_zodiac(month, day)
                        if zodiac:
                            zodiac_signs.append(zodiac)
        
        # Birth months statistics
        if birth_months:
            month_counts = Counter(birth_months)
            # Convert to month names
            month_names_counts = {MONTH_NAMES.get(m, f'Month {m}'): count 
                                 for m, count in month_counts.items()}
            stats.add_value('births', 'birth_months', dict(sorted(month_names_counts.items(), 
                                                                  key=lambda x: list(MONTH_NAMES.values()).index(x[0]))))
            stats.add_value('births', 'people_with_birth_month', people_with_month)
            
            # Find most/least common birth month
            most_common_month = max(month_names_counts.items(), key=lambda x: x[1])
            stats.add_value('births', 'most_common_birth_month', 
                          {'month': most_common_month[0], 'count': most_common_month[1]})
            
            # Seasonal distribution
            seasons = self._categorize_by_season(birth_months)
            stats.add_value('births', 'birth_seasons', seasons)
        
        # Birth decades statistics
        if birth_decades:
            decade_counts = Counter(birth_decades)
            # Format as strings like "1800s", "1900s"
            decade_labels = {f"{decade}s": count for decade, count in sorted(decade_counts.items())}
            stats.add_value('births', 'birth_decades', decade_labels)
        
        # Birth centuries statistics
        if birth_centuries:
            century_counts = Counter(birth_centuries)
            # Format as ordinal centuries
            century_labels = {self._ordinal(c) + ' century': count 
                            for c, count in sorted(century_counts.items())}
            stats.add_value('births', 'birth_centuries', century_labels)
        
        # Birth years range
        if birth_years:
            stats.add_value('births', 'earliest_birth_year', min(birth_years))
            stats.add_value('births', 'latest_birth_year', max(birth_years))
            stats.add_value('births', 'birth_year_span', max(birth_years) - min(birth_years))
        
        # Zodiac signs statistics
        if zodiac_signs:
            zodiac_counts = Counter(zodiac_signs)
            stats.add_value('births', 'zodiac_signs', dict(zodiac_counts.most_common()))
            stats.add_value('births', 'people_with_zodiac', len(zodiac_signs))
            
            # Most/least common zodiac
            most_common = max(zodiac_counts.items(), key=lambda x: x[1])
            least_common = min(zodiac_counts.items(), key=lambda x: x[1])
            stats.add_value('births', 'most_common_zodiac', 
                          {'sign': most_common[0], 'count': most_common[1]})
            stats.add_value('births', 'least_common_zodiac', 
                          {'sign': least_common[0], 'count': least_common[1]})
        
        logger.info(f"Births: {len(birth_years)} with years, {people_with_month} with months, {len(zodiac_signs)} with zodiac")
        
        return stats
    
    def _get_birth_date(self, person: Any) -> Optional[Any]:
        """Get birth date object from person."""
        if hasattr(person, 'get_event_date'):
            return person.get_event_date('birth')
        
        if hasattr(person, 'get_event'):
            birth = person.get_event('birth')
            if birth and hasattr(birth, 'date'):
                return birth.date
        
        return None
    
    def _get_birth_year(self, person: Any) -> Optional[int]:
        """Extract birth year from person."""
        birth_date = self._get_birth_date(person)
        if birth_date:
            return year_num(birth_date)
        return None
    
    def _get_month(self, date_obj: Any) -> Optional[int]:
        """
        Extract month number from a date object.
        
        Handles GedcomDate, GregorianDate, and datetime.date objects.
        """
        if date_obj is None:
            return None
        
        # Try to get single date from GedcomDate
        single_date = coerce_to_single_date(date_obj)
        if single_date is None:
            single_date = date_obj
        
        # Check for month attribute (GregorianDate-like or datetime)
        if hasattr(single_date, 'month'):
            month = single_date.month
            # Handle string months (GEDCOM format)
            if isinstance(month, str):
                month_map = {
                    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4,
                    'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
                    'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
                }
                return month_map.get(month.upper())
            elif isinstance(month, int):
                return month
        
        return None
    
    def _get_day(self, date_obj: Any) -> Optional[int]:
        """Extract day from a date object."""
        if date_obj is None:
            return None
        
        # Try to get single date from GedcomDate
        single_date = coerce_to_single_date(date_obj)
        if single_date is None:
            single_date = date_obj
        
        # Check for day attribute
        if hasattr(single_date, 'day'):
            day = single_date.day
            if isinstance(day, int):
                return day
        
        return None
    
    def _calculate_zodiac(self, month: int, day: int) -> Optional[str]:
        """
        Calculate zodiac sign from month and day.
        
        Args:
            month: Month number (1-12)
            day: Day of month (1-31)
            
        Returns:
            Zodiac sign name, or None if invalid date
        """
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return None
        
        for (cutoff_month, cutoff_day), sign in ZODIAC_SIGNS:
            if month < cutoff_month or (month == cutoff_month and day <= cutoff_day):
                return sign
        
        return None
    
    def _categorize_by_season(self, months: list[int]) -> Dict[str, int]:
        """
        Categorize months into seasons (Northern Hemisphere).
        
        Args:
            months: List of month numbers
            
        Returns:
            Dictionary with season counts
        """
        seasons = {
            'Winter': 0,  # Dec, Jan, Feb
            'Spring': 0,  # Mar, Apr, May
            'Summer': 0,  # Jun, Jul, Aug
            'Fall': 0     # Sep, Oct, Nov
        }
        
        for month in months:
            if month in [12, 1, 2]:
                seasons['Winter'] += 1
            elif month in [3, 4, 5]:
                seasons['Spring'] += 1
            elif month in [6, 7, 8]:
                seasons['Summer'] += 1
            elif month in [9, 10, 11]:
                seasons['Fall'] += 1
        
        return seasons
    
    def _ordinal(self, n: int) -> str:
        """Convert number to ordinal string (1st, 2nd, 3rd, etc.)."""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

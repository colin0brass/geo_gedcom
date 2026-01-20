"""
Relationship status statistics collector.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import logging
from typing import Any, Iterable, Optional, Dict

from geo_gedcom.statistics.base import StatisticsCollector, register_collector
from geo_gedcom.statistics.model import Stats
from geo_gedcom.enrichment.date_utils import year_num

logger = logging.getLogger(__name__)


@register_collector
@dataclass
class RelationshipStatusCollector(StatisticsCollector):
    """
    Collects relationship status statistics from the dataset.
    
    Statistics collected:
        - Never married count
        - Ever married count
        - Currently married count (for living people)
        - Widowed count
        - Relationship status by gender
        - Relationship status by age group
    """
    collector_id: str = "relationship_status"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats) -> Stats:
        """Collect relationship status statistics."""
        stats = Stats()
        
        # Convert to list and dict for lookups
        people_list = list(people)
        people_dict = {self._get_id(p): p for p in people_list}
        
        # Status counts
        never_married = 0
        ever_married = 0
        currently_married_living = 0  # Living and has living spouse
        widowed = 0
        
        # By gender
        status_by_gender = {
            'M': {'never_married': 0, 'ever_married': 0, 'widowed': 0, 'currently_married': 0},
            'F': {'never_married': 0, 'ever_married': 0, 'widowed': 0, 'currently_married': 0},
            'Unknown': {'never_married': 0, 'ever_married': 0, 'widowed': 0, 'currently_married': 0}
        }
        
        # By age group (for living people)
        age_groups = ['0-17', '18-29', '30-39', '40-49', '50-59', '60-69', '70+']
        status_by_age = {age: {'never_married': 0, 'married': 0, 'widowed': 0} for age in age_groups}
        
        current_year = 2026  # Could use datetime.date.today().year
        
        for person in people_list:
            person_id = self._get_id(person)
            sex = self._get_sex(person)
            sex_key = sex if sex in ['M', 'F'] else 'Unknown'
            birth_year = self._get_birth_year(person)
            death_year = self._get_death_year(person)
            is_living = death_year is None
            
            # Get marriages
            marriages = self._get_marriages(person)
            has_marriage = len(marriages) > 0
            
            if not has_marriage:
                never_married += 1
                status_by_gender[sex_key]['never_married'] += 1
                
                # Add to age group if living
                if is_living and birth_year:
                    age = current_year - birth_year
                    age_group = self._get_age_group(age)
                    if age_group:
                        status_by_age[age_group]['never_married'] += 1
            else:
                ever_married += 1
                status_by_gender[sex_key]['ever_married'] += 1
                
                # Check if currently married (for living people)
                if is_living:
                    has_living_spouse = False
                    all_spouses_deceased = True
                    
                    for marriage in marriages:
                        partner = self._get_partner(marriage, person)
                        if partner:
                            partner_death_year = self._get_death_year(partner)
                            if partner_death_year is None:
                                has_living_spouse = True
                                all_spouses_deceased = False
                            # If at least one spouse is living, not widowed
                    
                    if has_living_spouse:
                        currently_married_living += 1
                        status_by_gender[sex_key]['currently_married'] += 1
                        
                        if birth_year:
                            age = current_year - birth_year
                            age_group = self._get_age_group(age)
                            if age_group:
                                status_by_age[age_group]['married'] += 1
                    elif all_spouses_deceased:
                        widowed += 1
                        status_by_gender[sex_key]['widowed'] += 1
                        
                        if birth_year:
                            age = current_year - birth_year
                            age_group = self._get_age_group(age)
                            if age_group:
                                status_by_age[age_group]['widowed'] += 1
                else:
                    # For deceased people, check if they were widowed before death
                    if death_year:
                        was_widowed = False
                        for marriage in marriages:
                            partner = self._get_partner(marriage, person)
                            if partner:
                                partner_death_year = self._get_death_year(partner)
                                if partner_death_year and partner_death_year < death_year:
                                    was_widowed = True
                                    break
                        
                        if was_widowed:
                            widowed += 1
                            status_by_gender[sex_key]['widowed'] += 1
        
        total_people = len(people_list)
        
        # Overall statistics
        stats.add_value('relationship_status', 'total_people', total_people)
        stats.add_value('relationship_status', 'never_married', never_married)
        stats.add_value('relationship_status', 'ever_married', ever_married)
        stats.add_value('relationship_status', 'currently_married_living', currently_married_living)
        stats.add_value('relationship_status', 'widowed', widowed)
        
        if total_people > 0:
            stats.add_value('relationship_status', 'never_married_percentage', 
                          round(100 * never_married / total_people, 1))
            stats.add_value('relationship_status', 'ever_married_percentage', 
                          round(100 * ever_married / total_people, 1))
        
        # By gender
        stats.add_value('relationship_status', 'status_by_gender', status_by_gender)
        
        # By age group (for living people only)
        # Filter out empty age groups
        filtered_age_status = {age: counts for age, counts in status_by_age.items() 
                              if sum(counts.values()) > 0}
        if filtered_age_status:
            stats.add_value('relationship_status', 'status_by_age_group', filtered_age_status)
        
        # Additional insights
        living_people = sum(1 for p in people_list if self._get_death_year(p) is None)
        if living_people > 0:
            stats.add_value('relationship_status', 'living_people', living_people)
            stats.add_value('relationship_status', 'marriage_rate_among_living', 
                          round(100 * currently_married_living / living_people, 1))
        
        logger.info(f"Relationship: {never_married} never married, {ever_married} ever married, {widowed} widowed")
        
        return stats
    
    def _get_id(self, person: Any) -> str:
        """Get person ID."""
        return getattr(person, 'xref_id', None) or getattr(person, 'id', str(id(person)))
    
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
    
    def _get_marriages(self, person: Any) -> list:
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
    
    def _get_partner(self, marriage: Any, person: Any) -> Optional[Any]:
        """Get the partner from a marriage."""
        if hasattr(marriage, 'partner'):
            return marriage.partner(person)
        if hasattr(marriage, 'people_list'):
            partners = [p for p in marriage.people_list if p != person]
            return partners[0] if partners else None
        return None
    
    def _get_age_group(self, age: int) -> Optional[str]:
        """Get age group label for an age."""
        if age < 0 or age > 150:
            return None
        if age < 18:
            return '0-17'
        elif age < 30:
            return '18-29'
        elif age < 40:
            return '30-39'
        elif age < 50:
            return '40-49'
        elif age < 60:
            return '50-59'
        elif age < 70:
            return '60-69'
        else:
            return '70+'

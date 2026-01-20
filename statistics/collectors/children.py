"""
Children statistics collector.
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
class ChildrenCollector(StatisticsCollector):
    """
    Collects children and family size statistics from the dataset.
    
    Statistics collected:
        - Number of children per family
        - Number of children per person (by gender)
        - Age when having children
        - Age gaps between siblings
        - Largest/smallest families
    """
    collector_id: str = "children"
    
    def collect(self, people: Iterable[Any], existing_stats: Stats) -> Stats:
        """Collect children statistics."""
        stats = Stats()
        
        # Convert to list and dict for lookups
        people_list = list(people)
        people_dict = {self._get_id(p): p for p in people_list}
        
        # Children counts
        children_per_person = defaultdict(int)
        children_per_person_male = defaultdict(int)
        children_per_person_female = defaultdict(int)
        
        # Family sizes (by parent pair)
        family_sizes = []
        families_with_info = []  # (size, father_name, mother_name)
        
        # Age when having children
        ages_at_first_child_male = []
        ages_at_last_child_male = []
        ages_at_first_child_female = []
        ages_at_last_child_female = []
        
        # Sibling age gaps
        sibling_age_gaps = []
        families_with_gaps = []  # (max_gap, min_gap, father_name, mother_name)
        
        # Track processed families to avoid duplicates
        processed_families = set()
        
        for person in people_list:
            person_id = self._get_id(person)
            
            # Get children
            children_ids = self._get_children(person)
            if not children_ids:
                continue
            
            num_children = len(children_ids)
            children_per_person[person_id] = num_children
            
            sex = self._get_sex(person)
            if sex == 'M':
                children_per_person_male[person_id] = num_children
            elif sex == 'F':
                children_per_person_female[person_id] = num_children
            
            # Get children birth years for age analysis
            children_birth_years = []
            for child_id in children_ids:
                child = people_dict.get(child_id)
                if child:
                    child_birth_year = self._get_birth_year(child)
                    if child_birth_year:
                        children_birth_years.append(child_birth_year)
            
            # Calculate age when having children
            if children_birth_years:
                birth_year = self._get_birth_year(person)
                if birth_year:
                    children_birth_years_sorted = sorted(children_birth_years)
                    first_child_year = children_birth_years_sorted[0]
                    last_child_year = children_birth_years_sorted[-1]
                    
                    age_at_first = first_child_year - birth_year
                    age_at_last = last_child_year - birth_year
                    
                    if 10 <= age_at_first <= 60:
                        if sex == 'M':
                            ages_at_first_child_male.append(age_at_first)
                        elif sex == 'F':
                            ages_at_first_child_female.append(age_at_first)
                    
                    if 10 <= age_at_last <= 70:
                        if sex == 'M':
                            ages_at_last_child_male.append(age_at_last)
                        elif sex == 'F':
                            ages_at_last_child_female.append(age_at_last)
            
            # Analyze families (father-mother pairs)
            father_id = getattr(person, 'father', None)
            mother_id = getattr(person, 'mother', None)
            
            if father_id and mother_id:
                family_key = tuple(sorted([str(father_id), str(mother_id)]))
                if family_key not in processed_families:
                    processed_families.add(family_key)
                    
                    # Count all children in this family
                    siblings = []
                    sibling_birth_years = []
                    
                    for p in people_list:
                        p_father = getattr(p, 'father', None)
                        p_mother = getattr(p, 'mother', None)
                        
                        if str(p_father) == str(father_id) and str(p_mother) == str(mother_id):
                            siblings.append(p)
                            birth_year = self._get_birth_year(p)
                            if birth_year:
                                sibling_birth_years.append(birth_year)
                    
                    family_size = len(siblings)
                    family_sizes.append(family_size)
                    
                    # Get parent names
                    father = people_dict.get(str(father_id))
                    mother = people_dict.get(str(mother_id))
                    father_name = self._get_name(father) if father else 'Unknown'
                    mother_name = self._get_name(mother) if mother else 'Unknown'
                    
                    families_with_info.append((family_size, father_name, mother_name))
                    
                    # Calculate sibling age gaps
                    if len(sibling_birth_years) >= 2:
                        sorted_years = sorted(sibling_birth_years)
                        gaps = [sorted_years[i+1] - sorted_years[i] for i in range(len(sorted_years)-1)]
                        
                        for gap in gaps:
                            if gap > 0:
                                sibling_age_gaps.append(gap)
                        
                        if gaps:
                            max_gap = max(gaps)
                            min_gap = min(gaps)
                            families_with_gaps.append((max_gap, min_gap, father_name, mother_name))
        
        # Children per person statistics
        if children_per_person:
            children_counts = Counter(children_per_person.values())
            stats.add_value('children', 'children_per_person_distribution', dict(sorted(children_counts.items())))
            
            # People with most children
            max_children = max(children_per_person.values())
            most_children = [(self._get_name(people_dict[pid]), count) 
                           for pid, count in children_per_person.items() if count == max_children]
            if most_children:
                stats.add_value('children', 'most_children', max_children)
                stats.add_value('children', 'people_with_most_children', [
                    {'name': name, 'children': count} for name, count in most_children[:10]
                ])
        
        if children_per_person_male:
            max_male = max(children_per_person_male.values())
            stats.add_value('children', 'most_children_male', max_male)
            most_male = [(self._get_name(people_dict[pid]), count) 
                        for pid, count in children_per_person_male.items() if count == max_male]
            if most_male:
                stats.add_value('children', 'men_with_most_children', [
                    {'name': name, 'children': count} for name, count in most_male[:10]
                ])
        
        if children_per_person_female:
            max_female = max(children_per_person_female.values())
            stats.add_value('children', 'most_children_female', max_female)
            most_female = [(self._get_name(people_dict[pid]), count) 
                          for pid, count in children_per_person_female.items() if count == max_female]
            if most_female:
                stats.add_value('children', 'women_with_most_children', [
                    {'name': name, 'children': count} for name, count in most_female[:10]
                ])
        
        # Family size statistics
        if family_sizes:
            stats.add_value('children', 'total_families', len(family_sizes))
            stats.add_value('children', 'average_family_size', round(sum(family_sizes) / len(family_sizes), 1))
            stats.add_value('children', 'median_family_size', self._median(family_sizes))
            stats.add_value('children', 'largest_family_size', max(family_sizes))
            stats.add_value('children', 'smallest_family_size', min(family_sizes))
            
            # Family size distribution
            size_counts = Counter(family_sizes)
            stats.add_value('children', 'family_size_distribution', dict(sorted(size_counts.items())))
            
            # Largest families
            largest = sorted(families_with_info, key=lambda x: x[0], reverse=True)[:10]
            stats.add_value('children', 'largest_families', [
                {'size': size, 'father': father, 'mother': mother} 
                for size, father, mother in largest
            ])
        
        # Age when having children
        if ages_at_first_child_male:
            stats.add_value('children', 'average_age_first_child_male', 
                          round(sum(ages_at_first_child_male) / len(ages_at_first_child_male), 1))
            stats.add_value('children', 'youngest_father_at_first_child', min(ages_at_first_child_male))
            stats.add_value('children', 'oldest_father_at_first_child', max(ages_at_first_child_male))
        
        if ages_at_last_child_male:
            stats.add_value('children', 'average_age_last_child_male', 
                          round(sum(ages_at_last_child_male) / len(ages_at_last_child_male), 1))
            stats.add_value('children', 'oldest_father_at_last_child', max(ages_at_last_child_male))
        
        if ages_at_first_child_female:
            stats.add_value('children', 'average_age_first_child_female', 
                          round(sum(ages_at_first_child_female) / len(ages_at_first_child_female), 1))
            stats.add_value('children', 'youngest_mother_at_first_child', min(ages_at_first_child_female))
            stats.add_value('children', 'oldest_mother_at_first_child', max(ages_at_first_child_female))
        
        if ages_at_last_child_female:
            stats.add_value('children', 'average_age_last_child_female', 
                          round(sum(ages_at_last_child_female) / len(ages_at_last_child_female), 1))
            stats.add_value('children', 'oldest_mother_at_last_child', max(ages_at_last_child_female))
        
        # Sibling age gap statistics
        if sibling_age_gaps:
            stats.add_value('children', 'average_sibling_age_gap', 
                          round(sum(sibling_age_gaps) / len(sibling_age_gaps), 1))
            stats.add_value('children', 'median_sibling_age_gap', self._median(sibling_age_gaps))
            stats.add_value('children', 'largest_sibling_age_gap', max(sibling_age_gaps))
            stats.add_value('children', 'smallest_sibling_age_gap', min(sibling_age_gaps))
            
            # Families with largest gaps
            if families_with_gaps:
                largest_gaps = sorted(families_with_gaps, key=lambda x: x[0], reverse=True)[:10]
                stats.add_value('children', 'families_largest_sibling_gaps', [
                    {'max_gap': max_gap, 'min_gap': min_gap, 'father': father, 'mother': mother}
                    for max_gap, min_gap, father, mother in largest_gaps
                ])
        
        logger.info(f"Children: {len(family_sizes)} families, avg {sum(family_sizes)/len(family_sizes):.1f} children" if family_sizes else "Children: No family data")
        
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
    
    def _get_children(self, person: Any) -> List[str]:
        """Get list of children IDs."""
        children = getattr(person, 'children', None)
        if children:
            return children if isinstance(children, list) else [children]
        return []
    
    def _median(self, values: List[int]) -> float:
        """Calculate median of a list of values."""
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            return sorted_values[n // 2]

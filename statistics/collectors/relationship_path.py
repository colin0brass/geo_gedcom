"""
Relationship path statistics collector.

Analyzes relationships from a focus person's perspective.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
import logging
from typing import Any, Iterable, Optional, Dict, List, Set, Tuple

from geo_gedcom.statistics.base import StatisticsCollector, register_collector
from geo_gedcom.statistics.model import Stats

logger = logging.getLogger(__name__)


@register_collector
@dataclass
class RelationshipPathCollector(StatisticsCollector):
    """
    Collects relationship statistics from a focus person's perspective.
    
    Analyzes how people in the dataset relate to a specific focus person,
    including:
    - Direct ancestors and descendants
    - Blood relatives (extended family)
    - Relatives by marriage
    - Steps away (relationship distance)
    - Generational difference
    
    Attributes:
        focus_person_id: ID of the focus person (if None, uses first person or most connected)
    """
    collector_id: str = "relationship_path"
    focus_person_id: Optional[str] = None
    
    def collect(self, people: Iterable[Any], existing_stats: Stats) -> Stats:
        """Collect relationship path statistics."""
        stats = Stats()
        
        # Convert to list and create lookup
        people_list = list(people)
        if not people_list:
            return stats
        
        people_dict = {self._get_id(p): p for p in people_list}
        
        # Determine focus person
        focus_person = self._get_focus_person(people_list, people_dict)
        if not focus_person:
            logger.warning("No focus person found, skipping relationship path analysis")
            return stats
        
        focus_id = self._get_id(focus_person)
        focus_name = self._get_name(focus_person)
        
        stats.add_value('relationship_path', 'focus_person_id', focus_id)
        stats.add_value('relationship_path', 'focus_person_name', focus_name)
        
        # Build relationship graph
        relationships = self._analyze_relationships(focus_person, people_dict)
        
        # Categorize relationships
        direct_ancestors = []
        direct_descendants = []
        blood_relatives = []
        relatives_by_marriage = []
        
        steps_distribution = Counter()
        generation_distribution = Counter()
        
        # Relationship type counters
        relationship_types = Counter()
        
        for person_id, rel_info in relationships.items():
            if person_id == focus_id:
                continue
            
            person = people_dict.get(person_id)
            if not person:
                continue
            
            name = self._get_name(person)
            steps = rel_info['steps']
            generation = rel_info['generation']
            is_blood = rel_info['is_blood']
            rel_type = rel_info['type']
            
            # Count steps and generations
            steps_distribution[steps] += 1
            generation_distribution[generation] += 1
            relationship_types[rel_type] += 1
            
            # Categorize
            if rel_type in ['parent', 'grandparent', 'great-grandparent', 'ancestor']:
                direct_ancestors.append({'name': name, 'steps': steps, 'generation': generation, 'type': rel_type})
            elif rel_type in ['child', 'grandchild', 'great-grandchild', 'descendant']:
                direct_descendants.append({'name': name, 'steps': steps, 'generation': generation, 'type': rel_type})
            elif is_blood:
                blood_relatives.append({'name': name, 'steps': steps, 'generation': generation, 'type': rel_type})
            else:
                relatives_by_marriage.append({'name': name, 'steps': steps, 'generation': generation, 'type': rel_type})
        
        # Overall counts
        stats.add_value('relationship_path', 'total_people_analyzed', len(people_list))
        stats.add_value('relationship_path', 'total_relationships_found', len(relationships) - 1)  # Exclude focus person
        stats.add_value('relationship_path', 'direct_ancestors', len(direct_ancestors))
        stats.add_value('relationship_path', 'direct_descendants', len(direct_descendants))
        stats.add_value('relationship_path', 'blood_relatives', len(blood_relatives))
        stats.add_value('relationship_path', 'relatives_by_marriage', len(relatives_by_marriage))
        
        # Steps away distribution
        if steps_distribution:
            stats.add_value('relationship_path', 'steps_away_distribution', {
                f"{step} step{'s' if step != 1 else ''}": count
                for step, count in sorted(steps_distribution.items())
            })
            
            stats.add_value('relationship_path', 'closest_step', min(steps_distribution.keys()))
            stats.add_value('relationship_path', 'furthest_step', max(steps_distribution.keys()))
            stats.add_value('relationship_path', 'average_steps', round(
                sum(s * c for s, c in steps_distribution.items()) / sum(steps_distribution.values()), 1
            ))
        
        # Generation distribution
        if generation_distribution:
            stats.add_value('relationship_path', 'generation_distribution', {
                self._generation_label(gen): count
                for gen, count in sorted(generation_distribution.items())
            })
            
            stats.add_value('relationship_path', 'oldest_generation', min(generation_distribution.keys()))
            stats.add_value('relationship_path', 'youngest_generation', max(generation_distribution.keys()))
            stats.add_value('relationship_path', 'generation_span', 
                           max(generation_distribution.keys()) - min(generation_distribution.keys()))
        
        # Relationship types
        if relationship_types:
            stats.add_value('relationship_path', 'relationship_types', dict(
                sorted(relationship_types.items(), key=lambda x: x[1], reverse=True)
            ))
            
            most_common_type = relationship_types.most_common(1)[0]
            stats.add_value('relationship_path', 'most_common_relationship', {
                'type': most_common_type[0],
                'count': most_common_type[1]
            })
        
        # Detailed lists (top 20 each)
        if direct_ancestors:
            stats.add_value('relationship_path', 'direct_ancestors_list', 
                          sorted(direct_ancestors, key=lambda x: x['steps'])[:20])
        
        if direct_descendants:
            stats.add_value('relationship_path', 'direct_descendants_list',
                          sorted(direct_descendants, key=lambda x: x['steps'])[:20])
        
        if blood_relatives:
            stats.add_value('relationship_path', 'blood_relatives_list',
                          sorted(blood_relatives, key=lambda x: x['steps'])[:20])
        
        if relatives_by_marriage:
            stats.add_value('relationship_path', 'relatives_by_marriage_list',
                          sorted(relatives_by_marriage, key=lambda x: x['steps'])[:20])
        
        return stats
    
    def _get_focus_person(self, people_list: List[Any], people_dict: Dict[str, Any]) -> Optional[Any]:
        """Determine the focus person."""
        # If focus_person_id is specified, use it
        if self.focus_person_id:
            return people_dict.get(self.focus_person_id)
        
        # Otherwise, find the most connected person (heuristic: most children + parents)
        max_connections = 0
        focus = None
        
        for person in people_list:
            connections = 0
            
            # Count parents
            if hasattr(person, 'father') and person.father:
                connections += 1
            if hasattr(person, 'mother') and person.mother:
                connections += 1
            
            # Count children
            if hasattr(person, 'children'):
                connections += len(list(person.children))
            
            # Count spouses
            if hasattr(person, 'get_events'):
                marriages = person.get_events('marriage') or []
                connections += len(marriages)
            
            if connections > max_connections:
                max_connections = connections
                focus = person
        
        return focus if focus else (people_list[0] if people_list else None)
    
    def _analyze_relationships(self, focus_person: Any, people_dict: Dict[str, Any]) -> Dict[str, Dict]:
        """
        Analyze relationships using BFS from focus person.
        
        Returns dict mapping person_id to relationship info:
        {
            'steps': int,
            'generation': int,
            'is_blood': bool,
            'type': str,
            'path': List[str]
        }
        """
        focus_id = self._get_id(focus_person)
        relationships = {
            focus_id: {
                'steps': 0,
                'generation': 0,
                'is_blood': True,
                'type': 'self',
                'path': [focus_id]
            }
        }
        
        # BFS queue: (person_id, steps, generation, is_blood, relationship_type, path)
        queue = deque([(focus_id, 0, 0, True, 'self', [focus_id])])
        visited = {focus_id}
        
        while queue:
            current_id, steps, generation, is_blood, rel_type, path = queue.popleft()
            current_person = people_dict.get(current_id)
            
            if not current_person:
                continue
            
            # Explore parents (blood relatives, go up generation)
            for parent_attr in ['father', 'mother']:
                if hasattr(current_person, parent_attr):
                    parent_id = getattr(current_person, parent_attr)
                    if parent_id and isinstance(parent_id, str) and parent_id not in visited:
                        visited.add(parent_id)
                        new_gen = generation - 1
                        new_type = self._determine_relationship_type(steps + 1, new_gen, is_blood=True, is_ancestor=True)
                        new_path = path + [parent_id]
                        relationships[parent_id] = {
                            'steps': steps + 1,
                            'generation': new_gen,
                            'is_blood': True,
                            'type': new_type,
                            'path': new_path
                        }
                        queue.append((parent_id, steps + 1, new_gen, True, new_type, new_path))
            
            # Explore children (blood relatives, go down generation)
            if hasattr(current_person, 'children'):
                for child in current_person.children:
                    child_id = self._get_id(child) if hasattr(child, 'xref_id') else child
                    if isinstance(child_id, str) and child_id not in visited:
                        visited.add(child_id)
                        new_gen = generation + 1
                        new_type = self._determine_relationship_type(steps + 1, new_gen, is_blood=True, is_ancestor=False)
                        new_path = path + [child_id]
                        relationships[child_id] = {
                            'steps': steps + 1,
                            'generation': new_gen,
                            'is_blood': True,
                            'type': new_type,
                            'path': new_path
                        }
                        queue.append((child_id, steps + 1, new_gen, True, new_type, new_path))
            
            # Explore spouses (relatives by marriage, same generation)
            if hasattr(current_person, 'get_events'):
                marriages = current_person.get_events('marriage') or []
                for marriage in marriages:
                    spouse = self._get_partner(marriage, current_person)
                    if spouse:
                        spouse_id = self._get_id(spouse)
                        if spouse_id not in visited:
                            visited.add(spouse_id)
                            new_type = 'spouse' if steps == 0 else 'in-law'
                            new_path = path + [spouse_id]
                            relationships[spouse_id] = {
                                'steps': steps + 1,
                                'generation': generation,
                                'is_blood': False,
                                'type': new_type,
                                'path': new_path
                            }
                            queue.append((spouse_id, steps + 1, generation, False, new_type, new_path))
        
        return relationships
    
    def _determine_relationship_type(self, steps: int, generation: int, is_blood: bool, is_ancestor: bool = None) -> str:
        """Determine relationship type based on steps and generation."""
        if steps == 0:
            return 'self'
        
        if not is_blood:
            return 'in-law' if steps > 1 else 'spouse'
        
        # Direct ancestors
        if generation < 0:
            if generation == -1:
                return 'parent'
            elif generation == -2:
                return 'grandparent'
            elif generation == -3:
                return 'great-grandparent'
            else:
                return 'ancestor'
        
        # Direct descendants
        elif generation > 0:
            if generation == 1:
                return 'child'
            elif generation == 2:
                return 'grandchild'
            elif generation == 3:
                return 'great-grandchild'
            else:
                return 'descendant'
        
        # Same generation (siblings, cousins)
        else:
            if steps == 1:
                return 'sibling'
            elif steps == 2:
                return 'cousin/aunt/uncle'
            elif steps == 3:
                return 'cousin/great-aunt/uncle'
            else:
                return f'relative ({steps} steps away)'
    
    def _generation_label(self, generation: int) -> str:
        """Convert generation number to label."""
        if generation == 0:
            return 'Same generation'
        elif generation > 0:
            if generation == 1:
                return '+1 generation (children)'
            elif generation == 2:
                return '+2 generations (grandchildren)'
            else:
                return f'+{generation} generations'
        else:
            if generation == -1:
                return '-1 generation (parents)'
            elif generation == -2:
                return '-2 generations (grandparents)'
            else:
                return f'{generation} generations'
    
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
    
    def _get_name(self, person: Any) -> str:
        """Get person's name."""
        if hasattr(person, 'name'):
            return person.name
        return f"Unknown ({self._get_id(person)})"

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from geo_gedcom.app_hooks import AppHooks

from geo_gedcom.enrichment.model import DateRange, Issue, Provenance, EnrichedPerson
from geo_gedcom.enrichment.date_utils import subtract_days, coerce_to_single_date, year_num, add_years, sub_years, calculate_age_at_event
from .base import BaseRule, register_rule

@register_rule
@dataclass
class ParentChildBoundsRule(BaseRule):
    rule_id: str = "parent_child_bounds"
    min_mother_age: int = 11
    max_mother_age: int = 66
    min_father_age: int = 12
    max_father_age: int = 93
    infer_event_updates: bool = False  # Whether to infer event updates
    confidence: float = 0.7
    app_hooks: Optional[AppHooks] = None

    def apply(
        self,
        enriched_people: Dict[str, EnrichedPerson],
        original_people: Dict[str, Any],
        issues: List[Issue],
        app_hooks: Optional[AppHooks] = None,
        rule_num: int = None,
        total_rules: int = None,
    ) -> bool:
        changed = False
        
        # Build rule prefix
        prefix = f"Enrichment ({rule_num}/{total_rules}): " if rule_num and total_rules else "Enrichment: "
        
        for idx, (person_id, enriched_person) in enumerate(enriched_people.items()):
            if idx % 100 == 0:
                self._report_step(
                    info=f"{prefix}Applying {self.rule_id} to person {person_id} ({idx + 1}/{len(enriched_people)})",
                    target=len(enriched_people),
                    reset_counter=(idx == 0),
                    plus_step=100,
                )
            if self._stop_requested(logger_stop_message="Geolocation process stopped by user."):
                break

            child_birth = enriched_person.birth_range()
            if not child_birth:
                continue

            child_birth_latest = child_birth.latest
            if child_birth_latest is None:
                continue

            for parent in enriched_person.parents:
                parent_enriched = enriched_people.get(parent.id)
                if not parent_enriched:
                    continue

                # Determine if parent is mother or father based on sex
                parent_sex = parent_enriched.person.sex if hasattr(parent_enriched, 'person') else None
                if parent_sex == 'F':
                    min_age = self.min_mother_age
                    max_age = self.max_mother_age
                    parent_type = "mother"
                elif parent_sex == 'M':
                    min_age = self.min_father_age
                    max_age = self.max_father_age
                    parent_type = "father"
                else:
                    # Default to more conservative father ages if sex unknown
                    min_age = self.min_father_age
                    max_age = self.max_father_age
                    parent_type = "parent"

                # Check if parent and child have known birth dates that are incompatible
                parent_birth_date = parent_enriched.get_event_date('birth')
                child_birth_date = enriched_person.get_event_date('birth')
                
                if parent_birth_date and child_birth_date:
                    age_at_birth = calculate_age_at_event(parent_birth_date, child_birth_date)
                    if age_at_birth is not None:
                        if age_at_birth < min_age:
                            issue = Issue(
                                person_id=person_id,
                                issue_type="parent_child_bounds",
                                message=f"Parent {parent.id} ({parent_type}) was only {age_at_birth} years old when child {person_id} was born (minimum expected: {min_age}).",
                                severity="warning",
                                related_person_ids=(parent.id,)
                            )
                            issues.append(issue)
                            enriched_person.issues.append(issue)
                        elif age_at_birth > max_age:
                            issue = Issue(
                                person_id=person_id,
                                issue_type="parent_child_bounds",
                                message=f"Parent {parent.id} ({parent_type}) was {age_at_birth} years old when child {person_id} was born (maximum expected: {max_age}).",
                                severity="warning",
                                related_person_ids=(parent.id,)
                            )
                            issues.append(issue)
                            enriched_person.issues.append(issue)

        return changed

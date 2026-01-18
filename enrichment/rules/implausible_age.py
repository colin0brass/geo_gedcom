from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date
from typing import Any, Dict, List, Optional

from geo_gedcom.app_hooks import AppHooks

from geo_gedcom.enrichment.model import DateRange, InferredEvent, Issue, Provenance, EnrichedPerson
from geo_gedcom.enrichment.date_utils import coerce_to_single_date, year_num, add_years
from .base import BaseRule, register_rule


@register_rule
@dataclass
class ImplausibleAgeRule(BaseRule):
    """
    Check for people without death dates who would be implausibly old if still alive.
    
    If a person has a birth date but no death date, and their age would exceed
    max_age_years (default 122, the verified oldest human lifespan), this rule:
    - Creates an issue noting the implausible age
    - Optionally infers a death date range (birth + min_death_age to birth + max_age)
    """
    rule_id: str = "implausible_age"
    max_age_years: int = 122  # Jeanne Calment's verified age
    min_death_age_years: int = 0  # Minimum reasonable age for death inference
    infer_event_updates: bool = True  # Whether to infer event updates
    confidence: float = 0.7
    app_hooks: Optional[AppHooks] = None

    def apply(
        self,
        enriched_people: Dict[str, EnrichedPerson],
        original_people: Dict[str, Any],
        issues: List[Issue],
        app_hooks: Optional[AppHooks] = None,
    ) -> bool:
        changed = False
        current_year = _date.today().year
        
        for idx, (person_id, enriched_person) in enumerate(enriched_people.items()):
            if idx % 100 == 0:
                self._report_step(
                    info=f"Applying {self.rule_id} to person {person_id} ({idx + 1}/{len(enriched_people)})",
                    target=len(enriched_people),
                    reset_counter=(idx == 0),
                    plus_step=100,
                )
            
            if self._stop_requested(logger_stop_message="Enrichment process stopped by user."):
                break
            
            # Skip if person already has a death event (recorded or inferred)
            if enriched_person.has_event('death'):
                continue
            
            # Get birth date
            birth_date = enriched_person.get_event_date('birth')
            if not birth_date:
                continue
            
            # Get birth year
            birth_year = year_num(birth_date)
            if not birth_year:
                continue
            
            # Calculate age if alive today
            age_if_alive = current_year - birth_year
            
            # Check if implausibly old
            if age_if_alive > self.max_age_years:
                # Build the issue message
                message = (f"Person would be {age_if_alive} years old if alive today (born {birth_year}), "
                          f"which exceeds maximum plausible age of {self.max_age_years}")
                if self.infer_event_updates:
                    message += "; inferred death date range will be added"
                
                # Create an issue
                issue = Issue(
                    person_id=person_id,
                    issue_type="implausible_age",
                    message=message,
                    severity="warning"
                )
                issues.append(issue)
                enriched_person.issues.append(issue)
                
                # Optionally infer death date range
                if self.infer_event_updates:
                    # Infer death between min_death_age and max_age after birth
                    earliest_death = add_years(birth_date, self.min_death_age_years)
                    latest_death = add_years(birth_date, self.max_age_years)
                    
                    if earliest_death and latest_death:
                        death_range = DateRange(earliest=earliest_death, latest=latest_death)
                        
                        provenance = Provenance(
                            rule_id=self.rule_id,
                            notes=f"Inferred death date based on implausible age ({age_if_alive} years)"
                        )
                        
                        # Try to tighten the death date bound
                        if enriched_person.tighten_date_bound('death', death_range, provenance):
                            changed = True
                        
                        # Add an inferred death event if none exists
                        if 'death' not in enriched_person.inferred_events:
                            inferred_death = InferredEvent(
                                tag='death',
                                date_range=death_range,
                                place=None,
                                provenance=provenance
                            )
                            enriched_person.inferred_events['death'] = inferred_death
                            changed = True
        
        return changed

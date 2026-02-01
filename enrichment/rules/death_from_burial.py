from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

from geo_gedcom.app_hooks import AppHooks

from geo_gedcom.enrichment.model import DateRange, InferredEvent, Issue, Provenance, EnrichedPerson
from geo_gedcom.enrichment.date_utils import subtract_days, coerce_to_single_date, year_num
from .base import BaseRule, register_rule

@register_rule
@dataclass
class DeathFromBurialRule(BaseRule):
    rule_id: str = "death_from_burial"
    max_days: int = 14
    infer_event_updates: bool = True  # Whether to infer event updates
    confidence: float = 0.6
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

            # Check if death event already exists (using lowercase 'death')
            if 'death' in enriched_person.inferred_events:
                continue

            # Check for burial event (using lowercase 'burial')
            burial_event = enriched_person.get_explicit_event('burial')
            if not burial_event:
                continue

            burial_date = burial_event.date
            burial_date_single = coerce_to_single_date(burial_date) if burial_date else None
            if not burial_date_single:
                continue

            # Only infer death event if infer_event_updates is enabled
            if self.infer_event_updates:
                earliest = subtract_days(burial_date_single, days=self.max_days)

                if earliest is not None:
                    inferred_death_date_range = DateRange(
                        earliest=earliest,
                        latest=burial_date_single
                    )
                else:
                    inferred_death_date_range = DateRange(
                        earliest=None,
                        latest=burial_date_single
                    )

                inferred_death_event = InferredEvent(
                    tag='death',  # Changed to lowercase
                    date_range=inferred_death_date_range,
                    place=burial_event.place,
                    confidence=self.confidence,
                    provenance=Provenance(
                        rule_id=self.rule_id,
                        inputs=(person_id,),
                        notes="Inferred death from burial event."
                    )
                )
                enriched_person.add_inferred_event(inferred_death_event)
                issue = Issue(
                    person_id=person_id,
                    issue_type="inferred_death_from_burial",
                    message=f"Inferred death event between {inferred_death_date_range.earliest} "
                            f"and {inferred_death_date_range.latest} based on burial event.",
                    severity="info"
                )
                issues.append(issue)
                enriched_person.issues.append(issue)
                changed = True

        return changed

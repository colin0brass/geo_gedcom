from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from geo_gedcom.app_hooks import AppHooks

from .config import EnrichmentConfig
from .model import EnrichedPerson, Issue
from .rules.base import EnrichmentRule

logger = logging.getLogger(__name__)

@dataclass
class EnrichmentResult:
    enriched_people: Dict[str, EnrichedPerson]
    issues: List[Issue] = field(default_factory=list)
    iterations: int = 0
    rule_runs: Dict[str, int] = field(default_factory=dict)  # rule_id -> times run

class EnrichmentPipeline:
    def __init__(self, config: EnrichmentConfig, rules: Sequence[EnrichmentRule], app_hooks: Optional['AppHooks'] = None) -> None:
        self.config = config
        self.rules = list(rules)
        self.app_hooks = app_hooks
        
        # Set app_hooks on all rules that support it
        for rule in self.rules:
            if hasattr(rule, 'app_hooks'):
                rule.app_hooks = app_hooks

    def run(
        self,
        original_people: Dict[str, Any],
        *,
        existing_people: Optional[Dict[str, EnrichedPerson]] = None,
    ) -> EnrichmentResult:
        enriched_people = existing_people or {
            pid: EnrichedPerson(person=person)
            for pid, person in original_people.items()
        }
        issues: List[Issue] = []
        rule_runs: Dict[str, int] = {}

        # Set up progress tracking
        num_people = len(original_people)
        enabled_rules = [r for r in self.rules if self.config.rule_enabled(r.rule_id)]
        total_steps = self.config.max_iterations * len(enabled_rules)
        self._report_step(info="Enriching data", target=total_steps, reset_counter=True, plus_step=0)

        # Iterate until stable or max_iterations reached
        for iteration in range(self.config.max_iterations):
            any_changes = False
            rule_num = 0
            for rule in self.rules:
                if not self.config.rule_enabled(rule.rule_id):
                    continue
                
                rule_num += 1
                
                # Check for stop request
                if self._stop_requested("Enrichment stopped by user"):
                    logger.info(f"Enrichment stopped at iteration {iteration + 1}")
                    return EnrichmentResult(
                        enriched_people=enriched_people,
                        issues=issues,
                        iterations=iteration + 1,
                        rule_runs=rule_runs,
                    )
                
                # Pass app_hooks and rule numbering to rules that accept them
                try:
                    changed = rule.apply(enriched_people, original_people, issues, app_hooks=self.app_hooks, rule_num=rule_num, total_rules=len(enabled_rules))
                except TypeError:
                    # Rule doesn't accept new parameters
                    try:
                        changed = rule.apply(enriched_people, original_people, issues, app_hooks=self.app_hooks)
                    except TypeError:
                        # Rule doesn't accept app_hooks parameter
                        changed = rule.apply(enriched_people, original_people, issues)
                rule_runs[rule.rule_id] = rule_runs.get(rule.rule_id, 0) + 1
                if changed:
                    any_changes = True
                
                # Report progress after each rule
                self._report_step(plus_step=1)
            
            if not any_changes:
                break

        return EnrichmentResult(
            enriched_people=enriched_people,
            issues=issues,
            iterations=iteration + 1,
            rule_runs=rule_runs,
    )

    def _report_step(self, info: str = "", target: Optional[int] = None, reset_counter: bool = False, plus_step: int = 0) -> None:
        """
        Report a step via app hooks if available. (Private method)

        Args:
            info (str): Information message.
            target (int): Target count for progress.
            reset_counter (bool): Whether to reset the counter.
            plus_step (int): Incremental step count.
        """
        if self.app_hooks and callable(getattr(self.app_hooks, "report_step", None)):
            self.app_hooks.report_step(info=info, target=target, reset_counter=reset_counter, plus_step=plus_step)
        else:
            logger.debug(info)

    def _stop_requested(self, logger_stop_message: str = "Stop requested by user") -> bool:
        """
        Check if stop has been requested via app hooks. (Private method)

        Returns:
            bool: True if stop requested, False otherwise.
        """
        if self.app_hooks and callable(getattr(self.app_hooks, "stop_requested", None)):
            if self.app_hooks.stop_requested():
                if logger_stop_message:
                    logger.debug(logger_stop_message)
                return True
        return False
    
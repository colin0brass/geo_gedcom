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

        # Iterate until stable or max_iterations reached
        for iteration in range(self.config.max_iterations):
            any_changes = False
            for rule in self.rules:
                if not self.config.rule_enabled(rule.rule_id):
                    continue
                changed = rule.apply(enriched_people, original_people, issues)
                rule_runs[rule.rule_id] = rule_runs.get(rule.rule_id, 0) + 1
                if changed:
                    any_changes = True
            if not any_changes:
                break

        return EnrichmentResult(
            enriched_people=enriched_people,
            issues=issues,
            iterations=iteration + 1,
            rule_runs=rule_runs,
    )

    def _report_step(self, info: str = "", target: int = 0, reset_counter: bool = False, plus_step: int = 0) -> None:
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
            logger.info(info)

    def _stop_requested(self, logger_stop_message: str = "Stop requested by user") -> bool:
        """
        Check if stop has been requested via app hooks. (Private method)

        Returns:
            bool: True if stop requested, False otherwise.
        """
        if self.app_hooks and callable(getattr(self.app_hooks, "stop_requested", None)):
            if self.app_hooks.stop_requested():
                if logger_stop_message:
                    logger.info(logger_stop_message)
                return True
        return False
    
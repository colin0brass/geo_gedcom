"""Enrichment rules: Domain-specific inference and validation for genealogical data.

Built-in rules:
    - DeathFromBurialRule: Infers death date from burial event
    - ParentChildBoundsRule: Validates parent-child age relationships
    - ImplausibleAgeRule: Detects implausibly long lifespans (120+ years)

Extensibility:
    Create custom rules by:
        1. Subclass BaseRule or EnrichmentRule Protocol
        2. Implement run(person) → list[InferredEvent]
        3. Use @register_rule decorator for automatic registration

Example:
    >>> from geo_gedcom.enrichment.rules import BaseRule, register_rule
    >>> @register_rule
    ... class MyCustomRule(BaseRule):
    ...     def run(self, person):
    ...         # custom inference logic
    ...         return inferred_events
"""

from .base import EnrichmentRule
from .base import BaseRule
from .base import RuleStats
from .base import register_rule
from .base import get_rule_registry
from .death_from_burial import DeathFromBurialRule
from .parent_child_bounds import ParentChildBoundsRule
from .implausible_age import ImplausibleAgeRule

__all__ = [
    'EnrichmentRule',
    'BaseRule',
    'RuleStats',
    'register_rule',
    'get_rule_registry',
    'DeathFromBurialRule',
    'ParentChildBoundsRule',
    'ImplausibleAgeRule',
]

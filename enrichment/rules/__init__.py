"""
Enrichment rules for genealogical data.

This module contains built-in enrichment rules that apply domain knowledge
to infer missing information and detect data quality issues.

Built-in rules:
    - DeathFromBurialRule: Infers death events from burial records
    - ParentChildBoundsRule: Validates parent-child age compatibility
    - ImplausibleAgeRule: Detects implausibly old people (120+ years)

Custom rules can be created by subclassing BaseRule and using @register_rule.
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

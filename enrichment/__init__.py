"""
Enrichment module for genealogical data.

This module provides a flexible pipeline for enriching genealogical data by:
- Inferring missing events (e.g., death from burial)
- Detecting data quality issues (e.g., implausible ages)
- Tightening date bounds using relationships
- Generating confidence-rated inferences with provenance

Main components:
    - Enrichment: High-level interface for running enrichment
    - EnrichmentPipeline: Orchestrates rule execution
    - EnrichmentConfig: Configuration management
    - EnrichedPerson: Wrapper with inferred data and issues
    - Built-in rules: DeathFromBurialRule, ParentChildBoundsRule, ImplausibleAgeRule

Example:
    >>> from geo_gedcom.enrichment import Enrichment
    >>> enrichment = Enrichment(people=gedcom_people)
    >>> result = enrichment.run()
    >>> for person_id, enriched in result.people.items():
    ...     for issue in enriched.issues:
    ...         print(f"{issue.severity}: {issue.message}")
"""

from .model import EnrichedPerson
from .model import InferredEvent
from .model import Provenance
from .model import Confidence
from .model import DateRange
from .model import Issue
from .pipeline import EnrichmentPipeline
from .pipeline import EnrichmentResult
from .config import EnrichmentConfig
from .rules import EnrichmentRule
from .rules import BaseRule
from .rules import RuleStats
from .rules import DeathFromBurialRule
from .rules import ParentChildBoundsRule
from .rules import ImplausibleAgeRule
from .defaults import get_default_rules
from .enrichment import Enrichment

__all__ = [
    'EnrichedPerson',
    'InferredEvent',
    'Provenance',
    'Confidence',
    'DateRange',
    'Issue',
    'EnrichmentPipeline',
    'EnrichmentResult',
    'EnrichmentConfig',
    'EnrichmentRule',
    'BaseRule',
    'RuleStats',
    'DeathFromBurialRule',
    'ParentChildBoundsRule',
    'ImplausibleAgeRule',
    'get_default_rules',
    'Enrichment',
]

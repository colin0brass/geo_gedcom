"""Enrichment module: Data quality improvement and inference pipeline for genealogical data.

Provides a flexible, pluggable pipeline for enriching genealogical data by:
    - Inferring missing events (e.g., death from burial, birth from marriage)
    - Detecting data quality issues (e.g., implausible ages, date inconsistencies)
    - Tightening date bounds using family relationships
    - Computing confidence scores for inferences
    - Tracking provenance (which rule produced which inference)

Core classes:
    - Enrichment: High-level interface for running enrichment
    - EnrichmentPipeline: Orchestrates rule execution and aggregates results
    - EnrichmentConfig: Configuration for pipeline behavior
    - EnrichedPerson: Wrapper containing inferred events and detected issues
    - EnrichmentResult: Output containing enriched people and aggregate statistics

Data models:
    - InferredEvent: Event inferred with confidence and provenance
    - Issue: Data quality issue with severity level and message
    - Provenance: Origin tracking (rule name, date, confidence)
    - Confidence: Confidence level (HIGH, MEDIUM, LOW)
    - DateRange: Date range with optional bounds

Built-in rules:
    - DeathFromBurialRule: Infers death from burial events
    - ParentChildBoundsRule: Validates parent-child age relationships
    - ImplausibleAgeRule: Flags people older than 120 years

Customization:
    Create custom rules by:
        1. Subclass BaseRule
        2. Implement run(person) method
        3. Use @register_rule decorator

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

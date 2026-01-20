"""
Built-in statistics collectors.

Import collectors here to automatically register them.
"""

from geo_gedcom.statistics.collectors.demographics import DemographicsCollector
from geo_gedcom.statistics.collectors.events import EventCompletenessCollector
from geo_gedcom.statistics.collectors.geographic import GeographicCollector
from geo_gedcom.statistics.collectors.gender import GenderCollector
from geo_gedcom.statistics.collectors.names import NamesCollector
from geo_gedcom.statistics.collectors.ages import AgesCollector
from geo_gedcom.statistics.collectors.births import BirthsCollector
from geo_gedcom.statistics.collectors.longevity import LongevityCollector
from geo_gedcom.statistics.collectors.timeline import TimelineCollector
from geo_gedcom.statistics.collectors.marriage import MarriageCollector
from geo_gedcom.statistics.collectors.children import ChildrenCollector
from geo_gedcom.statistics.collectors.relationship_status import RelationshipStatusCollector

__all__ = [
    'DemographicsCollector',
    'EventCompletenessCollector',
    'GeographicCollector',
    'GenderCollector',
    'NamesCollector',
    'AgesCollector',
    'BirthsCollector',
    'LongevityCollector',
    'TimelineCollector',
    'MarriageCollector',
    'ChildrenCollector',
    'RelationshipStatusCollector',
]

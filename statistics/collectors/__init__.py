"""
Built-in statistics collectors.

Import collectors here to automatically register them.
"""

from geo_gedcom.statistics.collectors.demographics import DemographicsCollector
from geo_gedcom.statistics.collectors.events import EventCompletenessCollector
from geo_gedcom.statistics.collectors.geographic import GeographicCollector

__all__ = [
    'DemographicsCollector',
    'EventCompletenessCollector',
    'GeographicCollector',
]

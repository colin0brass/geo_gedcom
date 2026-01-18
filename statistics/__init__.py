"""
Statistics module for genealogical data analysis.

This module provides aggregate statistical analysis of genealogical datasets.
Unlike the enrichment module which modifies individual person records, the
statistics module collects and analyzes data across the entire dataset.

Main components:
    - StatisticsCollector: Base class for creating custom statistics collectors
    - StatisticsPipeline: Orchestrates running multiple collectors
    - Built-in collectors: Common statistical analyses
"""

from geo_gedcom.statistics.base import StatisticsCollector, register_collector, get_collector_registry
from geo_gedcom.statistics.pipeline import StatisticsPipeline, StatisticsConfig
from geo_gedcom.statistics.model import Stats, StatValue
from geo_gedcom.statistics.statistics import Statistics

# Import collectors to ensure they're registered
from geo_gedcom.statistics import collectors

__all__ = [
    'StatisticsCollector',
    'register_collector',
    'get_collector_registry',
    'StatisticsPipeline',
    'StatisticsConfig',
    'Statistics',
    'Stats',
    'StatValue',
    'collectors',
]

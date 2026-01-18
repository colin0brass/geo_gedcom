"""
Base classes for statistics collectors.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from typing import Any, Dict, Iterable, Type

from geo_gedcom.statistics.model import Stats

logger = logging.getLogger(__name__)

# Collector Registry
_COLLECTOR_REGISTRY: Dict[str, Type['StatisticsCollector']] = {}


def register_collector(cls: Type['StatisticsCollector']) -> Type['StatisticsCollector']:
    """
    Decorator to register a collector class in the global registry.
    
    Usage:
        @register_collector
        @dataclass
        class MyCollector(StatisticsCollector):
            collector_id = "my_collector"
            ...
    """
    if hasattr(cls, 'collector_id'):
        _COLLECTOR_REGISTRY[cls.collector_id] = cls
        logger.debug(f"Registered statistics collector: {cls.collector_id}")
    else:
        logger.warning(f"Collector {cls.__name__} missing 'collector_id' attribute, not registered")
    return cls


def get_collector_registry() -> Dict[str, Type['StatisticsCollector']]:
    """Get the global collector registry."""
    return _COLLECTOR_REGISTRY.copy()


@dataclass
class StatisticsCollector(ABC):
    """
    Base class for statistics collectors.
    
    Collectors analyze a dataset and produce aggregate statistics.
    Unlike enrichment rules, they don't modify the data, only analyze it.
    
    Attributes:
        collector_id: Unique identifier for this collector
        enabled: Whether this collector is enabled (can be set via config)
    """
    collector_id: str = ""
    enabled: bool = True
    
    @abstractmethod
    def collect(self, people: Iterable[Any], existing_stats: Stats) -> Stats:
        """
        Collect statistics from the dataset.
        
        Args:
            people: Iterable of Person or EnrichedPerson objects
            existing_stats: Existing statistics object to add to
            
        Returns:
            Stats object with collected values
        """
        pass
    
    def __post_init__(self):
        """Validate collector configuration."""
        if not self.collector_id:
            raise ValueError(f"{self.__class__.__name__} must define collector_id")

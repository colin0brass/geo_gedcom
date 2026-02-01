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
        app_hooks: Optional application hooks for progress reporting
    """
    collector_id: str = ""
    enabled: bool = True
    app_hooks: Any = None
    
    @abstractmethod
    def collect(self, people: Iterable[Any], existing_stats: Stats, collector_num: int = None, total_collectors: int = None) -> Stats:
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
    
    def _report_step(self, info: str = "", target: int = None, reset_counter: bool = False, plus_step: int = 0) -> None:
        """Report a step via app hooks if available.
        
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
        """Check if stop has been requested via app hooks.
        
        Returns:
            bool: True if stop requested, False otherwise.
        """
        if self.app_hooks and callable(getattr(self.app_hooks, "stop_requested", None)):
            if self.app_hooks.stop_requested():
                if logger_stop_message:
                    logger.debug(logger_stop_message)
                return True
        return False

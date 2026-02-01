"""
Pipeline for running statistics collectors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Type
import yaml

from geo_gedcom.statistics.base import StatisticsCollector, get_collector_registry
from geo_gedcom.statistics.model import Stats

logger = logging.getLogger(__name__)


@dataclass
class StatisticsConfig:
    """
    Configuration for statistics collection.
    
    Attributes:
        collectors: Dict of collector_id -> enabled status
        config_file: Path to YAML config file (optional)
    """
    collectors: Dict[str, bool] = field(default_factory=dict)
    config_file: Optional[Path] = None
    
    def __post_init__(self) -> None:
        """Load configuration from file if config_file is specified and exists."""
        if self.config_file and Path(self.config_file).exists():
            self._load_from_file()
    
    def _load_from_file(self) -> None:
        """
        Load configuration from YAML file.
        
        Reads the 'statistics' section from the YAML file and extracts
        collector enable/disable settings.
        """
        try:
            with open(self.config_file, 'r') as f:
                data = yaml.safe_load(f) or {}
                statistics_config = data.get('statistics', {})
                
                # Load collector enabled/disabled settings
                collectors_config = statistics_config.get('collectors', {})
                for collector_id, settings in collectors_config.items():
                    if isinstance(settings, dict):
                        self.collectors[collector_id] = settings.get('enabled', True)
                    elif isinstance(settings, bool):
                        self.collectors[collector_id] = settings
                        
                logger.info(f"Loaded statistics config from {self.config_file}")
        except Exception as e:
            logger.warning(f"Failed to load statistics config from {self.config_file}: {e}")
    
    def is_enabled(self, collector_id: str) -> bool:
        """
        Check if a collector is enabled.
        
        Args:
            collector_id: Identifier of the collector to check
            
        Returns:
            True if enabled (default if not specified), False otherwise
        """
        return self.collectors.get(collector_id, True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StatisticsConfig:
        """
        Create configuration from dictionary.
        
        Useful for testing and programmatic configuration.
        
        Args:
            data: Dictionary with 'collectors' key mapping collector_id to enabled status
            
        Returns:
            StatisticsConfig instance
        """
        return cls(collectors=data.get('collectors', {}))


@dataclass
class StatisticsPipeline:
    """
    Pipeline for running statistics collectors on a dataset.
    
    Attributes:
        collectors: List of collector instances to run
        config: Configuration for the pipeline
        app_hooks: Optional application hooks for progress reporting
    """
    collectors: List[StatisticsCollector] = field(default_factory=list)
    config: StatisticsConfig = field(default_factory=StatisticsConfig)
    app_hooks: Optional[Any] = field(default=None)
    
    def __post_init__(self) -> None:
        """
        Initialize collectors from registry if none provided.
        
        If no collectors are explicitly provided, automatically loads
        all registered collectors from the global registry.
        """
        if not self.collectors:
            self._load_collectors_from_registry()
    
    def _load_collectors_from_registry(self) -> None:
        """
        Load all registered collectors with configuration applied.
        
        Instantiates each collector from the registry and applies the
        enabled/disabled setting from configuration.
        """
        registry = get_collector_registry()
        for collector_id, collector_cls in registry.items():
            enabled = self.config.is_enabled(collector_id)
            try:
                collector = collector_cls(enabled=enabled, app_hooks=self.app_hooks)
                self.collectors.append(collector)
                logger.debug(f"Loaded collector: {collector_id} (enabled={enabled})")
            except Exception as e:
                logger.error(f"Failed to load collector {collector_id}: {e}")
    
    def run(self, people: Iterable[Any]) -> Stats:
        """
        Run all enabled collectors on the dataset.
        
        Args:
            people: Iterable of Person or EnrichedPerson objects
            
        Returns:
            Stats object with all collected values
        """
        stats = Stats()
        
        # Convert to list to allow multiple passes if needed
        people_list = list(people)
        
        logger.debug(f"Running statistics on {len(people_list)} people")
        
        # Set up progress tracking
        enabled_collectors = [c for c in self.collectors if c.enabled]
        total_collectors = len(enabled_collectors)
        self._report_step(info="Collecting statistics", target=total_collectors, reset_counter=True, plus_step=0)
        
        collector_num = 0
        for idx, collector in enumerate(self.collectors):
            if not collector.enabled:
                logger.debug(f"Skipping disabled collector: {collector.collector_id}")
                continue
            
            collector_num += 1
            
            # Check for stop request
            if self._stop_requested("Statistics collection stopped by user"):
                logger.info(f"Statistics stopped after {idx} collectors")
                return stats
            
            try:
                logger.debug(f"Running collector: {collector.collector_id}")
                collector_stats = collector.collect(people_list, stats, collector_num, total_collectors)
                stats.merge(collector_stats)
                
                # Report progress after each collector
                self._report_step(plus_step=1)
            except Exception as e:
                logger.error(f"Error in collector {collector.collector_id}: {e}", exc_info=True)
        
        return stats
    
    def _report_step(self, info: str = "", target: Optional[int] = None, reset_counter: bool = False, plus_step: int = 0) -> None:
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
            logger.debug(info)

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

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import logging

from geo_gedcom.person import Person
from geo_gedcom.app_hooks import AppHooks
from .pipeline import StatisticsConfig, StatisticsPipeline
from .model import Stats

logger = logging.getLogger(__name__)


class Statistics:
    """
    High-level interface for collecting statistics from genealogical data.
    
    This is a convenience wrapper around StatisticsPipeline that provides
    a simpler API for common use cases.
    
    Example:
        # From gedcom_parser
        stats = Statistics(gedcom_parser=parser)
        results = stats.results  # Get Stats object
        
        # Standalone usage
        stats = Statistics(people=people_dict)
        results = stats.results
    """
    
    def __init__(
        self, 
        gedcom_parser=None,
        people: Optional[Dict[str, Person]] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        config_file: Optional[Path] = None,
        app_hooks: Optional[AppHooks] = None
    ) -> None:
        """
        Initialize statistics collection.
        
        Args:
            gedcom_parser: Optional GedcomParser instance to extract people from
            people: Optional dictionary of person_id -> Person objects
            config_dict: Dictionary to configure collectors (e.g., {'collectors': {'demographics': True}})
            config_file: Path to YAML config file
            app_hooks: Optional application hooks for progress reporting
        """
        self.app_hooks = app_hooks
        
        # Extract people from gedcom_parser if provided
        if gedcom_parser:
            people = getattr(gedcom_parser, 'people', {})
        
        if not people:
            logger.warning("No people data provided to Statistics")
            people = {}
        
        self.people = people
        
        # Create configuration
        if config_dict:
            self.config = StatisticsConfig.from_dict(config_dict)
        elif config_file:
            self.config = StatisticsConfig(config_file=config_file)
        else:
            # Use defaults - all collectors enabled
            self.config = StatisticsConfig()
        
        # Create pipeline
        self.pipeline = StatisticsPipeline(config=self.config)
        
        # Run analysis automatically
        self._results = None
        if people:
            self._results = self._analyze()
    
    def _analyze(self) -> Stats:
        """
        Run statistics collection on the people data.
        
        Returns:
            Stats object with collected statistics
        """
        logger.info(f"Collecting statistics on {len(self.people)} people")
        
        # Convert dict to iterable of Person objects
        if isinstance(self.people, dict):
            people_list = list(self.people.values())
        else:
            people_list = list(self.people)
        
        return self.pipeline.run(people_list)
    
    @property
    def results(self) -> Optional[Stats]:
        """Get the statistics results."""
        return self._results
    
    def analyze(self, people: Optional[Iterable[Person]] = None) -> Stats:
        """
        Analyze the given people data.
        
        Args:
            people: Optional iterable of Person objects. If None, uses self.people.
        
        Returns:
            Stats object with collected statistics
        """
        if people is not None:
            if isinstance(people, dict):
                self.people = people
            else:
                # Convert iterable to dict
                self.people = {getattr(p, 'xref_id', str(i)): p for i, p in enumerate(people)}
        
        self._results = self._analyze()
        return self._results
    
    def get_value(self, category: str, name: str, default=None):
        """
        Convenience method to get a specific statistic value.
        
        Args:
            category: Category name (e.g., 'demographics', 'events')
            name: Statistic name (e.g., 'total_people')
            default: Default value if not found
            
        Returns:
            The statistic value or default
        """
        if self._results:
            return self._results.get_value(category, name, default)
        return default
    
    def get_category(self, category: str) -> Dict[str, Any]:
        """
        Get all statistics in a category.
        
        Args:
            category: Category name (e.g., 'demographics')
            
        Returns:
            Dictionary of statistic names to values
        """
        if self._results:
            return self._results.get_category(category)
        return {}
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Export all statistics as a dictionary.
        
        Returns:
            Dictionary of categories to statistics
        """
        if self._results:
            return self._results.to_dict()
        return {}

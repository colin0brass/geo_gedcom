from __future__ import annotations

from pathlib import Path
from typing import Optional
from geo_gedcom.person import Person
from geo_gedcom.app_hooks import AppHooks
from . import EnrichmentConfig, EnrichmentPipeline, EnrichmentResult, get_default_rules

class Enrichment:
    def __init__(
        self, 
        config_dict=None, 
        config_yaml: Optional[Path] = None,
        people: Optional[dict[str, Person]] = None, 
        app_hooks: Optional['AppHooks'] = None
    ) -> None:
        """
        Initialize enrichment with optional configuration.
        
        Args:
            config_dict: Dictionary to override config values
            config_yaml: Path to YAML config file. If None, uses default config.yaml
            people: Optional initial people to enrich
            app_hooks: Optional application hooks for progress reporting
        """
        # Load from YAML first (or use defaults), then apply any dict overrides
        if not config_yaml and config_dict is None:
            config_yaml = Path(__file__).parent / "config.yaml"
        if not config_yaml.exists():
            raise FileNotFoundError(
                f"Default configuration file not found: {config_yaml}. "
            )
        else:
            self.config = EnrichmentConfig.from_yaml(config_yaml)
        
        # Apply dictionary overrides if provided
        if config_dict:
            self.config = EnrichmentConfig.from_dict({**self.config.__dict__, **config_dict})
        
        self.rules = get_default_rules(self.config)
        self.pipeline = EnrichmentPipeline(
            config=self.config,
            rules=self.rules,
            app_hooks=app_hooks
        )
        if people:
            self.enrich(people)

    def enrich(self, people=None) -> EnrichmentResult:
        """
        Enrich the given people data using the enrichment pipeline.
        
        Args:
            people: Optional list of people to enrich. If None, uses self.people.
        
        Returns:
            EnrichmentResult: The result of the enrichment process.
        """
        if people is None:
            people = self.people
        result = self.pipeline.run(original_people=people)
        self.people = result.enriched_people
        self.issues = result.issues
        return result
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple
import yaml

@dataclass
class EnrichmentConfig:
    """
    Configuration for the enrichment process.
    
    Loads all configuration values from config.yaml in the enrichment directory.
    """
    # General settings
    enabled: bool = field(init=False)
    max_iterations: int = field(init=False)

    # Age constraints - Person lifespan
    death_age_min: int = field(init=False)
    death_age_max: int = field(init=False)
    
    # Age constraints - Parents
    mother_age_min: int = field(init=False)
    mother_age_max: int = field(init=False)
    father_age_min: int = field(init=False)
    father_age_max: int = field(init=False)

    # Inference windows
    burial_to_death_max_days: int = field(init=False)
    baptism_to_birth_max_days: int = field(init=False)

    # Rule event date updates
    rules_infer_event_date_updates: Dict[str, bool] = field(init=False)

    # Rule confidence levels (nested dict)
    rule_confidence: Dict[str, float] = field(init=False)

    # Rule toggles (nested dict)
    rules_enabled: Dict[str, bool] = field(init=False)

    def __post_init__(self):
        """Load configuration from YAML file."""
        yaml_path = Path(__file__).parent / "config.yaml"
        
        if not yaml_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {yaml_path}. "
                "Please ensure config.yaml exists in the enrichment directory."
            )
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f) or {}
            
            # Set fields from YAML
            for key in self.__dataclass_fields__.keys():
                if key in config_dict:
                    object.__setattr__(self, key, config_dict[key])
                else:
                    raise ValueError(f"Required configuration field '{key}' not found in config.yaml")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing config.yaml: {e}")

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> EnrichmentConfig:
        """
        Load configuration from a specific YAML file.

        Args:
            yaml_path: Path to YAML config file.

        Returns:
            EnrichmentConfig: Configuration instance loaded from YAML.
        """
        if not yaml_path or not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing {yaml_path}: {e}")
        
        return cls.from_dict(config_dict, yaml_path)

    def rule_enabled(self, rule_id: str) -> bool:
        # default: enabled unless explicitly false
        return self.rules_enabled.get(rule_id, True)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any], yaml_path: Optional[Path] = None) -> EnrichmentConfig:
        """
        Create configuration from a dictionary.

        Args:
            config_dict (Dict[str, Any]): Dictionary with configuration values.
            yaml_path: Optional path to save as temporary YAML for loading.
        Returns:
            EnrichmentConfig: Configuration instance.
        """
        # Create a temporary instance by directly setting attributes
        instance = object.__new__(cls)
        
        # Set all fields from dictionary
        for key in cls.__dataclass_fields__.keys():
            if key in config_dict:
                object.__setattr__(instance, key, config_dict[key])
            else:
                # Try to get from default config.yaml
                default_yaml = Path(__file__).parent / "config.yaml"
                if default_yaml.exists():
                    with open(default_yaml, 'r', encoding='utf-8') as f:
                        default_dict = yaml.safe_load(f) or {}
                    if key in default_dict:
                        object.__setattr__(instance, key, default_dict[key])
                    else:
                        raise ValueError(f"Required configuration field '{key}' not found")
                else:
                    raise ValueError(f"Required configuration field '{key}' not found and no default config.yaml")
        
        return instance
        valid_fields = {k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)
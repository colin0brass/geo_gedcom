"""
Default enrichment rules configuration.
"""
from __future__ import annotations

from typing import List

from .config import EnrichmentConfig
from .rules import EnrichmentRule, get_rule_registry


# Rule parameter mapping: maps config fields to rule constructor parameters
RULE_PARAM_MAP = {
    'death_from_burial': {
        'max_days': 'burial_to_death_max_days',
        'infer_event_updates': lambda cfg: cfg.rules_infer_event_date_updates.get('death_from_burial', True),
        'confidence': lambda cfg: cfg.rule_confidence.get('death_from_burial', 0.6),
    },
    'parent_child_bounds': {
        'min_mother_age': 'mother_age_min',
        'max_mother_age': 'mother_age_max',
        'min_father_age': 'father_age_min',
        'max_father_age': 'father_age_max',
        'infer_event_updates': lambda cfg: cfg.rules_infer_event_date_updates.get('parent_child_bounds', True),
        'confidence': lambda cfg: cfg.rule_confidence.get('parent_child_bounds', 0.5),
    },
    'implausible_age': {
        'max_age_years': 'death_age_max',
        'min_death_age_years': 'death_age_min',
        'infer_event_updates': lambda cfg: cfg.rules_infer_event_date_updates.get('implausible_age', True),
        'confidence': lambda cfg: cfg.rule_confidence.get('implausible_age', 0.7)
    }
}


def get_default_rules(config: EnrichmentConfig) -> List[EnrichmentRule]:
    """
    Create default enrichment rules based on config using the rule registry.
    
    Automatically discovers all registered rules and instantiates them with
    appropriate config values.
    
    Args:
        config: EnrichmentConfig instance with rule parameters.
        
    Returns:
        List[EnrichmentRule]: List of configured rules from the registry.
    """
    registry = get_rule_registry()
    rules = []
    
    for rule_id, rule_class in registry.items():
        # Check if rule is enabled in config
        if not config.rule_enabled(rule_id):
            continue
        
        # Get parameter mapping for this rule
        param_map = RULE_PARAM_MAP.get(rule_id, {})
        
        # Build kwargs from config
        kwargs = {}
        for param_name, config_key in param_map.items():
            if callable(config_key):
                # It's a lambda or function
                kwargs[param_name] = config_key(config)
            else:
                # It's a config attribute name
                kwargs[param_name] = getattr(config, config_key)
        
        # Instantiate the rule
        rules.append(rule_class(**kwargs))
    
    return rules
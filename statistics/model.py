"""
Data models for statistics module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


StatValue = Union[int, float, str, List[Any], Dict[str, Any]]


@dataclass
class Stats:
    """
    Container for statistical results collected from a dataset.
    
    Statistics are organized into categories (e.g., 'demographics', 'events')
    with named values within each category.
    """
    categories: Dict[str, Dict[str, StatValue]] = field(default_factory=dict)
    
    def add_value(self, category: str, name: str, value: StatValue) -> None:
        """Add a statistical value to a category."""
        if category not in self.categories:
            self.categories[category] = {}
        self.categories[category][name] = value
    
    def get_value(self, category: str, name: str, default: Optional[StatValue] = None) -> Optional[StatValue]:
        """Get a statistical value from a category."""
        return self.categories.get(category, {}).get(name, default)
    
    def get_category(self, category: str) -> Dict[str, StatValue]:
        """Get all values in a category."""
        return self.categories.get(category, {})
    
    def merge(self, other: Stats) -> None:
        """Merge another Stats object into this one."""
        for category, values in other.categories.items():
            if category not in self.categories:
                self.categories[category] = {}
            self.categories[category].update(values)
    
    def to_dict(self) -> Dict[str, Dict[str, StatValue]]:
        """Convert to a plain dictionary."""
        return dict(self.categories)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, StatValue]]) -> Stats:
        """Create from a plain dictionary."""
        return cls(categories=data)

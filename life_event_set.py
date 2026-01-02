"""
life_event_set.py - geo_gedcom life event extraction and modeling for GEDCOM data.

This module provides the LifeEventSet class and utilities for extracting and modeling
life events (birth, death, marriage, etc.) from GEDCOM data. It supports:
    - Parsing event records
    - Normalizing event dates and locations
    - Associating events with people and families

Module: geo_gedcom.life_event_set
Author: @colin0brass
Last updated: 2025-12-06
"""

from typing import Optional, List, Union, Dict, TypeVar, Generic
from .life_event import LifeEvent
from .marriage import Marriage

T = TypeVar('T', bound=Union[LifeEvent, Marriage])

class LifeEventSet(Generic[T]):
    """
    Represents a set of life events for a person, organized by event_type.

    Attributes:
        events (Dict[str, List[LifeEvent|Marriage]]): Dictionary mapping event_type to list of LifeEvent or Marriage.
        event_types (List[str]): List of allowed event types. If empty, all types are allowed unless allow_new_event_types is False.
        allow_new_event_types (bool): Whether to allow new event types not in event_types.
    """
    def __init__(self, event_types: Optional[List[str]] = None, allow_new_event_types: bool = False) -> None:
        """
        Initialize an empty LifeEventSet.

        Args:
            event_types (Optional[List[str]]): List of allowed event types. If None or empty, all types are allowed unless allow_new_event_types is False.
            allow_new_event_types (bool): Whether to allow new event types not in event_types.
        """
        self.events: Dict[str, List[Union[LifeEvent, Marriage]]] = {}
        self.event_types: List[str] = event_types if event_types else []
        self.allow_new_event_types: bool = allow_new_event_types

    def set_event_types(self, event_types: List[str], allow_new_event_types: Optional[bool] = None) -> None:
        """
        Set the allowed event types for this LifeEventSet.

        Args:
            event_types (List[str]): List of allowed event types.
            allow_new_event_types (Optional[bool]): Whether to allow new event types not in event_types.
        """
        self.event_types = event_types
        if allow_new_event_types is not None:
            self.allow_new_event_types = allow_new_event_types

    def add_events(self, event_type: str, events: Union[LifeEvent, Marriage, List[Union[LifeEvent, Marriage]]]) -> None:
        """
        Add a LifeEvent, Marriage, or list of them to the set, organized by event_type (event.what).

        Args:
            event_type (str): The type of event (e.g., 'BIRT', 'DEAT').
            events (LifeEvent, Marriage, or List[LifeEvent|Marriage]): The event(s) to add.

        Raises:
            ValueError: If event_type is 'all' or not allowed.
        """
        if event_type == 'all':
            raise ValueError("Cannot add events to 'all' event_type.")
        if self.event_types and event_type not in self.event_types and not self.allow_new_event_types:
            raise ValueError(f"Event type '{event_type}' not recognized and new event types are not allowed.")
        # Accept both single event and list of events
        if not isinstance(events, list):
            events = [events]
        if event_type not in self.events:
            self.events[event_type] = []
        for ev in events:
            if ev is not None:
                self.events[event_type].append(ev)

    def add_event(self, event_type: str, event: Union[LifeEvent, Marriage]) -> None:
        """
        Add a single LifeEvent or Marriage to the set, organized by event_type (event.what).

        Args:
            event_type (str): The type of event (e.g., 'BIRT', 'DEAT').
            event (LifeEvent or Marriage): The event to add.
        """
        self.add_events(event_type, event)

    def get_events(self, event_type: str, date_order: bool = False) -> List[Union[LifeEvent, Marriage]]:
        """
        Get all events of a specific type, or all events if event_type == 'all'.

        Args:
            event_type (str): The type of event to filter by (e.g., 'BIRT', 'DEAT'), or 'all' for all events.
            date_order (bool): If True, return events sorted by date (if possible).

        Returns:
            List[LifeEvent|Marriage]: List of matching life events.
        """
        if event_type == 'all':
            events: List[Union[LifeEvent, Marriage]] = []
            for ev_list in self.events.values():
                events.extend(ev_list)
        else:
            events = self.events.get(event_type, [])
        if date_order:
            def get_date(ev):
                d = getattr(ev, 'date', None)
                # Try to get a sortable value (year_num or resolved or str)
                if hasattr(d, 'year_num') and d.year_num is not None:
                    return d.year_num
                if hasattr(d, 'resolved') and d.resolved is not None:
                    return d.resolved
                if hasattr(d, 'date') and d.date is not None:
                    return d.date
                return str(d) if d is not None else ''
            try:
                events = sorted(events, key=get_date)
            except Exception as e:
                # If sorting fails, return unsorted
                pass
        return events

    def get_event(self, event_type: str, date_order: bool = False) -> Optional[Union[LifeEvent, Marriage]]:
        """
        Get the first event of a specific type (optionally sorted by date).

        Args:
            event_type (str): The type of event to filter by (e.g., 'BIRT', 'DEAT').
            date_order (bool): If True, return the earliest event by date (if possible).

        Returns:
            LifeEvent or Marriage or None: The first matching life event, or None if not found.
        """
        events = self.get_events(event_type, date_order=date_order)
        return events[0] if events else None

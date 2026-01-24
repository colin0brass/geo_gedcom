from geo_gedcom.person import Person
from geo_gedcom.life_event import LifeEvent
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple, Literal

from geo_gedcom.enrichment.date_utils import calculate_age_at_event

# Use lowercase event types to match Person class
EventTag = str # e.g., 'birth', 'death', 'burial', etc.

@dataclass(frozen=True)
class DateRange:
    """
    Represents uncertainty without forcing a single inferred date.
    Use None for open-ended bounds.
    """
    earliest: Optional[Any] = None # where Any is a date type (e.g. GedcomDate, datetime, int year)
    latest: Optional[Any] = None
    
    def is_empty(self) -> bool:
        """Check if both bounds are None."""
        return self.earliest is None and self.latest is None
    
    def intersect(self, other: 'DateRange') -> 'DateRange':
        """Return the intersection of two DateRanges."""
        new_earliest = max(self.earliest, other.earliest) if self.earliest and other.earliest else self.earliest or other.earliest
        new_latest = min(self.latest, other.latest) if self.latest and other.latest else self.latest or other.latest
        if new_earliest and new_latest and new_earliest > new_latest:
            return DateRange()  # Empty range
        return DateRange(earliest=new_earliest, latest=new_latest)
    
    def contains(self, date: Any) -> bool:
        """Check if a date is within the range."""
        if self.earliest and date < self.earliest:
            return False
        if self.latest and date > self.latest:
            return False
        return True

Confidence = float  # e.g., 0.0 to 1.0

@dataclass
class Provenance:
    rule_id: str
    inputs: Tuple[str, ...] = ()
    notes: str = ""

@dataclass
class InferredEvent:
    """
    Class representing an inferred life event for a person.

    Attributes:
        tag (EventTag): The event type tag (lowercase like 'birth', 'death', 'burial').
        date_range (Optional[DateRange]): Date range for the event.
        place (Optional[str]): Place where the event occurred.
        confidence (Confidence): Confidence level (0.0 to 1.0).
        provenance (Provenance): Information about how this was inferred.
    """
    tag: EventTag
    date_range: Optional[DateRange] = None
    place: Optional[str] = None
    confidence: Confidence = 0.5
    provenance: Provenance = field(default_factory=lambda: Provenance(rule_id="unknown"))

@dataclass(frozen=True)
class Issue:
    issue_type: str
    severity: Literal["info", "warning", "error"]
    message: str
    person_id: Optional[str] = None
    related_person_ids: Tuple[str, ...] = ()

@dataclass
class EnrichedPerson:
    """
    Class representing an enriched person with additional metadata.

    Attributes:
        person (Person): The base Person object.
        inferred_events (Dict[EventTag, InferredEvent]): Inferred events by event type.
        date_bounds (Dict[EventTag, DateRange]): Tightened date bounds by event type.
        place_overrides (Dict[EventTag, str]): Place overrides by event type.
        issues (List[Issue]): List of issues found during enrichment.
    """
    person: Person
    
    inferred_events: Dict[EventTag, InferredEvent] = field(default_factory=dict)
    date_bounds: Dict[EventTag, DateRange] = field(default_factory=dict)
    place_overrides: Dict[EventTag, str] = field(default_factory=dict)
    issues: List[Issue] = field(default_factory=list)

    # Identity helpers
    @property
    def id(self) -> str:
        """Get the person's unique identifier."""
        return self.person.xref_id
    
    @property
    def display_name(self) -> str:
        """Get the person's display name."""
        return self.person.name
    
    # recording inferred data
    def add_inferred_event(self, inferred_event: InferredEvent) -> None:
        """
        Add an inferred event to the person.
        
        If an event of the same type already exists, replaces it only if the new
        event has higher confidence.
        
        Args:
            inferred_event: The inferred event to add
        """
        existing = self.inferred_events.get(inferred_event.tag)
        if existing is None or inferred_event.confidence > existing.confidence:
            self.inferred_events[inferred_event.tag] = inferred_event

    def tighten_date_bound(self, tag: EventTag, bound: DateRange, provenance: Provenance, confidence: Confidence = 0.4) -> bool:
        """
        Tighten the date bounds for a given event tag.
        
        Returns:
            bool: True if the bound was successfully tightened, False if conflict detected
        """
        existing_bound = self.date_bounds.get(tag)
        new_bound = existing_bound.intersect(bound) if existing_bound else bound  # Ensure new_bound is valid
        if new_bound.is_empty():
            self.issues.append(Issue(
                severity="warning",
                issue_type="conflicting_date_bounds",
                message=f"Conflicting bounds for {tag}: {existing_bound} vs {bound} results in empty range.",
                person_id=self.id
            ))
            return False  # Do not update to an empty range
        self.date_bounds[tag] = new_bound
        return True

    def override_place(self, tag: EventTag, place: str, provenance: Provenance, confidence: Confidence = 0.4) -> None:
        """
        Override the place for a given event tag.
        
        Args:
            tag: Event type tag (e.g., 'birth', 'death')
            place: Place name to set
            provenance: Information about how this was determined
            confidence: Confidence level (0.0 to 1.0)
        """
        self.place_overrides[tag] = place

    def get_explicit_event(self, tag: EventTag) -> Optional[LifeEvent]:
        """
        Get the explicit LifeEvent for a given tag, if it exists.
        
        Args:
            tag: Event type tag (e.g., 'birth', 'death', 'burial')
            
        Returns:
            The LifeEvent if found, None otherwise
        """
        # tag is already lowercase (e.g., 'birth', 'death', 'burial')
        event = self.person.get_event(tag)
        return event
    
    def has_event(self, tag: EventTag) -> bool:
        """
        Check if person has an event (explicit or inferred) for the given tag.
        
        Args:
            tag: Event type tag (e.g., 'birth', 'death', 'burial')
            
        Returns:
            bool: True if person has explicit or inferred event, False otherwise
        """
        # Check if there's an explicit event
        explicit_event = self.get_explicit_event(tag)
        if explicit_event:
            return True
        
        # Check if there's an inferred event
        if tag in self.inferred_events:
            return True
        
        return False
    
    def get_event_date(self, tag: EventTag) -> Optional[Any]:
        """
        Get the date for an event (explicit or inferred).
        
        Args:
            tag: Event type tag (e.g., 'birth', 'death', 'burial')
            
        Returns:
            The date from explicit event if available, otherwise from inferred event date_range
        """
        # First check explicit event
        explicit_event = self.get_explicit_event(tag)
        if explicit_event and explicit_event.date:
            return explicit_event.date
        
        # Check inferred event - return the earliest date from date_range
        inferred_event = self.inferred_events.get(tag)
        if inferred_event and inferred_event.date_range:
            # Return earliest date from range
            return inferred_event.date_range.earliest
        
        return None
    
    def best_place(self, tag: EventTag) -> Optional[str]:
        """
        Get the best place for a given event tag, considering overrides.
        
        Preference order:
        1. Explicit event place
        2. Place override (propagated/inferred)
        3. Inferred event place
        
        Args:
            tag: Event type tag (e.g., 'birth', 'death')
            
        Returns:
            Place name if found, None otherwise
        """
        explicit_event = self.get_explicit_event(tag)
        if explicit_event and explicit_event.place:
            return explicit_event.place
        if tag in self.place_overrides:
            return self.place_overrides[tag]
        inferred_event = self.inferred_events.get(tag)
        if inferred_event and inferred_event.place:
            return inferred_event.place
        return None

    def best_date_range(self, tag: EventTag) -> Optional[DateRange]:
        """
        Get the best date range for a given event tag.
        
        Preference order:
        1. Explicit exact date → DateRange(date, date)
        2. Explicit date range (if model supports it)
        3. Tightened bounds
        4. Inferred event date_range
        
        Args:
            tag: Event type tag (e.g., 'birth', 'death')
            
        Returns:
            DateRange if found, None otherwise
        """
        explicit_event = self.get_explicit_event(tag)
        if explicit_event and explicit_event.date and explicit_event.date.resolved:
            resolved_date = explicit_event.date.resolved
            if isinstance(resolved_date, tuple) and len(resolved_date) == 2:
                return DateRange(earliest=resolved_date[0], latest=resolved_date[1])
            else:
                return DateRange(earliest=resolved_date, latest=resolved_date)
        if tag in self.date_bounds:
            return self.date_bounds[tag]
        inferred_event = self.inferred_events.get(tag)
        if inferred_event and inferred_event.date_range:
            return inferred_event.date_range
        return None
    
    # Convenience shortcuts for common stats
    def birth_range(self) -> Optional[DateRange]:
        """Get birth date range, falls back to baptism if birth not available."""
        return self.best_date_range("birth") or self.best_date_range("baptism")

    def death_range(self) -> Optional[DateRange]:
        """Get death date range, falls back to burial if death not available."""
        return self.best_date_range("death") or self.best_date_range("burial")
    
    def is_deceased(self) -> bool:
        """Check if person is deceased based on death or burial events."""
        return self.has_event("death") or self.has_event("burial")
    
    def lifespan_age_years(self) -> Optional[int]:
        """
        Calculate lifespan in years.
        
        Returns:
            Age in years if both birth and death dates available, None otherwise
        """
        birth_date = self.get_event_date("birth")
        death_date = self.get_event_date("death") or self.get_event_date("burial")
        if birth_date and death_date:
            return calculate_age_at_event(birth_date, death_date)
        return None

    # ---------- Relationship helpers (delegated) ----------

    @property
    def parents(self) -> Iterable[Any]:
        """Get the person's parents (delegates to underlying Person object)."""
        return getattr(self.person, "parents", []) or []

    @property
    def children(self) -> Iterable[Any]:
        """Get the person's children (delegates to underlying Person object)."""
        return getattr(self.person, "children", []) or []

    @property
    def partners(self) -> Iterable[Any]:
        """Get the person's partners/spouses (delegates to underlying Person object)."""
        return getattr(self.person, "spouses", []) or getattr(self.person, "partners", []) or []

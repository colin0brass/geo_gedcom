from typing import List, TYPE_CHECKING
from geo_gedcom.life_event import LifeEvent

if TYPE_CHECKING:
    from geo_gedcom.person import Person

class Marriage:
    """Represents a marriage event between two or more persons.

    Attributes:
        people_list (List[Person]): The list of people involved in the marriage.
        event (LifeEvent): The marriage event details.
    """

    __slots__ = ['people_list', 'event']

    def __init__(self, people_list: List["Person"] = None, marriage_event: LifeEvent = None):
        """Initializes a Marriage instance.

        Args:
            people_list (List["Person"], optional): List of people in the marriage. Defaults to empty list.
            marriage_event (LifeEvent, optional): The marriage event details. Defaults to None.
        """
        self.people_list : List["Person"] = people_list if people_list is not None else []
        self.event : LifeEvent = marriage_event if marriage_event is not None else None

    def __str__(self) -> str:
        """Returns a string representation of the marriage.

        Returns:
            str: String describing the marriage participants and event.
        """
        people_str = ', '.join([str(person) for person in self.people_list])
        return f"Marriage(people=[{people_str}], event={self.event})"
    
    def __repr__(self) -> str:
        """Returns a detailed string representation for debugging.

        Returns:
            str: Debug string for the marriage.
        """
        people_repr = ', '.join([repr(person) for person in self.people_list])
        return f'Marriage(people=[{people_repr}], event={repr(self.event)})'
    
    def other_partners(self, person: "Person") -> List["Person"]:
        """Return a list of partners excluding the given person.

        Args:
            person (Person): The person to exclude.

        Returns:
            List[Person]: List of other partners in the marriage.
        """
        return [p for p in self.people_list if p != person]

    def partner(self, person: "Person") -> "Person":
        """Return the first partner that is not the given person.

        Args:
            person (Person): The person to exclude.
        Returns:
            Person: The first other partner in the marriage, or None if not found.
        """
        return self.other_partners(person)[0] if self.other_partners(person) else None

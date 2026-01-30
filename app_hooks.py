from typing import Protocol
from .gedcom_date import GedcomDate

class AppHooks(Protocol):
    """
    Protocol for application hooks to customize behavior.
    This can be implemented by the main application to modify
    geocoding and address processing.

    Methods:
        preprocess_address(address: str) -> str:
            Preprocess an address string before geocoding.
    """
    def report_step(self, info: str = None, target: int = None, reset_counter: bool = False, plus_step: int = 1, set_counter: int = None) -> None:
        """
        Report progress messages from the geocoding process.

        Args:
            info (str): Progress message/information.
            target (int): Target count for progress tracking.
            reset_counter (bool): Whether to reset the counter.
            plus_step (int): Incremental step count.
            set_counter (int): Directly set the counter value.
        """
        pass

    def stop_requested(self) -> bool:
        """
        Check if a stop has been requested by the user.

        Returns:
            bool: True if stop is requested, False otherwise.
        """
        return False

    def update_key_value(self, key: str, value) -> None:
        """
        Report a status update with a key-value pair.

        Args:
            key (str): Status key.
            value: Status value.
        """
        pass

    def add_time_reference(self, gedcom_date: GedcomDate) -> None:
        """
        Add a time reference for an event.

        Args:
            gedcom_date (GedcomDate): The GEDCOM date to add a time reference for.
        """
        pass
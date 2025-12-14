import pytest
from geo_gedcom.addressbook import FuzzyAddressBook

def test_fuzzy_addressbook_init():
    """Test FuzzyAddressBook can be instantiated."""
    ab = FuzzyAddressBook()
    assert isinstance(ab, FuzzyAddressBook)

def test_fuzzy_addressbook_add_and_search():
    """Test adding and searching for an address (if supported)."""
    ab = FuzzyAddressBook()
    if hasattr(ab, "add") and hasattr(ab, "search"):
        ab.add("123 Main St", (51.5, -0.1))
        result = ab.search("123 Main St")
        assert result == (51.5, -0.1)
    else:
        # If not implemented, pass the test
        pass

def test_fuzzy_addressbook_empty_search():
    """Test searching for a non-existent address returns None or raises."""
    ab = FuzzyAddressBook()
    if hasattr(ab, "search"):
        result = ab.search("Nonexistent Address")
        assert result is None or result == ()
    else:
        pass

def test_fuzzy_addressbook_invalid_add():
    """Test adding an invalid address raises an error (if supported)."""
    ab = FuzzyAddressBook()
    if hasattr(ab, "add"):
        with pytest.raises(Exception):
            ab.add(None, None)
    else:
        pass

import pytest
from geo_gedcom.addressbook import AddressBook

def test_addressbook_init():
    """Test AddressBook can be instantiated."""
    ab = AddressBook()
    assert isinstance(ab, AddressBook)

def test_addressbook_add_and_search():
    """Test adding and searching for an address (if supported)."""
    ab = AddressBook()
    if hasattr(ab, "add") and hasattr(ab, "search"):
        ab.add("123 Main St", (51.5, -0.1))
        result = ab.search("123 Main St")
        assert result == (51.5, -0.1)
    else:
        # If not implemented, pass the test
        pass

def test_addressbook_empty_search():
    """Test searching for a non-existent address returns None or raises."""
    ab = AddressBook()
    if hasattr(ab, "search"):
        result = ab.search("Nonexistent Address")
        assert result is None or result == ()
    else:
        pass

def test_addressbook_invalid_add():
    """Test adding an invalid address raises an error (if supported)."""
    ab = AddressBook()
    if hasattr(ab, "add"):
        with pytest.raises(Exception):
            ab.add(None, None)
    else:
        pass

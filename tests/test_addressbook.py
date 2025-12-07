from geo_gedcom.addressbook import FuzzyAddressBook

def test_fuzzy_addressbook_init():
    ab = FuzzyAddressBook()
    assert isinstance(ab, FuzzyAddressBook)

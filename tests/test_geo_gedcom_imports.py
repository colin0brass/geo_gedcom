import pytest


@pytest.mark.parametrize(
    "symbol_name",
    [
        "Gedcom",
        "GedcomParser",
        "Person",
        "LifeEvent",
        "Location",
        "LatLon",
        "AddressBook",
        "GedcomDate",
    ],
)
def test_import_symbol(symbol_name):
    """Test that each key symbol can be imported from geo_gedcom."""
    module = __import__("geo_gedcom", fromlist=[symbol_name])
    symbol = getattr(module, symbol_name, None)
    assert symbol is not None, f"{symbol_name} could not be imported"


def test_import_failure():
    """Test that importing a non-existent symbol raises ImportError or AttributeError."""
    with pytest.raises((ImportError, AttributeError)):
        from geo_gedcom import NotARealClass

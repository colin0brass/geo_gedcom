import pytest
from geo_gedcom import Person
from geo_gedcom import LifeEvent
from geo_gedcom.gedcom_date import GedcomDate

@pytest.fixture
def mock_event() -> callable:
    def _event(year=None, month=None, place=None, lat=None, lon=None) -> LifeEvent:
        date_str = f"{year} {month}" if year and month else str(year) if year else ""
        date = GedcomDate(date_str if date_str.strip() else None)
        latlon = None
        if lat is not None and lon is not None:
            from geo_gedcom import LatLon
            latlon = LatLon(lat, lon)
        return LifeEvent(place=place, date=date, latlon=latlon)
    return _event

def test_person_init():
    p = Person("I1")
    assert p.xref_id == "I1"
    assert p.name is None

@pytest.mark.parametrize(
    "name,firstname,surname,maidenname",
    [
        ("Herbert Campbell /Westmorland/", "Herbert Campbell", "Westmorland", None),
        ("Herbert /Westmorland/", "Herbert", "Westmorland", None),
        ("Herbert C /Westmorland/", "Herbert C", "Westmorland", None),
    ]
)
def test_person_multiple_names(name, firstname, surname, maidenname):
    p = Person("I635")
    p.name = name
    p.firstname = firstname
    p.surname = surname
    p.maidenname = maidenname
    assert p.name.startswith("Herbert")
    assert p.surname == "Westmorland"

def test_person_birth_full_date_place(mock_event):
    p = Person("I635")
    p.add_event('birth', mock_event(year=1893, month="DEC", place="Ryde, Isle of Wight, England"))
    assert p.get_event('birth').date.year_num == 1893
    assert p.get_event('birth').place == "Ryde, Isle of Wight, England"
    assert p.get_event('birth').date.single.month == "DEC"

@pytest.mark.parametrize("year", [1893, 1894])
def test_person_birth_year_only(mock_event, year):
    p = Person("I635")
    p.add_event('birth', mock_event(year=year, place="Ryde, Isle of Wight, England"))
    assert p.get_event('birth').date.year_num == year

def test_person_birth_range(mock_event):
    p = Person("I635")
    p.add_event('birth', mock_event(year=1894, place="Isle of Wight, England"))
    assert p.get_event('birth').place == "Isle of Wight, England"

def test_person_residence_event(mock_event):
    p = Person("I635")
    p.add_event('residence', mock_event(year=1925, place="Berkshire, England"))
    assert p.get_event('residence').date.year_num == 1925
    assert p.get_event('residence').place == "Berkshire, England"

def test_person_military_event(mock_event):
    p = Person("I635")
    p.add_event('military', mock_event(year=1916))
    assert p.get_event('military').date.year_num == 1916

def test_person_arrival_departure_events(mock_event):
    p = Person("I635")
    p.add_event('arrival', mock_event(year=1934, place="London, London, England"))
    p.add_event('departure', mock_event(year=1934, place="England"))
    assert p.get_event('arrival').place == "London, London, England"
    assert p.get_event('departure').place == "England"

def test_person_baptism_event(mock_event):
    p = Person("I635")
    p.add_event('baptism', mock_event(year=1894, place="Ryde, Isle of Wight, England"))
    assert p.get_event('baptism').place == "Ryde, Isle of Wight, England"

def test_person_death_event(mock_event):
    p = Person("I635")
    p.add_event('death', mock_event(year=1972, place="Winchester, Hampshire, England"))
    assert p.get_event('death').date.year_num == 1972
    assert p.get_event('death').place == "Winchester, Hampshire, England"

def test_person_family_relationships():
    p = Person("I635")
    p.family_spouse = ["F2513", "F259"]
    p.family_child = ["F2515", "F258"]
    assert "F2513" in p.family_spouse
    assert "F2515" in p.family_child

def test_person_geocoded_event(mock_event):
    p = Person("I635")
    p.add_event('birth', mock_event(year=1893, place="Ryde, Isle of Wight, England", lat=50.674908, lon=-1.301753))
    assert p.get_event('birth').location.latlon.lat == 50.674908
    assert p.get_event('birth').location.latlon.lon == -1.301753

def test_person_empty_fields():
    """Test Person with no events or relationships."""
    p = Person("I999")
    assert p.name is None
    assert p.get_event('birth') is None
    assert p.get_event('residence') is None
    assert p.family_spouse == []
    assert p.family_child == []

import pytest
from geo_gedcom import Person

@pytest.fixture
def mock_event():
    def _event(year=None, month=None, place=None, lat=None, lon=None):
        date = type('dt', (), {'year_num': year, 'single': type('sd', (), {'month': month})() if month else None})()
        latlon = type('ll', (), {'lat': lat, 'lon': lon})() if lat is not None and lon is not None else None
        return type('evt', (), {'date': date, 'place': place, 'latlon': latlon})()
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
    p.birth = mock_event(year=1893, month="DEC", place="Ryde, Isle of Wight, England")
    assert p.birth.date.year_num == 1893
    assert p.birth.place == "Ryde, Isle of Wight, England"
    assert p.birth.date.single.month == "DEC"

@pytest.mark.parametrize("year", [1893, 1894])
def test_person_birth_year_only(mock_event, year):
    p = Person("I635")
    p.birth = mock_event(year=year, place="Ryde, Isle of Wight, England")
    assert p.birth.date.year_num == year

def test_person_birth_range(mock_event):
    p = Person("I635")
    p.birth = mock_event(year=1894, place="Isle of Wight, England")
    assert p.birth.place == "Isle of Wight, England"

def test_person_residence_event(mock_event):
    p = Person("I635")
    p.residences = [mock_event(year=1925, place="Berkshire, England")]
    assert p.residences[0].date.year_num == 1925
    assert p.residences[0].place == "Berkshire, England"

def test_person_military_event(mock_event):
    p = Person("I635")
    p.military = [mock_event(year=1916)]
    assert p.military[0].date.year_num == 1916

def test_person_arrival_departure_events(mock_event):
    p = Person("I635")
    p.arrivals = [mock_event(year=1934, place="London, London, England")]
    p.departures = [mock_event(year=1934, place="England")]
    assert p.arrivals[0].place == "London, London, England"
    assert p.departures[0].place == "England"

def test_person_baptism_event(mock_event):
    p = Person("I635")
    p.baptism = mock_event(year=1894, place="Ryde, Isle of Wight, England")
    assert p.baptism.place == "Ryde, Isle of Wight, England"

def test_person_death_event(mock_event):
    p = Person("I635")
    p.death = mock_event(year=1972, place="Winchester, Hampshire, England")
    assert p.death.date.year_num == 1972
    assert p.death.place == "Winchester, Hampshire, England"

def test_person_family_relationships():
    p = Person("I635")
    p.family_spouse = ["F2513", "F259"]
    p.family_child = ["F2515", "F258"]
    assert "F2513" in p.family_spouse
    assert "F2515" in p.family_child

def test_person_geocoded_event(mock_event):
    p = Person("I635")
    p.birth = mock_event(year=1893, place="Ryde, Isle of Wight, England", lat=50.674908, lon=-1.301753)
    assert p.birth.latlon.lat == 50.674908
    assert p.birth.latlon.lon == -1.301753

def test_person_empty_fields():
    """Test Person with no events or relationships."""
    p = Person("I999")
    assert p.name is None
    assert p.birth is None
    assert p.residences == []
    assert p.family_spouse == []
    assert p.family_child == []

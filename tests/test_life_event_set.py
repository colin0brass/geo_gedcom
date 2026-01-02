import pytest
from geo_gedcom.life_event import LifeEvent
from geo_gedcom.marriage import Marriage
from geo_gedcom.life_event_set import LifeEventSet
from geo_gedcom.gedcom_date import GedcomDate

def make_event(what, year=None, place=None):
    return LifeEvent(place=place, date=GedcomDate(str(year)) if year else None, what=what)

def test_add_and_get_single_event():
    les = LifeEventSet()
    event = make_event('BIRT', 1900, 'London')
    les.add_event('BIRT', event)
    assert les.get_event('BIRT') == event
    assert les.get_events('BIRT') == [event]

def test_add_multiple_events():
    les = LifeEventSet()
    e1 = make_event('BIRT', 1900)
    e2 = make_event('BIRT', 1901)
    les.add_events('BIRT', [e1, e2])
    assert les.get_events('BIRT') == [e1, e2]

def test_get_events_all():
    les = LifeEventSet()
    e1 = make_event('BIRT', 1900)
    e2 = make_event('DEAT', 1950)
    les.add_event('BIRT', e1)
    les.add_event('DEAT', e2)
    all_events = les.get_events('all')
    assert set(all_events) == {e1, e2}

def test_event_type_enforcement():
    les = LifeEventSet(event_types=['BIRT'], allow_new_event_types=False)
    e1 = make_event('BIRT', 1900)
    les.add_event('BIRT', e1)
    with pytest.raises(ValueError):
        les.add_event('DEAT', make_event('DEAT', 1950))

def test_date_order_sorting():
    les = LifeEventSet()
    e1 = make_event('BIRT', 1902)
    e2 = make_event('BIRT', 1901)
    e3 = make_event('BIRT', 1903)
    les.add_events('BIRT', [e1, e2, e3])
    sorted_events = les.get_events('BIRT', date_order=True)
    assert [e.date.year_num for e in sorted_events] == [1901, 1902, 1903]

def test_get_event_with_date_order():
    les = LifeEventSet()
    e1 = make_event('BIRT', 1902)
    e2 = make_event('BIRT', 1901)
    les.add_events('BIRT', [e1, e2])
    first = les.get_event('BIRT', date_order=True)
    assert first.date.year_num == 1901

def test_add_events_invalid_type():
    les = LifeEventSet(event_types=['BIRT'], allow_new_event_types=False)
    with pytest.raises(ValueError):
        les.add_events('DEAT', make_event('DEAT', 1950))

def test_add_none_event():
    les = LifeEventSet()
    les.add_event('BIRT', None)
    assert les.get_events('BIRT') == []

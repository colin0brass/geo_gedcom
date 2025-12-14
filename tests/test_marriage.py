import pytest
from geo_gedcom.marriage import Marriage

class MockPerson:
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name
    def __repr__(self):
        return f"MockPerson({self.name!r})"
    def __eq__(self, other):
        return isinstance(other, MockPerson) and self.name == other.name

class MockLifeEvent:
    def __init__(self, desc):
        self.desc = desc
    def __str__(self):
        return self.desc
    def __repr__(self):
        return f"MockLifeEvent({self.desc!r})"

def test_marriage_init_defaults():
    m = Marriage()
    assert m.people_list == []
    assert m.event is None

def test_marriage_init_with_people_and_event():
    p1 = MockPerson("Alice")
    p2 = MockPerson("Bob")
    evt = MockLifeEvent("Married in Paris")
    m = Marriage([p1, p2], evt)
    assert m.people_list == [p1, p2]
    assert m.event == evt

def test_marriage_str_and_repr():
    p1 = MockPerson("Alice")
    p2 = MockPerson("Bob")
    evt = MockLifeEvent("Married in Paris")
    m = Marriage([p1, p2], evt)
    s = str(m)
    r = repr(m)
    assert "Alice" in s and "Bob" in s and "Married in Paris" in s
    assert "MockPerson('Alice')" in r and "MockLifeEvent('Married in Paris')" in r

def test_other_partners_and_partner():
    p1 = MockPerson("Alice")
    p2 = MockPerson("Bob")
    p3 = MockPerson("Charlie")
    m = Marriage([p1, p2, p3], MockLifeEvent("Group wedding"))
    # Exclude p1, should get [p2, p3]
    others = m.other_partners(p1)
    assert p2 in others and p3 in others and p1 not in others
    # partner() returns first other partner
    assert m.partner(p1) in [p2, p3]
    # If only one person, partner() returns None
    solo = Marriage([p1], MockLifeEvent("Solo wedding"))
    assert solo.partner(p1) is None

def test_other_partners_empty():
    p1 = MockPerson("Alice")
    m = Marriage([p1], MockLifeEvent("Solo wedding"))
    assert m.other_partners(p1) == []
    
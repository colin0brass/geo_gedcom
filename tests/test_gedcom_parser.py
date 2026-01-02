import pytest
from geo_gedcom.gedcom_parser import GedcomParser
from pathlib import Path
import tempfile

@pytest.fixture
def minimal_gedcom_file(tmp_path):
    content = (
        "0 @I1@ INDI\n"
        "1 NAME John /Doe/\n"
        "1 SEX M\n"
        "1 BIRT\n"
        "2 DATE 1 JAN 1900\n"
        "2 PLAC London, England\n"
        "1 DEAT\n"
        "2 DATE 1 JAN 1980\n"
        "2 PLAC London, England\n"
        "0 TRLR\n"
    )
    file_path = tmp_path / "test.ged"
    file_path.write_text(content)
    return file_path

def test_gedcom_parser_init_none():
    parser = GedcomParser(gedcom_file=None)
    assert parser.gedcom_file is None or isinstance(parser.gedcom_file, Path)

def test_gedcom_parser_init_file(minimal_gedcom_file):
    parser = GedcomParser(gedcom_file=minimal_gedcom_file)
    assert parser.gedcom_file is not None
    assert isinstance(parser.gedcom_file, Path)

def test_parse_people(minimal_gedcom_file):
    parser = GedcomParser(gedcom_file=minimal_gedcom_file)
    people = parser.parse_people()
    assert isinstance(people, dict)
    assert len(people) == 1
    person = next(iter(people.values()))
    assert person.name == "John Doe"
    assert person.sex == "M"
    assert person.get_event('birth') is not None
    assert person.get_event('birth').place == "London, England"
    assert person.get_event('death') is not None
    assert person.get_event('death').place == "London, England"

def test_parse_people_no_file(tmp_path):
    # Should not raise, but return empty dict
    parser = GedcomParser(gedcom_file=tmp_path / "nonexistent.ged")
    people = parser.parse_people()
    assert isinstance(people, dict)
    assert len(people) == 0

import pytest
from geo_gedcom.gedcom_parser import GedcomParser
import geo_gedcom.gedcom_parser as gedcom_parser_module
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
    file_path.write_text(content, encoding='utf-8')
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
    people = parser.people
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
    people = parser.people
    assert isinstance(people, dict)
    assert len(people) == 0


@pytest.fixture
def family_gedcom_file(tmp_path):
    content = (
        "0 HEAD\n"
        "1 SOUR pytest\n"
        "1 GEDC\n"
        "2 VERS 5.5.1\n"
        "1 CHAR UTF-8\n"
        "0 @I1@ INDI\n"
        "1 NAME John /Doe/\n"
        "1 SEX M\n"
        "1 BIRT\n"
        "2 DATE 1 JAN 1900\n"
        "2 PLAC London, England\n"
        "1 FAMS @F1@\n"
        "0 @I2@ INDI\n"
        "1 NAME Jane /Smith/\n"
        "1 SEX F\n"
        "1 BIRT\n"
        "2 DATE 1 JAN 1902\n"
        "2 PLAC Paris, France\n"
        "1 FAMS @F1@\n"
        "0 @F1@ FAM\n"
        "1 HUSB @I1@\n"
        "1 WIFE @I2@\n"
        "1 MARR\n"
        "2 DATE 1 JAN 1920\n"
        "2 PLAC Berlin, Germany\n"
        "0 TRLR\n"
    )
    file_path = tmp_path / "family.ged"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_get_full_address_list_from_people_without_second_parse(family_gedcom_file, monkeypatch):
    parser = GedcomParser(gedcom_file=family_gedcom_file)

    class _RaiseIfCalled:
        def __init__(self, *args, **kwargs):
            raise AssertionError("GedcomReader should not be called during address extraction")

    monkeypatch.setattr(gedcom_parser_module, "GedcomReader", _RaiseIfCalled)

    addresses = parser.get_full_address_list()

    assert "London, England" in addresses
    assert "Paris, France" in addresses
    assert "Berlin, Germany" in addresses

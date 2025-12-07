from geo_gedcom.canonical import Canonical

def test_canonical_strip_and_norm():
    canon = Canonical()
    assert canon._Canonical__strip_and_norm(' 123 Main St., Zürich ') == '123 Main St., Zurich'

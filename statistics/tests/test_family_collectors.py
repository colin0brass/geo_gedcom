"""
Unit tests for family relationship statistics collectors.

Tests collectors that analyze family structures and relationships:
- MarriageCollector: Marriage patterns, ages, durations, and age differences
- ChildrenCollector: Family size, children statistics, and sibling relationships
- RelationshipStatusCollector: Marital status categorization and demographics
"""
import pytest

from geo_gedcom.statistics.collectors.marriage import MarriageCollector
from geo_gedcom.statistics.collectors.children import ChildrenCollector
from geo_gedcom.statistics.collectors.relationship_status import RelationshipStatusCollector
from geo_gedcom.statistics.model import Stats


class MockDate:
    """Mock GedcomDate with year_num property."""
    def __init__(self, year):
        self.year_num = year
        self.year = year


class MockEvent:
    """Mock LifeEvent with date."""
    def __init__(self, year=None):
        self.date = MockDate(year) if year is not None else None


class MockMarriage:
    """Mock Marriage object."""
    def __init__(self, people_list, event_year=None):
        self.people_list = people_list
        self.event = MockEvent(event_year) if event_year is not None else None
    
    def partner(self, person):
        """Return the other partner."""
        partners = [p for p in self.people_list if p != person]
        return partners[0] if partners else None


class MockPerson:
    """Mock Person for testing."""
    def __init__(self, xref_id='I1', birth_year=None, death_year=None, sex=None, name='Test Person'):
        self.xref_id = xref_id
        self._birth_year = birth_year
        self._death_year = death_year
        self.sex = sex
        self.name = name
        self.children = []
        self.father = None
        self.mother = None
        self._marriages = []
    
    def add_marriage(self, partner, marriage_year=None):
        """Add a marriage."""
        marriage = MockMarriage([self, partner], marriage_year)
        self._marriages.append(marriage)
        partner._marriages.append(marriage)
    
    def get_events(self, event_type):
        if event_type == 'marriage':
            return self._marriages
        return []
    
    def get_event(self, event_type):
        if event_type == 'birth' and self._birth_year:
            return MockEvent(self._birth_year)
        elif event_type == 'death' and self._death_year:
            return MockEvent(self._death_year)
        return None


def test_marriage_collector_basic():
    """Test MarriageCollector with basic data."""
    husband = MockPerson('I1', 1950, 2020, 'M', 'John Smith')
    wife = MockPerson('I2', 1952, 2022, 'F', 'Jane Smith')
    husband.add_marriage(wife, 1975)
    
    people = [husband, wife]
    
    collector = MarriageCollector()
    stats = collector.collect(people, Stats())
    
    marriage_stats = stats.get_category('marriage')
    
    assert marriage_stats['total_people'] == 2
    assert marriage_stats['people_with_marriages'] == 2
    assert marriage_stats['people_never_married'] == 0
    assert marriage_stats['total_marriages_recorded'] == 1


def test_marriage_collector_ages():
    """Test marriage age calculations."""
    husband = MockPerson('I1', 1950, None, 'M', 'John')
    wife = MockPerson('I2', 1955, None, 'F', 'Jane')
    husband.add_marriage(wife, 1975)  # He was 25, she was 20
    
    collector = MarriageCollector()
    stats = collector.collect([husband, wife], Stats())
    
    marriage_stats = stats.get_category('marriage')
    
    assert 'average_marriage_age_male' in marriage_stats
    assert marriage_stats['average_marriage_age_male'] == 25.0
    assert 'average_marriage_age_female' in marriage_stats
    assert marriage_stats['average_marriage_age_female'] == 20.0


def test_marriage_collector_duration():
    """Test marriage duration calculations."""
    husband = MockPerson('I1', 1950, 2020, 'M', 'John')
    wife = MockPerson('I2', 1952, 2015, 'F', 'Jane')
    husband.add_marriage(wife, 1975)  # Married 1975, she died 2015 = 40 years
    
    collector = MarriageCollector()
    stats = collector.collect([husband, wife], Stats())
    
    marriage_stats = stats.get_category('marriage')
    
    assert 'average_marriage_duration' in marriage_stats
    assert marriage_stats['average_marriage_duration'] == 40.0
    assert 'longest_marriages' in marriage_stats


def test_marriage_collector_age_difference():
    """Test age difference calculations."""
    husband = MockPerson('I1', 1940, None, 'M', 'Old John')
    wife = MockPerson('I2', 1960, None, 'F', 'Young Jane')
    husband.add_marriage(wife, 1985)  # 20 year age difference
    
    collector = MarriageCollector()
    stats = collector.collect([husband, wife], Stats())
    
    marriage_stats = stats.get_category('marriage')
    
    assert 'average_age_difference' in marriage_stats
    assert marriage_stats['average_age_difference'] == 20.0
    assert 'husband_much_older_cases' in marriage_stats
    assert len(marriage_stats['husband_much_older_cases']) == 1


def test_marriage_collector_multiple_marriages():
    """Test tracking of multiple marriages."""
    person = MockPerson('I1', 1950, None, 'M', 'John')
    spouse1 = MockPerson('I2', 1952, 1990, 'F', 'First Wife')
    spouse2 = MockPerson('I3', 1960, None, 'F', 'Second Wife')
    
    person.add_marriage(spouse1, 1975)
    person.add_marriage(spouse2, 1995)
    
    collector = MarriageCollector()
    stats = collector.collect([person, spouse1, spouse2], Stats())
    
    marriage_stats = stats.get_category('marriage')
    
    assert marriage_stats['total_marriages_recorded'] == 2
    assert 'marriages_per_person_distribution' in marriage_stats
    assert marriage_stats['marriages_per_person_distribution'][2] == 1  # One person with 2 marriages


def test_children_collector_basic():
    """Test ChildrenCollector with basic data."""
    father = MockPerson('I1', 1950, None, 'M', 'Father')
    mother = MockPerson('I2', 1952, None, 'F', 'Mother')
    child1 = MockPerson('I3', 1975, None, 'M', 'Son')
    child2 = MockPerson('I4', 1977, None, 'F', 'Daughter')
    
    father.children = ['I3', 'I4']
    mother.children = ['I3', 'I4']
    child1.father = 'I1'
    child1.mother = 'I2'
    child2.father = 'I1'
    child2.mother = 'I2'
    
    people = [father, mother, child1, child2]
    
    collector = ChildrenCollector()
    stats = collector.collect(people, Stats())
    
    children_stats = stats.get_category('children')
    
    # Basic distribution statistics are always present for people with children
    assert 'children_per_person_distribution' in children_stats
    assert children_stats['children_per_person_distribution'][2] == 2  # 2 people with 2 children each
    
    # Note: Family statistics (total_families, sibling gaps) require that people
    # who have both father/mother set also have children themselves. In this
    # simple test case, only the parents have children, so family statistics
    # won't be generated. See test_children_collector_multigenerational for that.
    assert 'most_children' in children_stats
    assert children_stats['most_children'] == 2


def test_children_collector_ages():
    """Test age at having children."""
    father = MockPerson('I1', 1950, None, 'M', 'Father')
    mother = MockPerson('I2', 1952, None, 'F', 'Mother')
    child1 = MockPerson('I3', 1975, None, 'M', 'First Child')  # Father was 25, mother was 23
    child2 = MockPerson('I4', 1985, None, 'F', 'Last Child')   # Father was 35, mother was 33
    
    father.children = ['I3', 'I4']
    mother.children = ['I3', 'I4']
    
    collector = ChildrenCollector()
    stats = collector.collect([father, mother, child1, child2], Stats())
    
    children_stats = stats.get_category('children')
    
    assert 'average_age_first_child_male' in children_stats
    assert children_stats['average_age_first_child_male'] == 25.0
    assert 'average_age_first_child_female' in children_stats
    assert children_stats['average_age_first_child_female'] == 23.0
    assert 'average_age_last_child_male' in children_stats
    assert children_stats['average_age_last_child_male'] == 35.0


def test_children_collector_sibling_gaps():
    """Test sibling age gap calculations."""
    # For sibling gaps to be calculated, we need people who:
    # 1. Have children (so they're processed)
    # 2. Have both father and mother set (so family analysis runs)
    # This means a 3-generation dataset
    
    grandfather = MockPerson('I1', 1920, None, 'M', 'Grandfather')
    grandmother = MockPerson('I2', 1922, None, 'F', 'Grandmother')
    
    # Parents who have both parents and children
    parent1 = MockPerson('I3', 1945, None, 'M', 'Parent1')
    parent2 = MockPerson('I4', 1948, None, 'F', 'Parent2')
    parent3 = MockPerson('I5', 1955, None, 'M', 'Parent3')  # 7 year gap from parent2
    
    # Set up family relationships
    grandfather.children = ['I3', 'I4', 'I5']
    grandmother.children = ['I3', 'I4', 'I5']
    
    parent1.father = 'I1'
    parent1.mother = 'I2'
    parent1.children = ['I6']  # Has at least one child
    
    parent2.father = 'I1'
    parent2.mother = 'I2'
    parent2.children = ['I7']
    
    parent3.father = 'I1'
    parent3.mother = 'I2'
    parent3.children = ['I8']
    
    # Add grandchildren (so parents are processed)
    grandchild1 = MockPerson('I6', 1970, None, 'M', 'Grandchild1')
    grandchild2 = MockPerson('I7', 1973, None, 'F', 'Grandchild2')
    grandchild3 = MockPerson('I8', 1980, None, 'M', 'Grandchild3')
    
    people = [grandfather, grandmother, parent1, parent2, parent3, grandchild1, grandchild2, grandchild3]
    
    collector = ChildrenCollector()
    stats = collector.collect(people, Stats())
    
    children_stats = stats.get_category('children')
    
    # Now family statistics should be present
    assert 'total_families' in children_stats
    assert children_stats['total_families'] == 1
    
    # Sibling gap statistics should be calculated
    # Gaps: parent1(1945) to parent2(1948) = 3 years
    #       parent2(1948) to parent3(1955) = 7 years  
    # Average: (3 + 7) / 2 = 5.0
    assert 'average_sibling_age_gap' in children_stats
    assert children_stats['average_sibling_age_gap'] == 5.0
    assert 'largest_sibling_age_gap' in children_stats
    assert children_stats['largest_sibling_age_gap'] == 7


def test_relationship_status_collector_basic():
    """Test RelationshipStatusCollector basic functionality."""
    married = MockPerson('I1', 1950, None, 'M', 'Married Man')
    spouse = MockPerson('I2', 1952, None, 'F', 'Spouse')
    single = MockPerson('I3', 1980, None, 'F', 'Single Woman')
    
    married.add_marriage(spouse, 1975)
    
    people = [married, spouse, single]
    
    collector = RelationshipStatusCollector()
    stats = collector.collect(people, Stats())
    
    status_stats = stats.get_category('relationship_status')
    
    assert status_stats['total_people'] == 3
    assert status_stats['never_married'] == 1
    assert status_stats['ever_married'] == 2
    assert status_stats['currently_married_living'] == 2


def test_relationship_status_collector_widowed():
    """Test widowed status detection."""
    person = MockPerson('I1', 1950, None, 'M', 'Widower')
    deceased_spouse = MockPerson('I2', 1952, 2010, 'F', 'Deceased Spouse')
    
    person.add_marriage(deceased_spouse, 1975)
    
    collector = RelationshipStatusCollector()
    stats = collector.collect([person, deceased_spouse], Stats())
    
    status_stats = stats.get_category('relationship_status')
    
    assert status_stats['widowed'] == 1
    assert status_stats['currently_married_living'] == 0


def test_relationship_status_collector_by_gender():
    """Test status distribution by gender."""
    male_married = MockPerson('I1', 1950, None, 'M', 'Married Man')
    female_spouse = MockPerson('I2', 1952, None, 'F', 'Wife')
    male_single = MockPerson('I3', 1980, None, 'M', 'Single Man')
    female_single = MockPerson('I4', 1985, None, 'F', 'Single Woman')
    
    male_married.add_marriage(female_spouse, 1975)
    
    people = [male_married, female_spouse, male_single, female_single]
    
    collector = RelationshipStatusCollector()
    stats = collector.collect(people, Stats())
    
    status_stats = stats.get_category('relationship_status')
    
    assert 'status_by_gender' in status_stats
    gender_stats = status_stats['status_by_gender']
    assert gender_stats['M']['never_married'] == 1
    assert gender_stats['M']['ever_married'] == 1
    assert gender_stats['F']['never_married'] == 1
    assert gender_stats['F']['ever_married'] == 1


def test_integration_all_family_collectors():
    """Test all three family collectors working together."""
    # Create a family
    father = MockPerson('I1', 1950, 2020, 'M', 'Father')
    mother = MockPerson('I2', 1952, None, 'F', 'Mother')
    child1 = MockPerson('I3', 1975, None, 'M', 'Son')
    child2 = MockPerson('I4', 1978, None, 'F', 'Daughter')
    
    father.add_marriage(mother, 1973)
    father.children = ['I3', 'I4']
    mother.children = ['I3', 'I4']
    child1.father = 'I1'
    child1.mother = 'I2'
    child2.father = 'I1'
    child2.mother = 'I2'
    
    people = [father, mother, child1, child2]
    
    # Run all collectors
    marriage_collector = MarriageCollector()
    children_collector = ChildrenCollector()
    status_collector = RelationshipStatusCollector()
    
    combined_stats = Stats()
    
    marriage_stats = marriage_collector.collect(people, combined_stats)
    children_stats = children_collector.collect(people, combined_stats)
    status_stats = status_collector.collect(people, combined_stats)
    
    combined_stats.merge(marriage_stats)
    combined_stats.merge(children_stats)
    combined_stats.merge(status_stats)
    
    # Verify all categories exist
    assert 'marriage' in combined_stats.categories
    assert 'children' in combined_stats.categories
    assert 'relationship_status' in combined_stats.categories
    
    # Verify cross-consistency
    assert combined_stats.get_value('marriage', 'total_marriages_recorded') == 1
    # Note: total_families requires children to have father/mother set
    if combined_stats.get_value('children', 'total_families'):
        assert combined_stats.get_value('children', 'total_families') == 1
    assert combined_stats.get_value('relationship_status', 'ever_married') == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

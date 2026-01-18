"""
Example: Using the Statistics convenience wrapper.

This example shows how to use the high-level Statistics class
which provides a simple interface to the statistics module.
"""

from geo_gedcom.person import Person
from geo_gedcom.life_event import LifeEvent
from geo_gedcom.statistics import Statistics


def example_basic_usage():
    """Basic usage of Statistics wrapper."""
    
    # Create sample people
    people = {}
    
    person1 = Person(xref_id='I1')
    person1.name = 'John /Doe/'
    person1.add_event('birth', LifeEvent(date='1 JAN 1900', place='London, England', what='BIRT'))
    person1.add_event('death', LifeEvent(date='31 DEC 1975', place='London, England', what='DEAT'))
    people['I1'] = person1
    
    person2 = Person(xref_id='I2')
    person2.name = 'Jane /Smith/'
    person2.add_event('birth', LifeEvent(date='15 MAR 1925', place='Paris, France', what='BIRT'))
    people['I2'] = person2
    
    person3 = Person(xref_id='I3')
    person3.name = 'Bob /Johnson/'
    person3.add_event('birth', LifeEvent(date='20 JUL 1950', place='New York, USA', what='BIRT'))
    person3.add_event('burial', LifeEvent(date='15 AUG 2020', place='New York, USA', what='BURI'))
    people['I3'] = person3
    
    # Create Statistics instance
    stats = Statistics(people=people)
    
    # Access results
    print("=== Basic Statistics ===")
    print(f"Total people: {stats.get_value('demographics', 'total_people')}")
    print(f"Living: {stats.get_value('demographics', 'living')}")
    print(f"Deceased: {stats.get_value('demographics', 'deceased')}")
    
    avg_lifespan = stats.get_value('demographics', 'average_lifespan')
    if avg_lifespan:
        print(f"Average lifespan: {avg_lifespan} years")
    
    print("\n=== Event Completeness ===")
    completeness = stats.get_value('events', 'completeness', {})
    for event_type, data in completeness.items():
        print(f"{event_type.title()}: {data['total']} events")
        print(f"  - With dates: {data['date_percentage']}%")
        print(f"  - With places: {data['place_percentage']}%")
    
    print("\n=== Geographic Distribution ===")
    unique_places = stats.get_value('geographic', 'unique_places')
    print(f"Unique places: {unique_places}")
    
    countries = stats.get_value('geographic', 'countries', {})
    print(f"Countries: {list(countries.keys())}")
    
    # Export to dictionary
    all_stats = stats.to_dict()
    print(f"\nTotal categories collected: {len(all_stats)}")


def example_with_gedcom_parser():
    """Example using Statistics with a gedcom_parser-like object."""
    
    # Simulate a gedcom_parser object
    class MockGedcomParser:
        def __init__(self):
            self.people = {}
            p1 = Person(xref_id='I1')
            p1.name = 'Test Person'
            self.people['I1'] = p1
    
    parser = MockGedcomParser()
    
    # Initialize Statistics with parser
    stats = Statistics(gedcom_parser=parser)
    
    print(f"Total people from parser: {stats.get_value('demographics', 'total_people')}")


def example_with_config():
    """Example using Statistics with custom configuration."""
    
    people = {'I1': Person(xref_id='I1')}
    
    # Disable some collectors
    config = {
        'collectors': {
            'demographics': True,
            'event_completeness': False,  # Disable this
            'geographic': False,          # Disable this
        }
    }
    
    stats = Statistics(people=people, config_dict=config)
    
    # Only demographics should have results
    demographics = stats.get_category('demographics')
    print(f"Demographics collected: {len(demographics)} metrics")
    
    events = stats.get_category('events')
    print(f"Events collected: {len(events)} metrics (should be 0)")


if __name__ == '__main__':
    print("=== Example 1: Basic Usage ===\n")
    example_basic_usage()
    
    print("\n\n=== Example 2: With GedcomParser ===\n")
    example_with_gedcom_parser()
    
    print("\n\n=== Example 3: With Custom Config ===\n")
    example_with_config()

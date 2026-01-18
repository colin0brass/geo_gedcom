"""
Example: Using enrichment and statistics modules together.

This example demonstrates how to:
1. Load genealogical data
2. Enrich it with inferred events and date bounds
3. Collect aggregate statistics
4. Export results
"""

from geo_gedcom.enrichment import StatisticsPipeline as EnrichmentPipeline
from geo_gedcom.enrichment.config import EnrichmentConfig
from geo_gedcom.statistics import StatisticsPipeline, StatisticsConfig
import json


def example_enrichment_and_statistics():
    """Example workflow combining enrichment and statistics."""
    
    # Step 1: Load your genealogical data (example uses mock data)
    people = load_sample_data()
    print(f"Loaded {len(people)} people")
    
    # Step 2: Enrich the data
    print("\n=== Running Enrichment ===")
    enrichment_config = EnrichmentConfig()
    enrichment_pipeline = EnrichmentPipeline(config=enrichment_config, max_iterations=3)
    enriched_people = enrichment_pipeline.run({p.xref_id: p for p in people})
    
    print(f"Enriched {len(enriched_people)} people")
    
    # Check for issues
    total_issues = sum(len(ep.issues) for ep in enriched_people.values())
    print(f"Found {total_issues} data quality issues")
    
    # Step 3: Collect statistics
    print("\n=== Collecting Statistics ===")
    stats_config = StatisticsConfig(collectors={
        'demographics': True,
        'event_completeness': True,
        'geographic': True,
    })
    stats_pipeline = StatisticsPipeline(config=stats_config)
    stats = stats_pipeline.run(enriched_people.values())
    
    # Step 4: Display results
    print("\n=== Demographics ===")
    demographics = stats.get_category('demographics')
    print(f"Total people: {demographics.get('total_people')}")
    print(f"Living: {demographics.get('living')}")
    print(f"Deceased: {demographics.get('deceased')}")
    print(f"Average lifespan: {demographics.get('average_lifespan')} years")
    
    print("\n=== Event Completeness ===")
    events = stats.get_category('events')
    completeness = events.get('completeness', {})
    if 'birth' in completeness:
        birth = completeness['birth']
        print(f"Birth events: {birth['total']}")
        print(f"  With dates: {birth['date_percentage']}%")
        print(f"  With places: {birth['place_percentage']}%")
    
    print("\n=== Geographic ===")
    geographic = stats.get_category('geographic')
    print(f"Unique places: {geographic.get('unique_places')}")
    
    # Step 5: Export results
    export_results(stats, enriched_people)
    print("\nResults exported to statistics.json and enriched_data.json")


def load_sample_data():
    """Load sample data for demonstration."""
    from geo_gedcom.person import Person
    from geo_gedcom.life_event import LifeEvent
    
    people = []
    
    # Person 1: Complete data
    p1 = Person(xref_id='I1')
    p1.name = 'John /Doe/'
    p1.add_event('birth', LifeEvent(date='1 JAN 1900', place='London, England', what='BIRT'))
    p1.add_event('death', LifeEvent(date='31 DEC 1975', place='London, England', what='DEAT'))
    people.append(p1)
    
    # Person 2: Only birth
    p2 = Person(xref_id='I2')
    p2.name = 'Jane /Smith/'
    p2.add_event('birth', LifeEvent(date='15 MAR 1925', place='Paris, France', what='BIRT'))
    people.append(p2)
    
    # Person 3: Birth and burial (death will be inferred)
    p3 = Person(xref_id='I3')
    p3.name = 'Bob /Johnson/'
    p3.add_event('birth', LifeEvent(date='20 JUL 1950', place='New York, USA', what='BIRT'))
    p3.add_event('burial', LifeEvent(date='15 AUG 2020', place='New York, USA', what='BURI'))
    people.append(p3)
    
    # Person 4: Minimal data
    p4 = Person(xref_id='I4')
    p4.name = 'Alice /Williams/'
    people.append(p4)
    
    return people


def export_results(stats, enriched_people):
    """Export statistics and enriched data."""
    
    # Export statistics
    with open('statistics.json', 'w') as f:
        json.dump(stats.to_dict(), f, indent=2)
    
    # Export enriched data summary
    enriched_summary = {}
    for person_id, enriched in enriched_people.items():
        enriched_summary[person_id] = {
            'name': enriched.display_name,
            'inferred_events': list(enriched.inferred_events.keys()),
            'issues': [
                {
                    'type': issue.issue_type,
                    'severity': issue.severity,
                    'message': issue.message
                }
                for issue in enriched.issues
            ]
        }
    
    with open('enriched_data.json', 'w') as f:
        json.dump(enriched_summary, f, indent=2)


if __name__ == '__main__':
    example_enrichment_and_statistics()

# Statistics Module

The statistics module provides aggregate statistical analysis of genealogical datasets. Unlike the enrichment module which modifies individual person records, the statistics module collects and analyzes data across the entire dataset without modifying it.

## Overview

The statistics module is built around **collectors** - independent analysis components that gather specific types of statistics from your dataset. Collectors can analyze demographics, events, geographic distribution, and more.

### Key Concepts

- **StatisticsCollector**: Base class for creating custom statistics collectors
- **Statistics**: Container for statistical results organized by category
- **StatisticsPipeline**: Orchestrates running multiple collectors
- **StatisticsConfig**: Configuration for enabling/disabling collectors

## Quick Start

### Basic Usage

```python
from geo_gedcom.statistics import StatisticsPipeline
from geo_gedcom.statistics.collectors import (
    DemographicsCollector,
    EventCompletenessCollector,
    GeographicCollector,
    GenderCollector,
    NamesCollector,
    AgesCollector,
    BirthsCollector,
    LongevityCollector,
    TimelineCollector,
    MarriageCollector,
    ChildrenCollector,
    RelationshipStatusCollector,
    DivorceCollector
)

# Create pipeline with built-in collectors
pipeline = StatisticsPipeline()

# Run on your dataset (works with Person or EnrichedPerson objects)
stats = pipeline.run(people)

# Access results
total_people = stats.get_value('demographics', 'total_people')
avg_lifespan = stats.get_value('demographics', 'average_lifespan')
birth_places = stats.get_value('geographic', 'most_common_birth_places')

print(f"Dataset contains {total_people} people")
print(f"Average lifespan: {avg_lifespan} years")
```

### With Configuration

```python
from geo_gedcom.statistics import StatisticsPipeline, StatisticsConfig

# Configure which collectors to run
config = StatisticsConfig(collectors={
    'demographics': True,
    'event_completeness': True,
    'geographic': False  # Disable geographic collector
})

pipeline = StatisticsPipeline(config=config)
stats = pipeline.run(people)
```

### Load Configuration from File

```yaml
# config.yaml
statistics:
  collectors:
    demographics:
      enabled: true
    event_completeness:
      enabled: true
    geographic:
      enabled: false
```

```python
config = StatisticsConfig(config_file='config.yaml')
pipeline = StatisticsPipeline(config=config)
```

## Built-in Collectors

The statistics module includes 13 built-in collectors organized into 4 categories:

### Core/Base Collectors (3)

#### DemographicsCollector

Collects demographic statistics about the dataset.

**Statistics collected:**
- `total_people`: Total count of people
- `living`: Count of living people
- `deceased`: Count of deceased people
- `birth_year_distribution`: Dictionary of birth years and counts
- `earliest_birth_year`: Earliest birth year in dataset
- `latest_birth_year`: Latest birth year in dataset
- `death_year_distribution`: Dictionary of death years and counts
- `average_lifespan`: Average lifespan in years
- `median_lifespan`: Median lifespan in years
- `min_lifespan`: Minimum lifespan
- `max_lifespan`: Maximum lifespan
- `unique_surnames`: Count of unique surnames
- `most_common_surnames`: Dictionary of most common surnames and counts

**Example:**
```python
stats = pipeline.run(people)
demographics = stats.get_category('demographics')

print(f"Total people: {demographics['total_people']}")
print(f"Average lifespan: {demographics['average_lifespan']} years")
print(f"Most common surnames: {demographics['most_common_surnames']}")
```

### EventCompletenessCollector

Analyzes completeness of event data.

**Statistics collected:**
- `event_counts`: Dictionary of event types and counts
- `completeness`: Detailed completeness data per event type
  - `total`: Total count of events
  - `with_date`: Count with dates
  - `with_place`: Count with places
  - `date_percentage`: Percentage with dates
  - `place_percentage`: Percentage with places
- `people_with_birth`: Count of people with birth events
- `people_with_death`: Count of people with death events
- `birth_coverage_percentage`: Percentage of people with birth events
- `death_coverage_percentage`: Percentage of people with death events

**Example:**
```python
completeness = stats.get_value('events', 'completeness')
birth_stats = completeness['birth']

print(f"Birth events: {birth_stats['total']}")
print(f"With dates: {birth_stats['date_percentage']}%")
print(f"With places: {birth_stats['place_percentage']}%")
```

### GeographicCollector

Analyzes geographic distribution of events.

**Statistics collected:**
- `most_common_birth_places`: Top 20 birth places
- `unique_birth_places`: Count of unique birth places
- `most_common_death_places`: Top 20 death places
- `unique_death_places`: Count of unique death places
- `most_common_places`: Top 30 places overall
- `unique_places`: Count of unique places overall
- `countries`: Dictionary of countries and counts

**Example:**
```python
geo = stats.get_category('geographic')

print(f"Unique places: {geo['unique_places']}")
print(f"Top birth places: {geo['most_common_birth_places']}")
print(f"Countries: {geo['countries']}")
```

### Demographic Collectors (4)

#### GenderCollector
Analyzes gender distribution and gender-specific statistics.

**Statistics collected:**
- Gender counts (male, female, unknown)
- Gender percentages
- Living vs deceased by gender
- Most common names by gender

#### NamesCollector
Analyzes name patterns and frequencies.

**Statistics collected:**
- Most common first names
- Most common middle names
- Most common surnames
- Unique name counts
- People with middle names

#### AgesCollector
Analyzes age distribution and lifespan statistics.

**Statistics collected:**
- Living people age distribution
- Oldest/youngest living people
- Age at death distribution
- Deceased lifespan statistics
- Age ranges and categories

#### BirthsCollector
Analyzes birth patterns and temporal trends.

**Statistics collected:**
- Birth months distribution
- Birth seasons
- Zodiac sign distribution
- Birth decades and centuries
- Most/least common birth months and zodiac signs

### Temporal Collectors (2)

#### LongevityCollector
Analyzes life expectancy and mortality patterns.

**Statistics collected:**
- Life expectancy by birth decade
- Life expectancy by birth century
- Life expectancy by gender over time
- Infant mortality rate
- Child mortality rate
- Survival rates by time period

#### TimelineCollector
Analyzes event density and temporal coverage.

**Statistics collected:**
- Total events with dates
- Event density by decade
- Peak periods (decade, year)
- Temporal coverage span
- Data completeness by decade
- Events by type

### Family Collectors (4)

#### MarriageCollector
Analyzes marriage patterns and statistics.

**Statistics collected:**
- Number of marriages per person
- Marriage age distribution (by gender)
- Marriage duration statistics
- Age differences between spouses
- Marriage trends over time (decades, centuries)
- Oldest/youngest when married
- Longest/shortest marriages

#### ChildrenCollector
Analyzes family size and children statistics.

**Statistics collected:**
- Children per family
- Children per person (by gender)
- Family with most children
- People with most children
- Age when having children
- Oldest/youngest when had a child
- Sibling age gaps
- Average children per family

#### RelationshipStatusCollector
Categorizes people by marital status.

**Statistics collected:**
- Never married count
- Currently married count
- Widowed count
- Status by gender
- Status by age groups
- Percentage breakdowns

#### DivorceCollector
Analyzes divorce patterns and statistics.

**Statistics collected:**
- Total divorces
- People with divorces
- Divorce rate percentage
- Age at divorce (by gender)
- Oldest/youngest when divorced
- Marriage duration before divorce
- Longest/shortest marriages ending in divorce
- Divorce trends over time (decades, centuries)
- People who divorced the most

## Creating Custom Collectors

### Basic Collector

```python
from dataclasses import dataclass
from typing import Any, Iterable
from geo_gedcom.statistics import StatisticsCollector, register_collector, Statistics

@register_collector
@dataclass
class MyCustomCollector(StatisticsCollector):
    """My custom statistics collector."""
    
    collector_id: str = "my_custom"
    
    def collect(self, people: Iterable[Any], existing_stats: Statistics) -> Statistics:
        stats = Statistics()
        
        # Analyze people
        count = 0
        for person in people:
            count += 1
            # Your analysis logic here
        
        # Add statistics
        stats.add_value('custom', 'person_count', count)
        
        return stats
```

### Advanced Collector

```python
@register_collector
@dataclass
class FamilyStatsCollector(StatisticsCollector):
    """Analyzes family structure statistics."""
    
    collector_id: str = "family_stats"
    
    def collect(self, people: Iterable[Any], existing_stats: Statistics) -> Statistics:
        stats = Statistics()
        
        children_counts = []
        
        for person in people:
            # Count children
            if hasattr(person, 'children'):
                num_children = len(list(person.children))
                children_counts.append(num_children)
        
        if children_counts:
            avg_children = sum(children_counts) / len(children_counts)
            stats.add_value('family', 'average_children', round(avg_children, 2))
            stats.add_value('family', 'max_children', max(children_counts))
        
        return stats
```

## Statistics Data Model

### Statistics Class

Container for all statistical results.

```python
stats = Statistics()

# Add values organized by category
stats.add_value('demographics', 'total_people', 100)
stats.add_value('demographics', 'living', 60)

# Get individual values
total = stats.get_value('demographics', 'total_people')
living = stats.get_value('demographics', 'living', default=0)

# Get all values in a category
demo = stats.get_category('demographics')

# Merge multiple Statistics objects
stats.merge(other_stats)

# Convert to/from dictionary
data = stats.to_dict()
stats = Statistics.from_dict(data)
```

### Supported Value Types

Statistics can store various data types:
- **int/float**: Counts, averages, percentages
- **str**: Text values
- **List**: Collections of values
- **Dict**: Nested data structures (e.g., distributions)

## Integration with Enrichment

The statistics module works seamlessly with enriched data:

```python
from geo_gedcom.enrichment import run_enrichment
from geo_gedcom.statistics import StatisticsPipeline

# First, enrich the data
enriched_people = run_enrichment(people, config)

# Then, gather statistics (can use inferred events)
pipeline = StatisticsPipeline()
stats = pipeline.run(enriched_people.values())
```

## Export Statistics

### To JSON

```python
import json

stats_dict = stats.to_dict()
with open('statistics.json', 'w') as f:
    json.dump(stats_dict, f, indent=2)
```

### To CSV

```python
import csv

demographics = stats.get_category('demographics')
with open('demographics.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Metric', 'Value'])
    for key, value in demographics.items():
        if not isinstance(value, (dict, list)):
            writer.writerow([key, value])
```

## Best Practices

1. **Keep collectors focused**: Each collector should analyze one aspect
2. **Use categories wisely**: Organize related statistics in same category
3. **Handle missing data**: Check for None values and handle gracefully
4. **Performance**: Convert people iterable to list if multiple passes needed
5. **Logging**: Use logging to report progress and issues
6. **Testing**: Write tests for custom collectors

## Architecture

```
statistics/
├── __init__.py           # Public API
├── model.py              # Statistics data model
├── base.py               # Base collector class
├── pipeline.py           # Pipeline and configuration
├── collectors/           # Built-in collectors
│   ├── demographics.py
│   ├── events.py
│   └── geographic.py
└── tests/                # Tests
```

## See Also

- [Enrichment Module](../enrichment/README.md) - For data enrichment and inference
- [Examples](../../examples/) - Usage examples

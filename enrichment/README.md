# Genealogical Data Enrichment Module

This module provides a flexible pipeline for enriching genealogical data (GEDCOM) by inferring missing information, identifying inconsistencies, and applying domain knowledge about human lifespans and family relationships.

> **Note**: When loading large GEDCOM files in the GUI application, enrichment processing can be disabled via Configuration Options → Processing Options → "Enable enrichment processing during GEDCOM load" to speed up loading. See the main README for details.

## Overview

The enrichment module processes genealogical records to:
- **Infer missing events** (e.g., death dates from burial records)
- **Detect data quality issues** (e.g., implausibly old people, incompatible parent-child ages)
- **Tighten date bounds** using relationships and life events
- **Generate confidence-rated inferences** with full provenance tracking

## Architecture

### Core Components

```
enrichment/
├── enrichment.py          # Main Enrichment class (entry point)
├── pipeline.py            # EnrichmentPipeline orchestrates rule execution
├── config.py             # EnrichmentConfig manages settings
├── config.yaml           # Default configuration values
├── model.py              # Data models (EnrichedPerson, Issue, InferredEvent, etc.)
├── defaults.py           # Rule instantiation with config mapping
├── date_utils.py         # Date manipulation utilities
└── rules/                # Enrichment rules
    ├── base.py           # BaseRule and registry system
    ├── death_from_burial.py
    ├── parent_child_bounds.py
    └── implausible_age.py
```

### Key Concepts

**EnrichedPerson**: Wraps a `Person` object with:
- `inferred_events`: Events inferred by rules (Dict[EventTag, InferredEvent])
- `date_bounds`: Tightened date ranges for events (Dict[EventTag, DateRange])
- `issues`: List of data quality issues found
- `place_overrides`: Alternative place information

**Enrichment Rules**: Implement domain knowledge:
- Each rule analyzes people and their relationships
- Rules can infer events, tighten date bounds, and report issues
- Rules are auto-discovered via the `@register_rule` decorator

**Pipeline**: Iteratively applies rules until convergence:
- Runs up to `max_iterations` times
- Stops early if no changes occur (convergence)
- Tracks which rules ran and how many times

## Quick Start

### Basic Usage

```python
from geo_gedcom.enrichment import Enrichment

# Initialize with default configuration
enrichment = Enrichment(people=my_gedcom_people)

# Run enrichment
result = enrichment.run()

# Access enriched people
for person_id, enriched_person in result.people.items():
    # Check for inferred events
    if 'death' in enriched_person.inferred_events:
        death_event = enriched_person.inferred_events['death']
        print(f"Inferred death: {death_event.date_range} (confidence: {death_event.confidence})")

    # Check for issues
    for issue in enriched_person.issues:
        print(f"Issue: {issue.severity} - {issue.message}")
```

### Custom Configuration

```python
# Using a custom YAML config file
from pathlib import Path
enrichment = Enrichment(
    config_yaml=Path("my_custom_config.yaml"),
    people=my_people
)

# Using a dictionary override
enrichment = Enrichment(
    config_dict={
        "max_iterations": 5,
        "death_age_max": 120,
        "rules_enabled": {
            "death_from_burial": True,
            "implausible_age": False  # Disable this rule
        }
    },
    people=my_people
)
```

## Configuration

### Configuration File (`config.yaml`)

```yaml
# General Settings
enabled: true
max_iterations: 3

# Age Constraints - Person Lifespan
death_age_min: 0
death_age_max: 122  # Jeanne Calment's verified age

# Age Constraints - Parents
mother_age_min: 11
mother_age_max: 66
father_age_min: 12
father_age_max: 93

# Inference Windows
burial_to_death_max_days: 14
baptism_to_birth_max_days: 365

# Rule Confidence Levels (0.0 to 1.0)
rule_confidence:
  death_from_burial: 0.6
  implausible_age: 0.7

# Enable/Disable Rules
rules_enabled:
  death_from_burial: true
  parent_child_bounds: true
  implausible_age: true

# Allow rules to infer event dates
rules_infer_event_date_updates:
  death_from_burial: true
  implausible_age: true
  parent_child_bounds: true
```

### Loading Configuration

```python
from geo_gedcom.enrichment import EnrichmentConfig
from pathlib import Path

# Load from YAML
config = EnrichmentConfig.from_yaml(Path("config.yaml"))

# Create from dictionary
config = EnrichmentConfig.from_dict({
    "enabled": True,
    "max_iterations": 5,
    # ... other settings
})

# Check if a rule is enabled
if config.rule_enabled("death_from_burial"):
    print("Death from burial rule is enabled")
```

## Built-in Enrichment Rules

### 1. DeathFromBurialRule

**Purpose**: Infers death dates from burial events

**Logic**:
- If a person has a burial event but no death event
- Infers death occurred within `burial_to_death_max_days` before burial
- Creates a `DateRange` from (burial - max_days) to burial date

**Example**:
```
Burial: 10 JAN 1950
Max days: 14
Inferred death range: 27 DEC 1949 to 10 JAN 1950
```

**Configuration**:
- `burial_to_death_max_days`: Maximum days between death and burial (default: 14)
- `rule_confidence.death_from_burial`: Confidence level (default: 0.6)
- `rules_infer_event_date_updates.death_from_burial`: Whether to infer (default: true)

### 2. ParentChildBoundsRule

**Purpose**: Validates and constrains parent-child birth dates

**Logic**:
- For each child, constrains parent's birth date based on child's birth
- Parent must be between `min_age` and `max_age` years old at child's birth
- Different age constraints for mothers vs fathers
- Reports issues when known dates are incompatible

**Examples**:
```
Child born: 1975
Mother age constraints: 11-66 years
Father age constraints: 12-93 years
→ Mother's birth: latest 1964 (1975 - 11)
→ Father's birth: latest 1963 (1975 - 12)
```

**Configuration**:
- `mother_age_min` / `mother_age_max`: Age range for mothers (default: 11-66)
- `father_age_min` / `father_age_max`: Age range for fathers (default: 12-93)

**Issues Reported**:
- Parent too young: "Parent was only X years old when child was born"
- Parent too old: "Parent was X years old when child was born (maximum expected: Y)"

### 3. ImplausibleAgeRule

**Purpose**: Identifies people who would be impossibly old if still alive

**Logic**:
- Calculates person's age if alive today
- If age exceeds `max_age_years` (default: 122) and no death recorded
- Reports a warning issue
- Optionally infers death date range

**Example**:
```
Person born: 1850
Current year: 2026
Age if alive: 176 years
Max plausible age: 122 years
→ Issue: Person would be 176 years old (exceeds 122)
→ Inferred death range: 1850 to 1972 (birth + max_age)
```

**Configuration**:
- `death_age_max`: Maximum plausible age (default: 122, based on Jeanne Calment)
- `death_age_min`: Minimum age for death inference (default: 0)
- `rules_infer_event_date_updates.implausible_age`: Whether to infer death (default: true)

## Data Models

### EnrichedPerson

Represents a person with enrichment data:

```python
@dataclass
class EnrichedPerson:
    person: Person  # Original GEDCOM person
    inferred_events: Dict[EventTag, InferredEvent]
    date_bounds: Dict[EventTag, DateRange]
    place_overrides: Dict[EventTag, str]
    issues: List[Issue]

    # Convenience methods
    def has_event(self, tag: str) -> bool
    def get_event_date(self, tag: str) -> Optional[Any]
    def best_place(self, tag: str) -> Optional[str]
    def birth_range(self) -> Optional[DateRange]
    def death_range(self) -> Optional[DateRange]
```

### InferredEvent

Represents an event inferred by a rule:

```python
@dataclass
class InferredEvent:
    tag: EventTag  # 'birth', 'death', 'burial', etc.
    date_range: Optional[DateRange]
    place: Optional[str]
    confidence: float  # 0.0 to 1.0
    provenance: Provenance  # How it was inferred
```

### Issue

Represents a data quality issue:

```python
@dataclass(frozen=True)
class Issue:
    issue_type: str  # e.g., "implausible_age", "parent_child_bounds"
    severity: Literal["info", "warning", "error"]
    message: str
    person_id: Optional[str]
    related_person_ids: Tuple[str, ...]
```

### DateRange

Represents uncertainty in dates:

```python
@dataclass(frozen=True)
class DateRange:
    earliest: Optional[Any]  # Earliest possible date
    latest: Optional[Any]    # Latest possible date

    def is_empty(self) -> bool
    def intersect(self, other: DateRange) -> DateRange
    def contains(self, date: Any) -> bool
```

## Creating Custom Rules

### Step 1: Define Your Rule

```python
from dataclasses import dataclass
from typing import Dict, List, Any
from geo_gedcom.enrichment.rules import BaseRule, register_rule
from geo_gedcom.enrichment.model import EnrichedPerson, Issue

@register_rule  # Auto-registers with the rule registry
@dataclass
class MyCustomRule(BaseRule):
    rule_id: str = "my_custom_rule"
    my_threshold: int = 10  # Custom parameter

    def apply(
        self,
        enriched_people: Dict[str, EnrichedPerson],
        original_people: Dict[str, Any],
        issues: List[Issue],
        app_hooks = None,
    ) -> bool:
        """
        Apply the rule to all people.

        Returns:
            bool: True if any changes were made, False otherwise
        """
        changed = False

        for person_id, enriched_person in enriched_people.items():
            # Your rule logic here
            # ...

            if some_condition:
                # Report an issue
                issue = Issue(
                    person_id=person_id,
                    issue_type=self.rule_id,
                    message="Something is wrong",
                    severity="warning"
                )
                issues.append(issue)
                enriched_person.issues.append(issue)
                changed = True

        return changed
```

### Step 2: Configure Your Rule

Add to `config.yaml`:

```yaml
# Rule parameters
my_custom_threshold: 10

# Rule confidence
rule_confidence:
  my_custom_rule: 0.8

# Enable the rule
rules_enabled:
  my_custom_rule: true

# Infer event updates
rules_infer_event_date_updates:
  my_custom_rule: true
```

### Step 3: Map Configuration to Rule

Add to `defaults.py`:

```python
RULE_PARAM_MAP = {
    # ... existing rules ...
    'my_custom_rule': {
        'my_threshold': 'my_custom_threshold',
        'confidence': lambda cfg: cfg.rule_confidence.get('my_custom_rule', 0.8),
        'infer_event_updates': lambda cfg: cfg.rules_infer_event_date_updates.get('my_custom_rule', True),
    }
}
```

The rule will now be automatically discovered and instantiated!

## Testing

Run the enrichment tests:

```bash
pytest gedcom-to-map/geo_gedcom/enrichment/tests/ -v
```

Test structure:
- `tests/test_model.py` - Data model tests
- `tests/test_rules.py` - Individual rule tests
- `tests/test_pipeline.py` - Pipeline and configuration tests
- `tests/test_integration.py` - End-to-end integration tests
- `tests/test_date_utils.py` - Date utility function tests

## Advanced Usage

### Progress Reporting

```python
from geo_gedcom.app_hooks import AppHooks

class MyAppHooks(AppHooks):
    def report_step(self, info, target=None, reset_counter=False, plus_step=1):
        print(f"Progress: {info}")

    def stop_requested(self, logger_stop_message=None):
        return False  # Return True to cancel enrichment

enrichment = Enrichment(people=my_people, app_hooks=MyAppHooks())
result = enrichment.run()
```

### Accessing Results

```python
result = enrichment.run()

# Result object contains
print(f"Iterations: {result.iterations}")
print(f"Issues found: {len(result.issues)}")
print(f"Rule execution stats: {result.rule_runs}")

# Access enriched people
for person_id, enriched_person in result.people.items():
    # Original person data
    original = enriched_person.person

    # Inferred events
    for event_tag, inferred_event in enriched_person.inferred_events.items():
        print(f"{event_tag}: {inferred_event.date_range} (confidence: {inferred_event.confidence})")

    # Date bounds (tightened ranges)
    for event_tag, date_range in enriched_person.date_bounds.items():
        print(f"{event_tag} bounds: {date_range.earliest} to {date_range.latest}")

    # Issues
    for issue in enriched_person.issues:
        print(f"{issue.severity}: {issue.message}")
```

### Exporting Issues to CSV

```python
from render.summary import write_enrichment_issues_summary

# Export all issues to CSV
write_enrichment_issues_summary(
    enriched_people=result.people,
    output_file="enrichment_issues.csv"
)
```

CSV format:
```csv
person_id,severity,issue_type,message
I1,warning,implausible_age,"Person would be 176 years old if alive today..."
I2,warning,parent_child_bounds,"Parent I1 (mother) was only 10 years old when child I2 was born..."
```

## Best Practices

1. **Start with default configuration**: The defaults are based on historical demographic research
2. **Review issues before trusting inferences**: Enrichment flags potential problems for manual review
3. **Adjust age constraints for your dataset**: Different time periods and regions may need different limits
4. **Test rules independently**: Write unit tests for custom rules before adding to pipeline
5. **Use confidence scores**: Higher confidence = more reliable inference
6. **Track provenance**: Every inference includes how it was derived
7. **Iterate carefully**: More iterations aren't always better; usually converges in 2-3 iterations

## Troubleshooting

### No changes after first iteration

This is expected behavior! Most rules make their changes in the first pass. The pipeline will stop early when no further changes are detected.

### Too many iterations needed

If the pipeline runs all `max_iterations` without converging, you may have:
- Conflicting rules that "fight" each other
- Rules that continuously modify the same data
- Check rule logic for potential infinite loops

### Unexpected inferences

1. Check the rule's confidence score - lower = less certain
2. Review the provenance to understand how it was inferred
3. Adjust rule parameters in `config.yaml`
4. Disable the rule if not applicable to your data

### Performance issues

- Rules iterate over all people, so performance scales with dataset size
- Use progress reporting hooks to monitor which rule is slow
- Consider parallelizing rule execution for large datasets (future enhancement)

## Future Enhancements

Potential areas for expansion:

- **More rules**: Marriage date inference, migration patterns, occupations
- **Machine learning**: Learn from corrected data to improve confidence scores
- **Relationship inference**: Identify potential missing parent-child links
- **Place validation**: Check geographic consistency of events
- **Name standardization**: Normalize spelling variations
- **Source integration**: Incorporate external data sources

## References

- Configuration based on demographic research:
  - Maximum human lifespan: Jeanne Calment (122 years, 164 days)
  - Parental age ranges based on historical birth records
  - Burial customs vary by culture but typically < 14 days

## License

See main project LICENSE file.

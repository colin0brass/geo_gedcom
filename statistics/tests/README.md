# Statistics Collectors Test Suite

## Test File Organization

The test suite is organized by collector category for better maintainability and clarity:

### 1. test_demographic_collectors.py
Tests collectors that gather demographic and personal information:
- **GenderCollector**: Gender distribution and name analysis by gender
- **NamesCollector**: Name frequency and diversity analysis  
- **AgesCollector**: Age distribution and lifespan statistics
- **BirthsCollector**: Birth patterns, zodiac signs, and temporal trends

**Tests:** 5 tests covering basic functionality and integration ✅ All passing

### 2. test_temporal_collectors.py
Tests collectors that analyze temporal patterns and life cycles:
- **LongevityCollector**: Life expectancy, mortality rates, and longevity trends
- **TimelineCollector**: Event density, temporal coverage, and historical patterns

**Tests:** 10 tests covering lifecycle analysis and temporal patterns ✅ All passing

### 3. test_family_collectors.py
Tests collectors that analyze family structures and relationships:
- **MarriageCollector**: Marriage patterns, ages, durations, and age differences
- **ChildrenCollector**: Family size, children statistics, and sibling relationships
- **RelationshipStatusCollector**: Marital status categorization and demographics

**Tests:** 12 tests covering family relationships and marital status ✅ All passing

### 4. test_collectors.py
Tests for existing base/core collectors:
- **DemographicsCollector**: Basic demographic statistics (original collector)
- **EventCompletenessCollector**: Event data completeness analysis
- **GeographicCollector**: Geographic distribution and location analysis

### 5. test_model.py
Tests for the Stats data model (add_value, merge, get_category, etc.)

### 6. test_pipeline.py
Tests for the statistics collection pipeline and orchestration

### 7. test_statistics.py
Integration tests for the overall statistics system and collector coordination

## Running Tests

### Run all tests:
```bash
# From project root
pytest gedcom-to-map/geo_gedcom/statistics/tests/ -v

# All collector tests only
pytest gedcom-to-map/geo_gedcom/statistics/tests/test_*collectors.py -v
```

### Run by category:
```bash
# Demographic collectors (Gender, Names, Ages, Births)
pytest gedcom-to-map/geo_gedcom/statistics/tests/test_demographic_collectors.py -v

# Temporal/lifecycle collectors (Longevity, Timeline)
pytest gedcom-to-map/geo_gedcom/statistics/tests/test_temporal_collectors.py -v

# Family relationship collectors (Marriage, Children, RelationshipStatus)
pytest gedcom-to-map/geo_gedcom/statistics/tests/test_family_collectors.py -v

# Base collectors (Demographics, Events, Geographic)
pytest gedcom-to-map/geo_gedcom/statistics/tests/test_collectors.py -v
```

### Run specific test:
```bash
# Specific test function
pytest gedcom-to-map/geo_gedcom/statistics/tests/test_family_collectors.py::test_marriage_collector_basic -v

# With detailed output
pytest gedcom-to-map/geo_gedcom/statistics/tests/test_family_collectors.py::test_marriage_collector_basic -vvs
```

### Run with coverage:
```bash
pytest gedcom-to-map/geo_gedcom/statistics/tests/ --cov=geo_gedcom.statistics --cov-report=html
```

## Test Coverage

### Collector Statistics
**Total Collectors Implemented:** 12
- **Demographic:** Gender, Names, Ages, Births (4 collectors)
- **Core/Base:** Demographics, EventCompleteness, Geographic (3 collectors)
- **Temporal:** Longevity, Timeline (2 collectors)
- **Family:** Marriage, Children, RelationshipStatus (3 collectors)

### Test Statistics
**Total Tests:** 54 tests across all test files

**By Category:**
- ✅ **test_family_collectors.py:** 12 tests - All passing
- ✅ **test_temporal_collectors.py:** 10 tests - All passing
- ✅ **test_demographic_collectors.py:** 5 tests - All passing
- ✅ **test_collectors.py:** 5 tests - All passing
- ✅ **test_model.py:** 7 tests - All passing
- ✅ **test_pipeline.py:** 7 tests - All passing
- ✅ **test_statistics.py:** 8 tests - All passing

**Status Summary:**
- ✅ **All 54 tests passing (100%)**
- ✅ Family collectors: 12/12 passing
- ✅ Demographic collectors: 5/5 passing
- ✅ Temporal collectors: 10/10 passing
- ✅ Base/Core collectors: 5/5 passing
- ✅ Infrastructure tests: 22/22 passing (model, pipeline, statistics)

## Naming Convention

Test files follow the pattern: `test_<category>_collectors.py`
- **Descriptive category names:** demographic, temporal, family, base
- **Consistent `_collectors` suffix:** Makes it easy to find all collector tests
- **Clear grouping by functionality:** Related collectors tested together

## Test Structure

Each collector test file follows this pattern:
1. **Mock classes:** Simulate Person, Event, Date objects with minimal dependencies
2. **Unit tests:** Test individual collector functionality
3. **Integration tests:** Test collectors working together
4. **Edge cases:** Test boundary conditions and error handling

All collector tests now use a consistent, refined mock strategy:
```python
class MockDate:
    def __init__(self, year):
        self.year_num = year  # Property, not method
        self.year = year

class MockEvent:
    def __init__(self, year=None):
        self.date = MockDate(year) if year is not None else None

class MockPerson:
    # Implements get_event(), get_events(), and necessary attributes
```

**Key principle:** Mock dates must have `year_num` as a property (not a method) to work correctly with the `year_num()` utility function used throughout the collectors. This pattern is now consistently applied across all test files

**Note:** Demographic and temporal collector tests use older mock patterns and need updates to match the family collector approach for consistency.

## Historical Note

**Previous names (now improved):**
- `test_new_collectors.py` → `test_demographic_collectors.py` (more descriptive)
- `test_longevity_timeline.py` → `test_temporal_collectors.py` (consistent naming)

## Contributing

When adding new collector tests:
1. Place in appropriate category file or create new category if needed
2. Use the refined mock object pattern from test_family_collectors.py
3. Include unit tests and at least one integration test
4. Update this README with test counts and descriptions
5. Ensure all tests pass before committing

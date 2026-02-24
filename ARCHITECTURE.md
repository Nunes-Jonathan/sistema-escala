# Architecture Documentation

## System Overview

Sistema de Escala is a modular scheduling system designed with clean separation of concerns between the scheduling engine and the user interface.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Streamlit UI Layer                       │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │  Sidebar   │  │ Schedule    │  │  Editable Tables         │ │
│  │  Controls  │  │ Views       │  │  (Availability Editor)   │ │
│  └────────────┘  └─────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Scheduling Engine                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Scheduler (Orchestrator)                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│         │                 │                    │                 │
│         ▼                 ▼                    ▼                 │
│  ┌──────────┐     ┌──────────┐        ┌──────────────┐         │
│  │ Assigner │     │Validator │        │Weekend       │         │
│  │          │     │          │        │Tracker       │         │
│  └──────────┘     └──────────┘        └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Data Models                            │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │Employee  │  │Category  │  │Assignment │  │WeekSchedule  │  │
│  └──────────┘  └──────────┘  └───────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Export Layer                               │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │ Excel Exporter   │              │  CSV Exporter    │         │
│  │  (3 tabs)        │              │  (zipped)        │         │
│  └──────────────────┘              └──────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Core Layer (`core/`)

**models.py**
- Pydantic data models for type safety and validation
- Employee, Category, TimeBlock, Assignment, Schedule, ValidationResult
- Immutable data structures with clear interfaces

**constants.py**
- Configuration: employees, categories, coverage windows
- Business rules: weekend requirements, eligibility constraints
- Single source of truth for domain constants

**utils.py**
- Time block generation
- Date/time manipulation utilities
- Helper functions for time range checks

### Engine Layer (`engine/`)

**scheduler.py** (Orchestrator)
- Main entry point for scheduling operations
- Coordinates assigner, validator, and weekend tracker
- Manages week-level schedule generation and regeneration

**assigner.py** (Assignment Algorithm)
- Greedy assignment with scoring
- Priority-based category assignment (fixed employees first)
- Fallback logic for Salas+Helpdesk overlap
- Scoring criteria:
  1. Prefer non-Anderson (last resort)
  2. Prefer default hours (minimize changes)
  3. Prefer fixed employees for their categories

**validator.py** (Rule Enforcement)
- Coverage validation (all required blocks assigned)
- Double-booking detection
- Category eligibility checks
- Fixed employee hour constraints
- Weekend rule validation

**weekend_tracker.py** (Weekend Compliance)
- Track weekends off/worked per employee per month
- Enforce 2-off/2-working rule
- Special handling for weekend-exempt employees

### UI Layer (`ui/`)

**sidebar.py**
- Week selection controls
- Scenario picker
- Absence/override editor per day

**schedule_view.py**
- Daily schedule grid visualization
- Validation result display
- Coverage summary tables
- Weekend tracking summary

**editor.py**
- Editable availability tables
- Quick absence entry forms
- Data conversion between UI and models

### Export Layer (`export/`)

**excel_exporter.py**
- WorkHours tab: Employee availability data
- WeekdaysGrid tab: Time block assignments Mon-Fri
- WeekendGrid tab: Weekend assignments + tracking summary
- Styled cells, conditional formatting

**csv_exporter.py**
- Same 3 datasets as Excel
- Zipped bundle for easy download
- Pandas-based data transformation

### Tests Layer (`tests/`)

**demo_scenarios.py**
- Pre-configured test cases
- Scenario factory functions
- Sample data generation

**test_scheduler.py**
- Unit tests for core components
- Integration tests for full workflow
- Model validation tests

## Data Flow

### Schedule Generation Flow

1. **Input**: Week start date, employee availability overrides
2. **Process**:
   - For each day in week:
     - Get employee availability (defaults + overrides)
     - For each category (priority order):
       - For each required time block:
         - Find eligible candidates
         - Score candidates
         - Assign best candidate
         - Track assignment
     - Apply fallback rules if needed
3. **Output**: WeekSchedule with assignments per day

### Validation Flow

1. **Input**: WeekSchedule
2. **Process**:
   - For each day:
     - Check coverage (all blocks assigned)
     - Check double-bookings
     - Check eligibility constraints
     - Check fixed employee hours
     - Check weekend rules
3. **Output**: ValidationResult with issues

### Export Flow

1. **Input**: WeekSchedule, WeekendTracker
2. **Process**:
   - Transform schedule to tabular format
   - Generate 3 datasets (WorkHours, WeekdaysGrid, WeekendGrid)
   - Apply formatting (Excel) or zip (CSV)
3. **Output**: File ready for download

## Assignment Algorithm Details

### Priority Order

Categories are processed in this order:
1. Supervisor de Marketing (Cesar only)
2. Marketing (Oscar only)
3. Tech (Roberto only)
4. Salas (Amanda + flexible employees)
5. Helpdesk (flexible employees)

### Candidate Scoring

For each candidate employee:
```python
score = 0.0

# Prefer non-Anderson
if employee != "Anderson":
    score += 10.0

# Prefer default hours (no overrides)
if using_default_hours:
    score += 5.0

# Prefer fixed employees for their categories
if is_fixed_employee:
    score += 8.0

# Consolidation bonus (minor)
score += 1.0
```

Best scoring candidate is selected.

### Fallback Mechanism

If no candidates available for Salas or Helpdesk:
1. Check if there are absences (day off/vacation)
2. If yes, find employee already assigned to the other category
3. Check if they can do both categories
4. Create overlap assignment (marked as fallback)

### Weekend Special Rules

**Anderson on Saturday:**
- Category: Helpdesk only
- Hours: 08:00-18:00 (overrides default)
- Day: Saturday only (never Sunday)

**Never work weekends:**
- Cesar, Oscar, Roberto, Amanda

**Weekend tracking:**
- Track per calendar month (not rolling)
- Count weekends off and worked (Sat/Sun separately)
- Validate 2-off + 2-working = 4 total weekends/month

## Design Decisions

### Why Pydantic?
- Type safety at runtime
- Automatic validation
- Clear data contracts
- Easy serialization

### Why Greedy Assignment?
- Simple, predictable, fast
- Good enough for typical schedules
- Can be replaced with CP-SAT solver if needed
- Deterministic (same input = same output)

### Why 30-Minute Blocks?
- Balance between granularity and complexity
- Matches typical shift patterns
- Easy to visualize in UI
- Configurable if needed

### Why Separate Validator?
- Single responsibility principle
- Can validate user-edited schedules
- Reusable validation logic
- Clear error reporting

### Why Streamlit?
- Rapid development
- Desktop-app feel
- Built-in data editor widgets
- Easy deployment

## Extension Points

### Adding a New Employee
1. Update `core/constants.py`: EMPLOYEE_DEFAULT_HOURS, EMPLOYEE_ALLOWED_CATEGORIES
2. Optionally add to FIXED_EMPLOYEES or WEEKEND_NEVER_WORK
3. System automatically includes them in scheduling

### Adding a New Category
1. Update `core/constants.py`: CATEGORY_COVERAGE
2. Update EMPLOYEE_ALLOWED_CATEGORIES for eligible employees
3. Optionally add exclusive employees
4. System handles it automatically

### Replacing Assignment Algorithm
1. Implement new assigner in `engine/assigner.py`
2. Keep same interface: `assign_day(date, availability) -> List[Assignment]`
3. Swap in `engine/scheduler.py`
4. Validator and rest of system unchanged

### Adding New Validation Rule
1. Add method to `engine/validator.py`
2. Call from `_validate_day()` or `validate_week()`
3. Add results to ValidationResult
4. UI displays automatically

## Performance Considerations

- **Time Complexity**: O(days × categories × blocks × employees) ≈ O(7 × 5 × 32 × 10) ≈ 11,200 operations
- **Memory**: Lightweight, all data in-memory
- **Optimization**: Use sets for lookups, avoid repeated calculations
- **Caching**: Streamlit caches schedule between interactions

## Security Considerations

- No authentication (local use only)
- No database (file-based export)
- Input validation via Pydantic
- Safe file handling for exports

## Assumptions

See ASSUMPTIONS.md for full list of assumptions made during development.

---

**Version**: 1.0
**Last Updated**: 2026-01-07

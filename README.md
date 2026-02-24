# Sistema de Escala - Work Schedule Management System

A production-quality, desktop-app feel scheduling tool built with **Python + Streamlit** that generates weekly work-hours sheets per category (role), supports real-time editing, validates coverage and rules, and exports to Excel and CSV.

## Features

- **Modular Architecture**: Clean separation between scheduling engine and UI
- **30-Minute Time Blocks**: Precise coverage tracking from 08:00 to 24:00
- **Multi-Category Scheduling**: Salas, Helpdesk, Tech, Supervisor de Marketing, Marketing
- **Rule Enforcement**: Automatic validation of employee constraints, coverage requirements, and weekend rules
- **Real-Time Editing**: Interactive UI for modifying employee availability and working hours
- **Smart Assignment**: Greedy algorithm with scoring to optimize assignments
- **Weekend Tracking**: Monitor 2-off/2-working compliance per employee per month
- **Export Formats**: Excel (.xlsx) with 3 tabs and CSV (zipped bundle)

## Quick Start

### Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Running the Application

```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

### First Steps

1. Select a Monday date for the week start
2. Choose a demo scenario or use "Normal Week"
3. Click "Generate Schedule"
4. Review the schedule in the Daily View tab
5. Check validation results
6. Export to Excel or CSV

## Project Structure

```
sistema-escala/
├── app.py                      # Streamlit entry point
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── config/                     # Configuration files (optional)
│
├── core/                       # Core data models and utilities
│   ├── __init__.py
│   ├── models.py               # Pydantic data models
│   ├── constants.py            # Categories, employees, rules
│   └── utils.py                # Helper functions
│
├── engine/                     # Scheduling engine
│   ├── __init__.py
│   ├── scheduler.py            # Main scheduler orchestrator
│   ├── validator.py            # Rule validation logic
│   ├── assigner.py             # Assignment algorithm
│   └── weekend_tracker.py      # Weekend rule tracking
│
├── export/                     # Export functionality
│   ├── __init__.py
│   ├── excel_exporter.py       # Excel export (3 tabs)
│   └── csv_exporter.py         # CSV export (zipped)
│
├── ui/                         # Streamlit UI components
│   ├── __init__.py
│   ├── sidebar.py              # Sidebar controls
│   ├── schedule_view.py        # Schedule visualization
│   └── editor.py               # Editable tables
│
└── tests/                      # Test scenarios and demos
    ├── __init__.py
    └── demo_scenarios.py       # Pre-configured test cases
```

## Architecture

### Data Models (Pydantic)

**Core Models:**
- `Employee`: Name, default hours, fixed/flexible, allowed categories
- `Category`: Name, coverage window, exclusive employees
- `TimeBlock`: 30-minute block (start_time, end_time)
- `EmployeeAvailability`: Per-date status (Working/DayOff/Vacation), hours, notes
- `Assignment`: Employee assigned to category for a time block
- `DaySchedule`: Complete schedule for one day
- `WeekSchedule`: Complete schedule for Mon-Sun
- `ValidationResult`: Coverage gaps, rule violations, warnings
- `WeekendTracking`: Weekend work counts per employee per month

### Rule Engine

**Constraint Checks:**
- Category coverage requirements (time windows)
- Employee eligibility (allowed categories)
- Fixed employee hours (cannot change)
- Weekend rules (2 off, 2 working per month)
- No double-booking (except Salas+Helpdesk overlap as fallback)

**Assignment Logic:**
- Priority-based category assignment (fixed employees first)
- Scoring system: prefer non-Anderson, default hours, fixed employees
- Fallback mechanism: Salas+Helpdesk overlap when missing employees
- Deterministic: same inputs produce same outputs

### Weekend Rules

- Each employee gets **2 weekends off** per month
- On working weekends, employees work **exactly ONE day** (Sat or Sun)
- **Exceptions:**
  - Cesar, Oscar, Roberto, Amanda: NEVER work weekends
  - Anderson: Always works Saturday (if working), 08AM-06PM, Helpdesk only

### Employee Configuration

| Employee | Default Hours | Type    | Categories                | Weekends |
|----------|---------------|---------|---------------------------|----------|
| Ana      | 08AM-04PM     | Flexible| Salas, Helpdesk           | Yes      |
| Cesar    | 11AM-07PM     | FIXED   | Supervisor de Marketing   | No       |
| Lilian   | 06PM-12AM     | Flexible| Salas, Helpdesk           | Yes      |
| Luisa    | 12PM-08PM     | Flexible| Salas, Helpdesk           | Yes      |
| Anderson | 11AM-07PM     | Flexible| Salas, Helpdesk (last resort) | Yes  |
| Pedro    | 02PM-10PM     | Flexible| Salas, Helpdesk           | Yes      |
| Gabriel  | 06PM-12AM     | Flexible| Salas, Helpdesk           | Yes      |
| Roberto  | 10AM-06PM     | FIXED   | Tech                      | No       |
| Oscar    | 08AM-05PM     | FIXED   | Marketing                 | No       |
| Amanda   | 06PM-09PM     | FIXED   | Salas (3 hours only)      | No       |

### Category Coverage Windows

| Category                  | Required Coverage |
|---------------------------|-------------------|
| Salas                     | 12PM - 12AM       |
| Helpdesk                  | 08AM - 12AM       |
| Tech                      | 10AM - 06PM       |
| Supervisor de Marketing   | 11AM - 07PM       |
| Marketing                 | 09AM - 05PM       |

## Export Formats

### Excel Output (3 Tabs)

**Tab 1: WorkHours**
- Date, DayOfWeek, Employee, Status, StartTime, EndTime, Notes
- Editable source of truth for availability

**Tab 2: WeekdaysGrid**
- Rows: Time blocks (08:00-24:00 in 30-min increments)
- Columns: Categories
- Cells: Assigned employees
- Includes coverage summary and uncovered blocks

**Tab 3: WeekendGrid**
- Same format as WeekdaysGrid but for Sat/Sun
- Weekend tracking summary: off/worked counts, compliance status

### CSV Output (Zipped Bundle)

- `workhours.csv`: Same as Excel Tab 1
- `weekdays_grid.csv`: Same as Excel Tab 2
- `weekend_grid.csv`: Same as Excel Tab 3

## Demo Scenarios

### 1. Normal Week
All employees working default hours, no absences. Tests basic assignment logic.

### 2. Ana Vacation (Tue-Thu)
Ana is on vacation Tuesday through Thursday. Tests absence handling and coverage adaptation.

### 3. Multiple Absences
Wednesday: Ana (vacation), Lilian (day off), Gabriel (vacation). Forces Salas+Helpdesk overlap fallback.

## Validation

The system validates:
- **Coverage**: All required time blocks are assigned
- **Double-bookings**: No employee in multiple categories simultaneously (except valid overlaps)
- **Eligibility**: Employees only assigned to allowed categories
- **Fixed Hours**: Fixed employees work only their designated hours
- **Weekend Rules**: Compliance with 2-off/2-working requirements

## Customization

### Adding Employees

Edit `core/constants.py`:
```python
EMPLOYEE_DEFAULT_HOURS["NewEmployee"] = (time(9, 0), time(17, 0))
EMPLOYEE_ALLOWED_CATEGORIES["NewEmployee"] = {"Salas", "Helpdesk"}
```

### Adding Categories

Edit `core/constants.py`:
```python
CATEGORY_COVERAGE["NewCategory"] = (time(10, 0), time(18, 0))
```

### Changing Rules

Modify logic in `engine/validator.py` and `engine/assigner.py`.

## Technical Details

### Dependencies

- **streamlit**: Web UI framework
- **pandas**: Data manipulation
- **pydantic**: Data validation and models
- **openpyxl**: Excel export
- **python-dateutil**: Date utilities
- **pyyaml**: Configuration files

### Assumptions Made

1. **Week starts on Monday**: All weeks run Mon-Sun
2. **Time blocks**: 30-minute blocks are sufficient granularity
3. **Coverage window**: 08:00-24:00 covers all categories
4. **Midnight crossing**: Times like 06PM-12AM are handled correctly
5. **Deterministic scheduling**: Same inputs always produce same output
6. **Greedy assignment**: Simple heuristic algorithm (can be replaced with CP-SAT solver)
7. **Overlap fallback**: Salas+Helpdesk overlap only when employees are missing
8. **Anderson as last resort**: Used only when other employees can't cover
9. **Weekend compliance**: Tracked per calendar month, not rolling 30 days
10. **Fixed employees**: Cannot change hours under any circumstance

## Future Enhancements

- Import availability from Excel/CSV
- Multi-week view and planning
- Conflict resolution suggestions
- Advanced constraint solver (CP-SAT)
- Email notifications for schedule changes
- Mobile-responsive design
- User authentication and roles
- Historical schedule archive
- Analytics and reporting dashboard

## Troubleshooting

### "Please select a Monday!"
Ensure the week start date is a Monday. The app will auto-adjust.

### Uncovered blocks after generation
Check validation results. May need to adjust employee availability or add overlap assignments.

### Export button not working
Ensure a schedule has been generated first.

## License

This project is provided as-is for educational and business use.

## Support

For issues or questions, refer to the inline documentation or modify the code to suit your needs.

---

**Built with Python, Streamlit, and Pydantic**

"""Demo scenarios for testing the scheduling system."""

from datetime import date, time, timedelta
from typing import Dict, List

from core.models import Employee, Category, EmployeeAvailability, WorkStatus
from core.constants import (
    EMPLOYEE_DEFAULT_HOURS, EMPLOYEE_ALLOWED_CATEGORIES,
    CATEGORY_COVERAGE, FIXED_EMPLOYEES, LAST_RESORT_EMPLOYEE,
    WEEKEND_NEVER_WORK
)


def create_employees() -> List[Employee]:
    """Create all employees with their configurations."""
    employees = []

    for emp_name, (default_start, default_end) in EMPLOYEE_DEFAULT_HOURS.items():
        employee = Employee(
            name=emp_name,
            default_start=default_start,
            default_end=default_end,
            is_fixed=emp_name in FIXED_EMPLOYEES,
            allowed_categories=EMPLOYEE_ALLOWED_CATEGORIES.get(emp_name, set()),
            works_weekends=emp_name not in WEEKEND_NEVER_WORK,
            is_last_resort=emp_name == LAST_RESORT_EMPLOYEE
        )
        employees.append(employee)

    return employees


def create_categories() -> List[Category]:
    """Create all categories with coverage windows."""
    categories = []

    for cat_name, (coverage_start, coverage_end) in CATEGORY_COVERAGE.items():
        # Determine exclusive employees
        exclusive = None
        if cat_name == "Supervisor de Marketing":
            exclusive = {"Cesar"}
        elif cat_name == "Marketing":
            exclusive = {"Oscar"}
        elif cat_name == "Tech":
            exclusive = {"Roberto"}

        category = Category(
            name=cat_name,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            exclusive_employees=exclusive
        )
        categories.append(category)

    return categories


def scenario_normal_week(week_start: date) -> Dict[date, List[EmployeeAvailability]]:
    """
    Scenario 1: Normal week with no absences.

    All employees working their default hours.
    """
    availability = {}
    employees = create_employees()

    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_availability = []

        for employee in employees:
            # Weekend rules
            if current_date.weekday() in [5, 6]:  # Weekend
                if not employee.works_weekends:
                    status = WorkStatus.DAY_OFF
                else:
                    status = WorkStatus.WORKING
            else:
                status = WorkStatus.WORKING

            avail = EmployeeAvailability(
                employee_name=employee.name,
                date=current_date,
                status=status,
                start_time=None,  # Use default
                end_time=None,
                notes=""
            )
            day_availability.append(avail)

        availability[current_date] = day_availability

    return availability


def scenario_ana_vacation(week_start: date) -> Dict[date, List[EmployeeAvailability]]:
    """
    Scenario 2: Ana on vacation Tuesday through Thursday.

    This tests the system's ability to handle absences and potentially
    trigger Salas+Helpdesk overlap as a fallback.
    """
    availability = {}
    employees = create_employees()

    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_availability = []

        for employee in employees:
            # Determine status
            if employee.name == "Ana" and current_date.weekday() in [1, 2, 3]:  # Tue, Wed, Thu
                status = WorkStatus.VACATION
                notes = "Scheduled vacation"
            elif current_date.weekday() in [5, 6]:  # Weekend
                if not employee.works_weekends:
                    status = WorkStatus.DAY_OFF
                    notes = ""
                else:
                    status = WorkStatus.WORKING
                    notes = ""
            else:
                status = WorkStatus.WORKING
                notes = ""

            avail = EmployeeAvailability(
                employee_name=employee.name,
                date=current_date,
                status=status,
                start_time=None,
                end_time=None,
                notes=notes
            )
            day_availability.append(avail)

        availability[current_date] = day_availability

    return availability


def scenario_multiple_absences(week_start: date) -> Dict[date, List[EmployeeAvailability]]:
    """
    Scenario 3: Multiple absences forcing Salas+Helpdesk overlap fallback.

    Wednesday:
    - Ana: Vacation
    - Lilian: Day Off
    - Gabriel: Vacation

    This should force the system to use overlap assignments.
    """
    availability = {}
    employees = create_employees()

    absences = {
        "Ana": ([2], WorkStatus.VACATION, "Family event"),  # Wednesday
        "Lilian": ([2], WorkStatus.DAY_OFF, "Personal day"),
        "Gabriel": ([2], WorkStatus.VACATION, "Vacation"),
    }

    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_availability = []

        for employee in employees:
            status = WorkStatus.WORKING
            notes = ""

            # Check for absences
            if employee.name in absences:
                absence_days, absence_status, absence_notes = absences[employee.name]
                if current_date.weekday() in absence_days:
                    status = absence_status
                    notes = absence_notes

            # Weekend rules
            if current_date.weekday() in [5, 6]:  # Weekend
                if not employee.works_weekends:
                    status = WorkStatus.DAY_OFF
                    notes = ""

            avail = EmployeeAvailability(
                employee_name=employee.name,
                date=current_date,
                status=status,
                start_time=None,
                end_time=None,
                notes=notes
            )
            day_availability.append(avail)

        availability[current_date] = day_availability

    return availability


def scenario_custom_hours(week_start: date) -> Dict[date, List[EmployeeAvailability]]:
    """
    Scenario 4: Custom hours for flexible employees.

    Tests hour override functionality:
    - Luisa works 10AM-06PM on Tuesday (instead of 12PM-08PM)
    - Pedro works 12PM-08PM on Thursday (instead of 02PM-10PM)
    """
    availability = {}
    employees = create_employees()

    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_availability = []

        for employee in employees:
            status = WorkStatus.WORKING
            start_override = None
            end_override = None
            notes = ""

            # Custom hours
            if employee.name == "Luisa" and current_date.weekday() == 1:  # Tuesday
                start_override = time(10, 0)
                end_override = time(18, 0)
                notes = "Custom hours for training"

            if employee.name == "Pedro" and current_date.weekday() == 3:  # Thursday
                start_override = time(12, 0)
                end_override = time(20, 0)
                notes = "Adjusted schedule"

            # Weekend rules
            if current_date.weekday() in [5, 6]:
                if not employee.works_weekends:
                    status = WorkStatus.DAY_OFF

            avail = EmployeeAvailability(
                employee_name=employee.name,
                date=current_date,
                status=status,
                start_time=start_override,
                end_time=end_override,
                notes=notes
            )
            day_availability.append(avail)

        availability[current_date] = day_availability

    return availability


def get_scenario(scenario_name: str, week_start: date) -> Dict[date, List[EmployeeAvailability]]:
    """
    Get availability data for a named scenario.

    Args:
        scenario_name: Name of the scenario
        week_start: Monday of the week

    Returns:
        Availability dictionary
    """
    scenarios = {
        "Normal Week": scenario_normal_week,
        "Ana Vacation (Tue-Thu)": scenario_ana_vacation,
        "Multiple Absences": scenario_multiple_absences,
        "Custom Hours": scenario_custom_hours,
    }

    if scenario_name not in scenarios:
        return scenario_normal_week(week_start)

    return scenarios[scenario_name](week_start)

"""Constants and configuration for the scheduling system."""

from datetime import time
from typing import Dict, Tuple

# Time block configuration
BLOCK_SIZE_MINUTES = 30
DAY_START_HOUR = 8
DAY_END_HOUR = 24

# Categories and their required coverage windows
CATEGORY_COVERAGE: Dict[str, Tuple[time, time]] = {
    "Salas": (time(12, 0), time(0, 0)),  # 12PM-12AM
    "Helpdesk": (time(8, 0), time(0, 0)),  # 08AM-12AM
    "Tech": (time(10, 0), time(18, 0)),  # 10AM-06PM
    "Supervisor/Marketing": (time(11, 0), time(19, 0)),  # 11AM-07PM
    "Marketing": (time(9, 0), time(17, 0)),  # 09AM-05PM
    "HD Supervisor": (time(11, 0), time(19, 0)),  # 11AM-07PM (Anderson only, flexible)
}

# All categories list
CATEGORIES = list(CATEGORY_COVERAGE.keys())

# Work status options
STATUS_WORKING = "Working"
STATUS_DAY_OFF = "DayOff"
STATUS_VACATION = "Vacation"

# Weekend rules
WEEKENDS_OFF_PER_MONTH = 2
WEEKENDS_WORKING_PER_MONTH = 2

# Employee fixed/flexible configuration
FIXED_EMPLOYEES = {"Cesar", "Roberto", "Oscar", "Amanda"}
FLEXIBLE_EMPLOYEES = {"Ana", "Lilian", "Luisa", "Anderson", "Pedro", "Gabriel"}

# Default working hours for employees
EMPLOYEE_DEFAULT_HOURS: Dict[str, Tuple[time, time]] = {
    "Ana": (time(8, 0), time(16, 0)),       # 08AM-04PM
    "Cesar": (time(11, 0), time(19, 0)),    # 11AM-07PM (FIXED)
    "Lilian": (time(18, 0), time(0, 0)),    # 06PM-12AM
    "Luisa": (time(12, 0), time(20, 0)),    # 12PM-08PM
    "Anderson": (time(11, 0), time(19, 0)), # 11AM-07PM
    "Pedro": (time(14, 0), time(22, 0)),    # 02PM-10PM
    "Gabriel": (time(18, 0), time(0, 0)),   # 06PM-12AM
    "Roberto": (time(10, 0), time(18, 0)),  # 10AM-06PM (FIXED)
    "Oscar": (time(8, 0), time(17, 0)),     # 08AM-05PM (FIXED)
    "Amanda": (time(18, 0), time(21, 0)),   # 06PM-09PM (FIXED, 3 hours only)
}

# Category eligibility rules
CATEGORY_EXCLUSIVE_EMPLOYEES: Dict[str, set] = {
    "Supervisor/Marketing": {"Cesar"},
    "Marketing": {"Oscar"},
    "Tech": {"Roberto"},
    "HD Supervisor": {"Anderson"},
}

# Employee-specific category restrictions
EMPLOYEE_ALLOWED_CATEGORIES: Dict[str, set] = {
    "Cesar": {"Supervisor/Marketing"},
    "Oscar": {"Marketing"},
    "Roberto": {"Tech"},
    "Amanda": {"Salas"},
    # Flexible employees can do Salas and Helpdesk
    "Ana": {"Salas", "Helpdesk"},
    "Lilian": {"Salas", "Helpdesk"},
    "Luisa": {"Salas", "Helpdesk"},
    "Anderson": {"Salas", "Helpdesk", "HD Supervisor"},
    "Pedro": {"Salas", "Helpdesk"},
    "Gabriel": {"Salas", "Helpdesk"},
}

# Employees who never work weekends
WEEKEND_NEVER_WORK = {"Cesar", "Oscar", "Roberto", "Amanda"}

# Categories that are staffed on weekends
WEEKEND_CATEGORIES = {"Salas", "Helpdesk"}

# Last resort employee (use only when needed)
LAST_RESORT_EMPLOYEE = "Anderson"

# Anderson's special weekend rule
ANDERSON_WEEKEND_CATEGORY = "Helpdesk"
ANDERSON_WEEKEND_HOURS = (time(8, 0), time(16, 0))  # 08AM-04PM on Saturdays

# Flexible employee hour adjustment priority
# Priority order for adjusting hours when coverage is needed
HOUR_ADJUSTMENT_PRIORITY = [
    "Anderson",   # First priority - morning coverage
    "Gabriel",    # Second priority - afternoon/night
    "Pedro",      # Third priority - afternoon/night
    "Luisa",      # Fourth priority - general flexible
    "Ana",        # Fifth priority - general flexible
    "Lilian",     # Sixth priority - general flexible
]

# Employees whose hours can be adjusted for coverage
FULLY_FLEXIBLE_EMPLOYEES = {"Anderson", "Gabriel", "Pedro", "Luisa", "Ana", "Lilian"}

# Day names
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKEND_DAYS = ["Saturday", "Sunday"]
ALL_DAYS = WEEKDAYS + WEEKEND_DAYS

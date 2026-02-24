"""Schedule validation logic."""

from datetime import date, time
from typing import List, Dict, Set
from collections import defaultdict

from core.models import (
    WeekSchedule, DaySchedule, Assignment, ValidationResult,
    TimeBlock, Employee, Category, EmployeeAvailability, WorkStatus
)
from core.constants import (
    EMPLOYEE_ALLOWED_CATEGORIES, FIXED_EMPLOYEES,
    EMPLOYEE_DEFAULT_HOURS, WEEKEND_NEVER_WORK
)
from core.utils import blocks_overlap, is_weekend


class ScheduleValidator:
    """Validates schedules against business rules."""

    def __init__(self, employees: List[Employee], categories: List[Category]):
        self.employees = {emp.name: emp for emp in employees}
        self.categories = {cat.name: cat for cat in categories}

    def validate_week(self, week_schedule: WeekSchedule) -> ValidationResult:
        """
        Validate a complete week schedule.

        Args:
            week_schedule: Week schedule to validate

        Returns:
            ValidationResult with all validation issues
        """
        result = ValidationResult(is_valid=True)

        for day_schedule in week_schedule.days:
            self._validate_day(day_schedule, result)

        return result

    def _validate_day(self, day_schedule: DaySchedule, result: ValidationResult):
        """Validate a single day schedule."""
        # Check coverage for each category
        self._validate_coverage(day_schedule, result)

        # Check for double-bookings
        self._validate_no_double_bookings(day_schedule, result)

        # Check category eligibility
        self._validate_category_eligibility(day_schedule, result)

        # Check fixed employee hours
        self._validate_fixed_hours(day_schedule, result)

        # Check weekend rules
        self._validate_weekend_rules(day_schedule, result)

        # Check overlap rules (Salas+Helpdesk)
        self._validate_overlap_rules(day_schedule, result)

    def _validate_coverage(self, day_schedule: DaySchedule, result: ValidationResult):
        """Validate that all required time blocks are covered."""
        for cat_name, category in self.categories.items():
            required_blocks = category.get_required_blocks()

            for block in required_blocks:
                # Find assignments for this category and block
                assignments = [
                    a for a in day_schedule.assignments
                    if a.category == cat_name and a.time_block == block
                ]

                if not assignments:
                    result.add_uncovered(cat_name, day_schedule.date, block)

    def _validate_no_double_bookings(
        self,
        day_schedule: DaySchedule,
        result: ValidationResult
    ):
        """Check for employee double-bookings (same time, different categories)."""
        employee_assignments: Dict[str, List[Assignment]] = defaultdict(list)

        for assignment in day_schedule.assignments:
            employee_assignments[assignment.employee_name].append(assignment)

        for employee, assignments in employee_assignments.items():
            # Group by time block
            block_assignments: Dict[TimeBlock, List[Assignment]] = defaultdict(list)

            for assignment in assignments:
                block_assignments[assignment.time_block].append(assignment)

            # Check each time block
            for block, block_assigns in block_assignments.items():
                if len(block_assigns) > 1:
                    # Check if it's a valid overlap (Salas + Helpdesk)
                    categories = {a.category for a in block_assigns}

                    if categories == {"Salas", "Helpdesk"}:
                        # Valid overlap, check if marked
                        if not all(a.is_overlap for a in block_assigns):
                            result.add_warning(
                                f"{employee} doing Salas+Helpdesk on "
                                f"{day_schedule.date.strftime('%Y-%m-%d')} at {block} "
                                f"(should be marked as overlap)"
                            )
                    else:
                        result.add_double_booking(employee, day_schedule.date, block)

    def _validate_category_eligibility(
        self,
        day_schedule: DaySchedule,
        result: ValidationResult
    ):
        """Validate employees are assigned to allowed categories."""
        for assignment in day_schedule.assignments:
            employee = assignment.employee_name
            category = assignment.category

            if employee not in EMPLOYEE_ALLOWED_CATEGORIES:
                result.add_violation(
                    f"{employee} not found in eligibility rules for {category}"
                )
                continue

            allowed = EMPLOYEE_ALLOWED_CATEGORIES[employee]

            if category not in allowed:
                result.add_violation(
                    f"{employee} assigned to {category} but only allowed: {allowed}"
                )

    def _validate_fixed_hours(self, day_schedule: DaySchedule, result: ValidationResult):
        """Validate fixed employees work only their assigned hours."""
        for assignment in day_schedule.assignments:
            employee = assignment.employee_name

            if employee not in FIXED_EMPLOYEES:
                continue

            # Get employee's default hours
            default_start, default_end = EMPLOYEE_DEFAULT_HOURS[employee]

            # Check if assignment block is within default hours
            block = assignment.time_block

            # Simple check: block start should be >= default start
            # and block end should be <= default end (or handle midnight)
            if not self._time_in_employee_hours(
                block.start_time,
                default_start,
                default_end
            ):
                result.add_violation(
                    f"Fixed employee {employee} assigned outside hours "
                    f"({default_start}-{default_end}) at {block} on "
                    f"{day_schedule.date.strftime('%Y-%m-%d')}"
                )

    def _time_in_employee_hours(
        self,
        check_time: time,
        start: time,
        end: time
    ) -> bool:
        """Check if time is within employee working hours."""
        if end < start:  # Crosses midnight
            return check_time >= start or check_time < end
        else:
            return start <= check_time < end

    def _validate_weekend_rules(self, day_schedule: DaySchedule, result: ValidationResult):
        """Validate weekend work rules."""
        if not is_weekend(day_schedule.date):
            return

        for assignment in day_schedule.assignments:
            employee = assignment.employee_name

            if employee in WEEKEND_NEVER_WORK:
                result.add_violation(
                    f"{employee} should never work weekends but assigned on "
                    f"{day_schedule.date.strftime('%Y-%m-%d')}"
                )

    def _validate_overlap_rules(self, day_schedule: DaySchedule, result: ValidationResult):
        """Validate Salas+Helpdesk overlap only happens when needed."""
        # Find all overlaps
        employee_assignments: Dict[str, List[Assignment]] = defaultdict(list)

        for assignment in day_schedule.assignments:
            if assignment.is_overlap:
                employee_assignments[assignment.employee_name].append(assignment)

        for employee, overlaps in employee_assignments.items():
            if overlaps:
                # Overlap should only happen if it's a fallback
                if not all(a.is_fallback for a in overlaps):
                    result.add_warning(
                        f"{employee} has Salas+Helpdesk overlap on "
                        f"{day_schedule.date.strftime('%Y-%m-%d')} but not marked as fallback"
                    )

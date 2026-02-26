"""Main scheduling engine."""

from datetime import date, time
from typing import List, Dict, Optional

from core.models import (
    Employee, Category, WeekSchedule, MonthSchedule, DaySchedule,
    EmployeeAvailability, WorkStatus, ValidationResult, VacationPeriod
)
from core.utils import get_week_dates, get_month_dates, is_weekend, count_weekends_in_month
from core.constants import EMPLOYEE_DEFAULT_HOURS, WEEKEND_NEVER_WORK
from engine.assigner import ScheduleAssigner
from engine.validator import ScheduleValidator
from engine.weekend_tracker import WeekendTracker
from engine.hour_adjuster import HourAdjuster
from engine.weekend_planner import WeekendPlanner, WeekendPlan


class Scheduler:
    """Main scheduling engine coordinating all components."""

    def __init__(self, employees: List[Employee], categories: List[Category]):
        self.employees = employees
        self.categories = categories
        self.employee_map = {emp.name: emp for emp in employees}

        self.assigner = ScheduleAssigner(employees, categories)
        self.validator = ScheduleValidator(employees, categories)
        self.weekend_tracker = WeekendTracker()
        self.hour_adjuster = HourAdjuster(employees, categories)
        self.weekend_planner = WeekendPlanner(employees)
        self.vacation_periods: List[VacationPeriod] = []
        self.current_weekend_plan: Optional[WeekendPlan] = None
        self.previous_weekend_plan: Optional[WeekendPlan] = None

    def generate_week_schedule(
        self,
        week_start: date,
        availability_overrides: Optional[Dict[date, List[EmployeeAvailability]]] = None
    ) -> WeekSchedule:
        """
        Generate a complete week schedule.

        Args:
            week_start: Monday date for week start
            availability_overrides: Optional dict of date -> availability list

        Returns:
            WeekSchedule object
        """
        if availability_overrides is None:
            availability_overrides = {}

        week_schedule = WeekSchedule(week_start=week_start, days=[])

        # Generate schedule for each day
        week_dates = get_week_dates(week_start)

        for target_date, day_name in week_dates:
            # Get or create availability for this day
            if target_date in availability_overrides:
                availability = availability_overrides[target_date]
            else:
                availability = self._create_default_availability(target_date)

            # Generate assignments
            assignments = self.assigner.assign_day(target_date, availability)

            # Create day schedule
            day_schedule = DaySchedule(
                date=target_date,
                day_of_week=day_name,
                assignments=assignments,
                availability=availability
            )

            week_schedule.days.append(day_schedule)

        # Update weekend tracking
        employee_names = [emp.name for emp in self.employees]
        self.weekend_tracker.update_from_schedule(week_schedule.days, employee_names)

        return week_schedule

    def _create_default_availability(self, target_date: date) -> List[EmployeeAvailability]:
        """Create default availability for all employees on a date."""
        availability = []

        for employee in self.employees:
            # Weekend rules
            if is_weekend(target_date):
                if employee.name in WEEKEND_NEVER_WORK:
                    status = WorkStatus.DAY_OFF
                else:
                    status = WorkStatus.WORKING

                # On weekends, employees are flexible (don't use default hours)
                # Exception: Anderson has fixed Saturday hours
                start_override = None
                end_override = None
                notes = ""

                if employee.name == "Anderson" and target_date.weekday() == 5:  # Saturday
                    start_override = time(8, 0)
                    end_override = time(16, 0)
                    notes = "Anderson Saturday fixed hours"
            else:
                # Weekdays: use normal default hours
                status = WorkStatus.WORKING
                start_override = None
                end_override = None
                notes = ""

            avail = EmployeeAvailability(
                employee_name=employee.name,
                date=target_date,
                status=status,
                start_time=start_override,
                end_time=end_override,
                notes=notes
            )

            availability.append(avail)

        return availability

    def validate_schedule(self, week_schedule: WeekSchedule) -> ValidationResult:
        """
        Validate a week schedule.

        Args:
            week_schedule: Schedule to validate

        Returns:
            ValidationResult
        """
        return self.validator.validate_week(week_schedule)

    def regenerate_with_updates(
        self,
        week_schedule: WeekSchedule,
        updated_availability: Dict[date, List[EmployeeAvailability]]
    ) -> WeekSchedule:
        """
        Regenerate schedule with updated availability.

        Args:
            week_schedule: Existing schedule
            updated_availability: New availability data

        Returns:
            New WeekSchedule
        """
        return self.generate_week_schedule(
            week_schedule.week_start,
            updated_availability
        )

    def get_weekend_summary(self, month: date) -> Dict[str, dict]:
        """
        Get weekend work summary for a month.

        Args:
            month: Any date in the target month

        Returns:
            Dict of employee -> summary data
        """
        summary = self.weekend_tracker.get_weekend_summary(month)

        result = {}
        for employee, tracking in summary.items():
            result[employee] = {
                "weekends_off": tracking.weekends_off,
                "weekends_worked_saturday": tracking.weekends_worked_saturday,
                "weekends_worked_sunday": tracking.weekends_worked_sunday,
                "total_worked": tracking.total_weekends_worked,
                "is_compliant": tracking.is_compliant
            }

        return result

    def generate_month_schedule(
        self,
        month_start: date,
        availability_overrides: Optional[Dict[date, List[EmployeeAvailability]]] = None,
        vacation_periods: Optional[List[VacationPeriod]] = None
    ) -> MonthSchedule:
        """
        Generate a complete month schedule.

        Args:
            month_start: First day of the month
            availability_overrides: Optional dict of date -> availability list
            vacation_periods: Optional list of vacation periods

        Returns:
            MonthSchedule object
        """
        if availability_overrides is None:
            availability_overrides = {}

        if vacation_periods:
            self.vacation_periods = vacation_periods

        # Plan weekend assignments for the month, passing the previous month's plan
        # so the consecutive-weekend constraint can be enforced across month boundaries.
        self.previous_weekend_plan = self.current_weekend_plan
        self.current_weekend_plan = self.weekend_planner.plan_month_weekends(
            month_start, previous_plan=self.previous_weekend_plan
        )

        month_schedule = MonthSchedule(month_start=month_start, days=[])

        # Generate schedule for each day in month
        month_dates = get_month_dates(month_start)

        for target_date, day_name in month_dates:
            # Get or create availability for this day
            if target_date in availability_overrides:
                availability = availability_overrides[target_date]
            else:
                availability = self._create_default_availability_with_vacations(target_date)

            # Apply hour adjustments for coverage (skip on weekends - fixed shifts)
            if not is_weekend(target_date):
                availability = self._apply_hour_adjustments(target_date, availability)

            # Generate assignments
            assignments = self.assigner.assign_day(target_date, availability)

            # Create day schedule
            day_schedule = DaySchedule(
                date=target_date,
                day_of_week=day_name,
                assignments=assignments,
                availability=availability
            )

            month_schedule.days.append(day_schedule)

        # Update weekend tracking
        employee_names = [emp.name for emp in self.employees]
        self.weekend_tracker.update_from_schedule(month_schedule.days, employee_names)

        return month_schedule

    def _create_default_availability_with_vacations(
        self,
        target_date: date
    ) -> List[EmployeeAvailability]:
        """Create default availability considering vacation periods and weekend plan."""
        availability = []

        for employee in self.employees:
            # Check if employee is on vacation
            is_on_vacation = any(
                vp.employee_name == employee.name and vp.contains_date(target_date)
                for vp in self.vacation_periods
            )

            if is_on_vacation:
                status = WorkStatus.VACATION
                start_override = None
                end_override = None
                notes = "On vacation"
            elif employee.name in WEEKEND_NEVER_WORK and is_weekend(target_date):
                # Never work weekends
                status = WorkStatus.DAY_OFF
                start_override = None
                end_override = None
                notes = ""
            elif self.current_weekend_plan:
                # Use weekend plan for status and hours
                weekend_status, weekend_notes, shift_start, shift_end = self.weekend_planner.get_availability_for_date(
                    target_date,
                    self.current_weekend_plan,
                    employee.name
                )

                status = weekend_status
                notes = weekend_notes

                # Set hours based on weekend shift assignment
                if status == WorkStatus.WORKING and is_weekend(target_date):
                    # Use shift hours returned by weekend planner
                    start_override = shift_start
                    end_override = shift_end
                elif status == WorkStatus.WORKING:
                    # Weekday - use default hours
                    start_override = None
                    end_override = None
                else:
                    # DAY_OFF or other status
                    start_override = None
                    end_override = None
            else:
                # Fallback if no weekend plan
                status = WorkStatus.WORKING
                start_override = None
                end_override = None
                notes = ""

            avail = EmployeeAvailability(
                employee_name=employee.name,
                date=target_date,
                status=status,
                start_time=start_override,
                end_time=end_override,
                notes=notes
            )

            availability.append(avail)

        return availability

    def _apply_hour_adjustments(
        self,
        target_date: date,
        availability: List[EmployeeAvailability]
    ) -> List[EmployeeAvailability]:
        """
        Apply hour adjustments to ensure coverage.

        Args:
            target_date: Date to adjust for
            availability: Current availability

        Returns:
            Adjusted availability
        """
        # First, do a preliminary assignment to see what gaps exist
        preliminary_assignments = self.assigner.assign_day(target_date, availability)

        # Find coverage gaps
        coverage_gaps = {}
        for category in self.categories:
            gaps = self.hour_adjuster.find_coverage_gaps(
                preliminary_assignments,
                category.name
            )
            if gaps:
                coverage_gaps[category.name] = gaps

        # If there are gaps, adjust hours
        if coverage_gaps:
            adjusted_availability = self.hour_adjuster.adjust_hours_for_coverage(
                target_date,
                availability,
                coverage_gaps
            )
            return adjusted_availability

        return availability

    def set_vacation_periods(self, vacation_periods: List[VacationPeriod]):
        """Set vacation periods for scheduling."""
        self.vacation_periods = vacation_periods

    def validate_month_schedule(self, month_schedule: MonthSchedule) -> ValidationResult:
        """
        Validate a month schedule.

        Args:
            month_schedule: Schedule to validate

        Returns:
            ValidationResult
        """
        # Reuse week validator for all days
        result = ValidationResult(is_valid=True)

        for day_schedule in month_schedule.days:
            # Create temporary week schedule for validation
            temp_week = WeekSchedule(week_start=day_schedule.date, days=[day_schedule])
            day_result = self.validator.validate_week(temp_week)

            # Merge results
            result.uncovered_blocks.update(day_result.uncovered_blocks)
            result.rule_violations.extend(day_result.rule_violations)
            result.double_bookings.extend(day_result.double_bookings)
            result.warnings.extend(day_result.warnings)

            if not day_result.is_valid:
                result.is_valid = False

        return result

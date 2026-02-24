"""Weekend tracking and rule enforcement."""

from datetime import date
from typing import Dict, List
from collections import defaultdict

from core.models import WeekendTracking, DaySchedule, EmployeeAvailability, WorkStatus
from core.constants import WEEKEND_NEVER_WORK, WEEKENDS_OFF_PER_MONTH
from core.utils import get_month_start


class WeekendTracker:
    """Tracks and validates weekend work rules."""

    def __init__(self):
        self.tracking: Dict[str, Dict[date, WeekendTracking]] = defaultdict(dict)

    def update_from_schedule(self, day_schedules: List[DaySchedule], employees: List[str]):
        """
        Update weekend tracking based on schedule.

        Args:
            day_schedules: List of day schedules
            employees: List of all employee names
        """
        for day_schedule in day_schedules:
            if day_schedule.date.weekday() not in [5, 6]:  # Not weekend
                continue

            month_start = get_month_start(day_schedule.date)

            for employee in employees:
                if employee not in self.tracking:
                    self.tracking[employee] = {}

                if month_start not in self.tracking[employee]:
                    self.tracking[employee][month_start] = WeekendTracking(
                        employee_name=employee,
                        month=month_start
                    )

                # Check if employee worked this day
                employee_avail = self._get_employee_availability(day_schedule, employee)
                worked = employee_avail and employee_avail.status == WorkStatus.WORKING

                # Get weekend number in month
                weekend_num = self._get_weekend_number(day_schedule.date)

                if worked:
                    if day_schedule.date.weekday() == 5:  # Saturday
                        self.tracking[employee][month_start].weekends_worked_saturday += 1
                    else:  # Sunday
                        self.tracking[employee][month_start].weekends_worked_sunday += 1

    def _get_employee_availability(
        self,
        day_schedule: DaySchedule,
        employee: str
    ) -> EmployeeAvailability:
        """Get employee availability for a day."""
        for avail in day_schedule.availability:
            if avail.employee_name == employee:
                return avail
        return None

    def _get_weekend_number(self, target_date: date) -> int:
        """Get which weekend of the month (1-4/5) this date belongs to."""
        day = target_date.day
        return (day - 1) // 7 + 1

    def get_tracking(self, employee: str, month: date) -> WeekendTracking:
        """Get weekend tracking for an employee in a specific month."""
        month_start = get_month_start(month)

        if employee not in self.tracking or month_start not in self.tracking[employee]:
            return WeekendTracking(employee_name=employee, month=month_start)

        return self.tracking[employee][month_start]

    def can_work_weekend(self, employee: str, target_date: date) -> bool:
        """
        Check if employee can work on a weekend day based on rules.

        Args:
            employee: Employee name
            target_date: Date to check (must be Sat/Sun)

        Returns:
            True if employee can work this weekend
        """
        if employee in WEEKEND_NEVER_WORK:
            return False

        month_start = get_month_start(target_date)
        tracking = self.get_tracking(employee, month_start)

        # Check if already worked 2 weekends
        if tracking.total_weekends_worked >= 2:
            return False

        return True

    def should_be_off(self, employee: str, target_date: date) -> bool:
        """
        Check if employee should be off this weekend.

        Args:
            employee: Employee name
            target_date: Date to check

        Returns:
            True if employee should be off
        """
        if employee in WEEKEND_NEVER_WORK:
            return True

        return not self.can_work_weekend(employee, target_date)

    def get_weekend_summary(self, month: date) -> Dict[str, WeekendTracking]:
        """Get weekend tracking summary for all employees in a month."""
        month_start = get_month_start(month)
        summary = {}

        for employee, months in self.tracking.items():
            if month_start in months:
                summary[employee] = months[month_start]
            else:
                summary[employee] = WeekendTracking(
                    employee_name=employee,
                    month=month_start
                )

        return summary

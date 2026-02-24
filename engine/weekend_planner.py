"""Weekend planning and assignment logic."""

from datetime import date, timedelta, time
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import random

from core.models import Employee, EmployeeAvailability, WorkStatus
from core.utils import get_month_dates, is_weekend
from core.constants import WEEKEND_NEVER_WORK


class WeekendPlan:
    """Plan for weekend assignments in a month."""

    def __init__(self, month_start: date):
        self.month_start = month_start
        # Dict of date -> dict of shift -> employee name
        # Shifts: "morning" (08:00-16:00) and "evening" (16:00-24:00)
        self.saturday_assignments: Dict[date, Dict[str, str]] = {}
        self.sunday_assignments: Dict[date, Dict[str, str]] = {}
        # Compensatory days off: employee -> list of dates
        self.compensatory_days: Dict[str, List[date]] = defaultdict(list)


class WeekendPlanner:
    """Plans weekend assignments to ensure fair distribution."""

    def __init__(self, employees: List[Employee]):
        self.employees = employees
        # Get weekend-eligible employees
        self.weekend_workers = [
            emp.name for emp in employees
            if emp.name not in WEEKEND_NEVER_WORK
        ]

    def plan_month_weekends(self, month_start: date) -> WeekendPlan:
        """
        Plan weekend assignments for a month.

        Requirements:
        - 2 employees per day (Saturday and Sunday)
        - Each employee works 2 weekends (1 day each = 2 days total)
        - Anderson always works Saturday only
        - Give compensatory Friday/Monday off when needed

        Args:
            month_start: First day of month

        Returns:
            WeekendPlan with assignments
        """
        plan = WeekendPlan(month_start)

        # Get all weekend dates in month
        weekends = self._get_weekends_in_month(month_start)

        # Plan assignments
        if len(weekends) == 4:
            # Standard month with 4 weekends
            self._plan_four_weekends(weekends, plan)
        elif len(weekends) == 5:
            # Month with 5 weekends
            self._plan_five_weekends(weekends, plan)
        else:
            # Fallback for unusual cases
            self._plan_generic(weekends, plan)

        # Assign compensatory days off
        self._assign_compensatory_days(month_start, plan)

        return plan

    def _get_weekends_in_month(self, month_start: date) -> List[Tuple[date, date]]:
        """Get list of (Saturday, Sunday) tuples for the month.

        If the month starts on a Sunday, the preceding month's Saturday is used
        to pair with that Sunday so it is included in weekend planning.
        """
        month_dates = get_month_dates(month_start)
        weekends = []

        # If the month opens on a Sunday, pair it with the prior month's Saturday
        if month_start.weekday() == 6:  # Sunday
            prev_saturday = month_start - timedelta(days=1)
            weekends.append((prev_saturday, month_start))

        current_weekend = None
        for day_date, day_name in month_dates:
            if day_name == "Saturday":
                current_weekend = [day_date, None]
            elif day_name == "Sunday" and current_weekend:
                current_weekend[1] = day_date
                weekends.append(tuple(current_weekend))
                current_weekend = None

        return weekends

    def _plan_four_weekends(self, weekends: List[Tuple[date, date]], plan: WeekendPlan):
        """
        Plan for standard 4-weekend month with morning/evening shifts.

        Strategy:
        - 4 weekends × 2 days × 2 shifts = 16 employee-shifts needed
        - Each employee works 2 shifts total
        - Anderson: 2 Saturday morning shifts (08:00-16:00, fixed)
        - Other 6 employees: distribute across remaining 14 shifts
        - Some employees work 2 shifts, some work 3 (with compensatory days)

        Shifts:
        - Morning: 08:00-16:00
        - Evening: 16:00-24:00
        """
        saturday_dates = [w[0] for w in weekends]
        sunday_dates = [w[1] for w in weekends]

        # Initialize all weekend days with empty shift assignments
        for sat in saturday_dates:
            plan.saturday_assignments[sat] = {"morning": None, "evening": None}
        for sun in sunday_dates:
            plan.sunday_assignments[sun] = {"morning": None, "evening": None}

        # Anderson takes 2 Saturday morning shifts — only from Saturdays within the current month
        in_month_saturdays = [d for d in saturday_dates if d.month == plan.month_start.month]
        anderson_saturdays = random.sample(in_month_saturdays, min(2, len(in_month_saturdays)))
        for sat in anderson_saturdays:
            plan.saturday_assignments[sat]["morning"] = "Anderson"

        # Remove Anderson from pool
        other_workers = [w for w in self.weekend_workers if w != "Anderson"]

        # Track shifts per employee
        employee_shifts = defaultdict(int)

        # Collect all unfilled shifts — skip cross-month Saturdays to avoid wasted slots
        unfilled_shifts = []

        for sat in saturday_dates:
            if sat.month != plan.month_start.month:  # e.g. Jan 31 in a Feb plan
                continue
            if plan.saturday_assignments[sat]["morning"] is None:
                unfilled_shifts.append((sat, "morning"))
            if plan.saturday_assignments[sat]["evening"] is None:
                unfilled_shifts.append((sat, "evening"))

        for sun in sunday_dates:
            unfilled_shifts.append((sun, "morning"))
            unfilled_shifts.append((sun, "evening"))

        # Shuffle for randomness
        random.shuffle(unfilled_shifts)

        # Fill shifts — always use a different employee for morning vs. evening on the same day
        for shift_date, shift_type in unfilled_shifts:
            other_type = "evening" if shift_type == "morning" else "morning"
            day_map = (
                plan.saturday_assignments[shift_date]
                if shift_date.weekday() == 5
                else plan.sunday_assignments[shift_date]
            )

            available = sorted(
                [(emp, employee_shifts[emp]) for emp in other_workers],
                key=lambda x: x[1]
            )

            for emp, _ in available:
                # Skip if this employee already covers the other shift today
                if day_map.get(other_type) == emp:
                    continue
                day_map[shift_type] = emp
                employee_shifts[emp] += 1
                break

    def _plan_five_weekends(self, weekends: List[Tuple[date, date]], plan: WeekendPlan):
        """
        Plan for 5-weekend month with morning/evening shifts.

        Strategy:
        - 5 weekends × 2 days × 2 shifts = 20 employee-shifts needed
        - Anderson: 2 Saturday morning shifts
        - Other 6 employees: cover 18 shifts
        - Average: 3 shifts per employee
        """
        saturday_dates = [w[0] for w in weekends]
        sunday_dates = [w[1] for w in weekends]

        # Initialize all weekend days with empty shift assignments
        for sat in saturday_dates:
            plan.saturday_assignments[sat] = {"morning": None, "evening": None}
        for sun in sunday_dates:
            plan.sunday_assignments[sun] = {"morning": None, "evening": None}

        # Anderson takes 2 Saturday morning shifts — only from Saturdays within the current month
        in_month_saturdays = [d for d in saturday_dates if d.month == plan.month_start.month]
        anderson_saturdays = random.sample(in_month_saturdays, min(2, len(in_month_saturdays)))
        for sat in anderson_saturdays:
            plan.saturday_assignments[sat]["morning"] = "Anderson"

        # Remove Anderson from pool
        other_workers = [w for w in self.weekend_workers if w != "Anderson"]

        # Track shifts per employee
        employee_shifts = defaultdict(int)

        # Collect all unfilled shifts — skip cross-month Saturdays to avoid wasted slots
        unfilled_shifts = []

        for sat in saturday_dates:
            if sat.month != plan.month_start.month:  # e.g. Jan 31 in a Feb plan
                continue
            if plan.saturday_assignments[sat]["morning"] is None:
                unfilled_shifts.append((sat, "morning"))
            if plan.saturday_assignments[sat]["evening"] is None:
                unfilled_shifts.append((sat, "evening"))

        for sun in sunday_dates:
            unfilled_shifts.append((sun, "morning"))
            unfilled_shifts.append((sun, "evening"))

        # Shuffle for randomness
        random.shuffle(unfilled_shifts)

        # Fill shifts — always use a different employee for morning vs. evening on the same day
        for shift_date, shift_type in unfilled_shifts:
            other_type = "evening" if shift_type == "morning" else "morning"
            day_map = (
                plan.saturday_assignments[shift_date]
                if shift_date.weekday() == 5
                else plan.sunday_assignments[shift_date]
            )

            available = sorted(
                [(emp, employee_shifts[emp]) for emp in other_workers],
                key=lambda x: x[1]
            )

            for emp, _ in available:
                # Skip if this employee already covers the other shift today
                if day_map.get(other_type) == emp:
                    continue
                day_map[shift_type] = emp
                employee_shifts[emp] += 1
                break

    def _plan_generic(self, weekends: List[Tuple[date, date]], plan: WeekendPlan):
        """Fallback planning for unusual cases."""
        self._plan_four_weekends(weekends, plan)

    def _assign_compensatory_days(self, month_start: date, plan: WeekendPlan):
        """
        Assign 2 consecutive days off for weekends not worked.

        Options: Fri-Sat, Sat-Sun, or Sun-Mon
        Cycles through these options to provide variety.
        """
        # Get all weekend dates
        all_saturdays = sorted(plan.saturday_assignments.keys())
        all_sundays = sorted(plan.sunday_assignments.keys())

        # Track which weekends each employee works
        employee_working_weekends = defaultdict(set)

        for sat, shifts in plan.saturday_assignments.items():
            for shift_type, emp in shifts.items():
                if emp:
                    employee_working_weekends[emp].add(sat)

        for sun, shifts in plan.sunday_assignments.items():
            for shift_type, emp in shifts.items():
                if emp:
                    employee_working_weekends[emp].add(sun)

        # For each weekend worker, assign consecutive days off for weekends they DON'T work
        for emp in self.weekend_workers:
            worked_dates = employee_working_weekends.get(emp, set())

            # Cycle through day-off options: Fri-Sat, Sat-Sun, Sun-Mon
            option_cycle = ["fri-sat", "sat-sun", "sun-mon"]
            option_index = 0

            # Check each weekend
            for i, sat in enumerate(all_saturdays):
                sun = all_sundays[i] if i < len(all_sundays) else None

                # Check if employee is NOT working this weekend
                if sat not in worked_dates and (sun is None or sun not in worked_dates):
                    # Assign 2 consecutive days off
                    option = option_cycle[option_index % len(option_cycle)]
                    option_index += 1

                    if option == "fri-sat":
                        # Friday before Saturday
                        friday = sat - timedelta(days=1)
                        if friday.month == month_start.month and friday.weekday() == 4:
                            plan.compensatory_days[emp].append(friday)
                            plan.compensatory_days[emp].append(sat)

                    elif option == "sat-sun" and sun:
                        # Saturday and Sunday
                        if sat.month == month_start.month:      # guard against cross-month Saturday
                            plan.compensatory_days[emp].append(sat)
                        plan.compensatory_days[emp].append(sun)

                    elif option == "sun-mon" and sun:
                        # Sunday and Monday after
                        monday = sun + timedelta(days=1)
                        if monday.month == month_start.month and monday.weekday() == 0:
                            plan.compensatory_days[emp].append(sun)
                            plan.compensatory_days[emp].append(monday)

    def get_availability_for_date(
        self,
        target_date: date,
        plan: WeekendPlan,
        employee_name: str
    ) -> Tuple[WorkStatus, str, Optional[time], Optional[time]]:
        """
        Get employee status and hours for a date based on weekend plan.

        Returns:
            (status, notes, start_time, end_time)
        """
        # Check if it's a compensatory day off
        if employee_name in plan.compensatory_days:
            if target_date in plan.compensatory_days[employee_name]:
                return WorkStatus.DAY_OFF, "Compensatory day off", None, None

        # Check if it's a weekend
        if not is_weekend(target_date):
            return WorkStatus.WORKING, "", None, None

        # Check weekend shift assignments
        day_name = target_date.strftime("%A")

        if day_name == "Saturday":
            if target_date in plan.saturday_assignments:
                shifts = plan.saturday_assignments[target_date]

                # Check if employee is assigned to morning shift
                if shifts.get("morning") == employee_name:
                    return WorkStatus.WORKING, "Saturday morning shift", time(8, 0), time(16, 0)

                # Check if employee is assigned to evening shift
                if shifts.get("evening") == employee_name:
                    return WorkStatus.WORKING, "Saturday evening shift", time(16, 0), time(0, 0)

                # Not assigned to any shift
                return WorkStatus.DAY_OFF, "Weekend off", None, None
            else:
                return WorkStatus.DAY_OFF, "Weekend off", None, None

        elif day_name == "Sunday":
            if target_date in plan.sunday_assignments:
                shifts = plan.sunday_assignments[target_date]

                # Check if employee is assigned to morning shift
                if shifts.get("morning") == employee_name:
                    return WorkStatus.WORKING, "Sunday morning shift", time(8, 0), time(16, 0)

                # Check if employee is assigned to evening shift
                if shifts.get("evening") == employee_name:
                    return WorkStatus.WORKING, "Sunday evening shift", time(16, 0), time(0, 0)

                # Not assigned to any shift
                return WorkStatus.DAY_OFF, "Weekend off", None, None
            else:
                return WorkStatus.DAY_OFF, "Weekend off", None, None

        return WorkStatus.WORKING, "", None, None

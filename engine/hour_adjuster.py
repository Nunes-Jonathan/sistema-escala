"""Hour adjustment logic for ensuring coverage."""

from datetime import date, time
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict

from core.models import (
    Employee, Category, TimeBlock, EmployeeAvailability,
    WorkStatus, Assignment
)
from core.constants import (
    HOUR_ADJUSTMENT_PRIORITY, FULLY_FLEXIBLE_EMPLOYEES,
    CATEGORY_COVERAGE, EMPLOYEE_DEFAULT_HOURS
)
from core.utils import get_employee_working_blocks, time_in_range


class HourAdjuster:
    """Adjusts employee hours to ensure category coverage."""

    def __init__(self, employees: List[Employee], categories: List[Category]):
        self.employees = {emp.name: emp for emp in employees}
        self.categories = {cat.name: cat for cat in categories}

    def find_coverage_gaps(
        self,
        day_assignments: List[Assignment],
        category: str
    ) -> List[TimeBlock]:
        """
        Find time blocks that are not covered for a category.

        Args:
            day_assignments: All assignments for the day
            category: Category name to check

        Returns:
            List of uncovered time blocks
        """
        if category not in self.categories:
            return []

        cat = self.categories[category]
        required_blocks = cat.get_required_blocks()

        # Find which blocks have assignments
        assigned_blocks = set()
        for assignment in day_assignments:
            if assignment.category == category:
                assigned_blocks.add(assignment.time_block)

        # Return gaps
        gaps = []
        for block in required_blocks:
            # Check if block is in assigned_blocks
            is_covered = False
            for assigned_block in assigned_blocks:
                if (assigned_block.start_time == block.start_time and
                    assigned_block.end_time == block.end_time):
                    is_covered = True
                    break

            if not is_covered:
                gaps.append(block)

        return gaps

    def adjust_hours_for_coverage(
        self,
        target_date: date,
        availability: List[EmployeeAvailability],
        coverage_gaps: Dict[str, List[TimeBlock]]
    ) -> List[EmployeeAvailability]:
        """
        Adjust flexible employee hours to cover gaps.

        Args:
            target_date: Date to adjust for
            availability: Current availability
            coverage_gaps: Dict of category -> uncovered blocks

        Returns:
            Updated availability with adjusted hours
        """
        if not coverage_gaps:
            return availability

        # Create a map of employee -> availability
        avail_map = {a.employee_name: a for a in availability}
        updated_avail = []

        # Try to adjust hours for each employee in priority order
        for employee_name in HOUR_ADJUSTMENT_PRIORITY:
            if employee_name not in avail_map:
                continue

            avail = avail_map[employee_name]

            # Skip if not working or not flexible
            if avail.status != WorkStatus.WORKING:
                updated_avail.append(avail)
                continue

            if employee_name not in FULLY_FLEXIBLE_EMPLOYEES:
                updated_avail.append(avail)
                continue

            # Try to expand hours to cover gaps
            adjusted = self._try_adjust_employee(
                employee_name,
                avail,
                coverage_gaps
            )

            updated_avail.append(adjusted)

        # Add remaining employees
        for avail in availability:
            if avail.employee_name not in [a.employee_name for a in updated_avail]:
                updated_avail.append(avail)

        return updated_avail

    def _try_adjust_employee(
        self,
        employee_name: str,
        availability: EmployeeAvailability,
        coverage_gaps: Dict[str, List[TimeBlock]]
    ) -> EmployeeAvailability:
        """
        Try to adjust a single employee's hours to cover gaps.

        Args:
            employee_name: Employee to adjust
            availability: Current availability
            coverage_gaps: Gaps to try to cover

        Returns:
            Updated availability
        """
        if employee_name not in self.employees:
            return availability

        employee = self.employees[employee_name]

        # Get current hours
        current_start = availability.start_time or employee.default_start
        current_end = availability.end_time or employee.default_end

        # Find earliest and latest gaps this employee could cover
        earliest_gap = None
        latest_gap = None

        for category, gaps in coverage_gaps.items():
            # Check if employee can do this category
            if category not in employee.allowed_categories:
                continue

            for gap in gaps:
                # Find earliest gap
                if earliest_gap is None or gap.start_time < earliest_gap.start_time:
                    earliest_gap = gap

                # Find latest gap
                if latest_gap is None or gap.end_time > latest_gap.end_time:
                    latest_gap = gap

        # If no gaps this employee can cover, return unchanged
        if earliest_gap is None:
            return availability

        # Adjust start time if needed (e.g., Anderson covering morning)
        new_start = current_start
        if earliest_gap.start_time < current_start:
            # Special logic for Anderson (morning coverage)
            if employee_name == "Anderson":
                new_start = time(8, 0)  # Can start as early as 8AM
            # Gabriel and Pedro can also adjust
            elif employee_name in ["Gabriel", "Pedro"]:
                new_start = earliest_gap.start_time
            else:
                # Other flexible employees can adjust within reason
                new_start = earliest_gap.start_time

        # Adjust end time if needed (less common - we prefer not to extend)
        new_end = current_end
        # Only adjust end if really needed and gap is close to current end
        # This is intentionally conservative per requirements

        # Only update if hours actually changed
        if new_start != current_start or new_end != current_end:
            return EmployeeAvailability(
                employee_name=availability.employee_name,
                date=availability.date,
                status=availability.status,
                start_time=new_start,
                end_time=new_end,
                notes=availability.notes + f" [Hours adjusted for coverage]"
            )

        return availability

    def calculate_required_adjustments(
        self,
        coverage_gaps: Dict[str, List[TimeBlock]],
        availability: List[EmployeeAvailability]
    ) -> Dict[str, Tuple[time, time]]:
        """
        Calculate which employees need hour adjustments.

        Args:
            coverage_gaps: Gaps per category
            availability: Current availability

        Returns:
            Dict of employee_name -> (new_start, new_end)
        """
        adjustments = {}

        for employee_name in HOUR_ADJUSTMENT_PRIORITY:
            # Find earliest gap this employee can cover
            earliest_gap = None

            for category, gaps in coverage_gaps.items():
                employee = self.employees.get(employee_name)
                if not employee:
                    continue

                if category not in employee.allowed_categories:
                    continue

                for gap in gaps:
                    if earliest_gap is None or gap.start_time < earliest_gap.start_time:
                        earliest_gap = gap

            if earliest_gap:
                # Calculate new hours
                avail = next((a for a in availability if a.employee_name == employee_name), None)
                if avail and avail.status == WorkStatus.WORKING:
                    employee = self.employees[employee_name]
                    current_start = avail.start_time or employee.default_start
                    current_end = avail.end_time or employee.default_end

                    if earliest_gap.start_time < current_start:
                        new_start = earliest_gap.start_time
                        if employee_name == "Anderson":
                            new_start = time(8, 0)

                        adjustments[employee_name] = (new_start, current_end)

        return adjustments

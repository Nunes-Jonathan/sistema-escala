"""Assignment algorithm for scheduling."""

from datetime import date, time
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict

from core.models import (
    Employee, Category, TimeBlock, Assignment,
    EmployeeAvailability, WorkStatus
)
from core.constants import (
    EMPLOYEE_ALLOWED_CATEGORIES, LAST_RESORT_EMPLOYEE,
    ANDERSON_WEEKEND_CATEGORY, ANDERSON_WEEKEND_HOURS,
    WEEKEND_NEVER_WORK, WEEKEND_CATEGORIES
)
from core.utils import blocks_overlap, get_employee_working_blocks, is_weekend


class ScheduleAssigner:
    """Assigns employees to categories based on rules and priorities."""

    def __init__(self, employees: List[Employee], categories: List[Category]):
        self.employees = {emp.name: emp for emp in employees}
        self.categories = {cat.name: cat for cat in categories}

    def assign_day(
        self,
        target_date: date,
        availability: List[EmployeeAvailability]
    ) -> List[Assignment]:
        """
        Assign employees to categories for a single day.

        Args:
            target_date: Date to schedule
            availability: Employee availability for this day

        Returns:
            List of assignments
        """
        assignments = []
        avail_map = {a.employee_name: a for a in availability}

        # Track what's been assigned per employee per time block
        employee_blocks: Dict[str, Set[TimeBlock]] = defaultdict(set)

        # Priority order for categories (fixed employees first)
        priority_categories = [
            "Supervisor/Marketing",     # Cesar only
            "Marketing",                # Oscar only
            "Tech",                     # Roberto only
            "Salas",                    # Amanda + others
            "Helpdesk",                 # Flexible employees
            # HD Supervisor handled separately for Anderson
        ]

        # On weekends, only assign Salas and Helpdesk
        # Assign Helpdesk first, then overlap with Salas
        if is_weekend(target_date):
            priority_categories = ["Helpdesk", "Salas"]

        for cat_name in priority_categories:
            category = self.categories[cat_name]
            required_blocks = category.get_required_blocks()

            for block in required_blocks:
                # Find available employees for this category and block
                candidates = self._find_candidates(
                    cat_name,
                    block,
                    target_date,
                    avail_map,
                    employee_blocks
                )

                if not candidates:
                    # Try fallback: Salas+Helpdesk overlap
                    if cat_name in ["Salas", "Helpdesk"]:
                        # On weekends, always try overlap (one person handles both)
                        # On weekdays, only if there are absences
                        fallback = self._try_overlap_fallback(
                            cat_name,
                            block,
                            target_date,
                            avail_map,
                            employee_blocks,
                            assignments,
                            force_overlap_on_weekend=is_weekend(target_date)
                        )
                        if fallback:
                            assignments.append(fallback)
                    continue

                # Score and select best candidate
                best_employee = self._select_best_candidate(
                    candidates,
                    cat_name,
                    block,
                    target_date,
                    avail_map
                )

                # Create assignment
                assignment = Assignment(
                    employee_name=best_employee,
                    category=cat_name,
                    date=target_date,
                    time_block=block,
                    is_overlap=False,
                    is_fallback=False
                )

                assignments.append(assignment)
                employee_blocks[best_employee].add(block)

        # Assign Anderson to HD Supervisor for any unassigned working blocks
        assignments = self._assign_anderson_hd_supervisor(
            assignments,
            employee_blocks,
            avail_map,
            target_date
        )

        return assignments

    def _find_candidates(
        self,
        category: str,
        block: TimeBlock,
        target_date: date,
        avail_map: Dict[str, EmployeeAvailability],
        employee_blocks: Dict[str, Set[TimeBlock]]
    ) -> List[str]:
        """Find eligible employees for a category and time block."""
        candidates = []

        for emp_name, employee in self.employees.items():
            # Check if employee is allowed for this category
            if category not in EMPLOYEE_ALLOWED_CATEGORIES.get(emp_name, set()):
                continue

            # Check availability
            avail = avail_map.get(emp_name)
            if not avail or avail.status != WorkStatus.WORKING:
                continue

            # Get employee's working hours for this day
            start_time = avail.start_time or employee.default_start
            end_time = avail.end_time or employee.default_end

            # Check if block is within working hours
            if not self._block_in_hours(block, start_time, end_time):
                continue

            # Check if already assigned at this time
            if block in employee_blocks.get(emp_name, set()):
                continue

            # Special weekend rules
            if is_weekend(target_date):
                # Check if employee can work weekends
                if emp_name in WEEKEND_NEVER_WORK:
                    continue

                # Anderson special rule: Saturday only, Helpdesk only, 08AM-06PM
                if emp_name == "Anderson":
                    if target_date.weekday() == 5:  # Saturday
                        if category != ANDERSON_WEEKEND_CATEGORY:
                            continue
                        if not self._block_in_hours(
                            block,
                            ANDERSON_WEEKEND_HOURS[0],
                            ANDERSON_WEEKEND_HOURS[1]
                        ):
                            continue
                    else:  # Sunday
                        continue  # Anderson doesn't work Sundays

            candidates.append(emp_name)

        return candidates

    def _block_in_hours(self, block: TimeBlock, start: time, end: time) -> bool:
        """Check if a time block falls within working hours."""
        block_start_minutes = block.start_time.hour * 60 + block.start_time.minute
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute

        # Handle midnight crossing
        if end < start:
            end_minutes += 24 * 60

        if block.end_time < block.start_time:
            block_end_minutes = (block.end_time.hour * 60 + block.end_time.minute) + 24 * 60
        else:
            block_end_minutes = block.end_time.hour * 60 + block.end_time.minute

        return block_start_minutes >= start_minutes and block_end_minutes <= end_minutes

    def _select_best_candidate(
        self,
        candidates: List[str],
        category: str,
        block: TimeBlock,
        target_date: date,
        avail_map: Dict[str, EmployeeAvailability]
    ) -> str:
        """
        Select best candidate using scoring.

        Priorities:
        1. Not Anderson (use as last resort)
        2. Using default hours (no changes needed)
        3. Fixed employees for their categories
        """
        scores = []

        for candidate in candidates:
            score = 0.0
            employee = self.employees[candidate]
            avail = avail_map[candidate]

            # Prefer non-Anderson
            if candidate != LAST_RESORT_EMPLOYEE:
                score += 10.0

            # Prefer employees using default hours
            if avail.start_time is None and avail.end_time is None:
                score += 5.0

            # Prefer fixed employees for their exclusive categories
            if employee.is_fixed:
                score += 8.0

            # Prefer employees already working (to consolidate)
            # This is a simple heuristic
            score += 1.0

            scores.append((score, candidate))

        # Return highest scoring candidate
        scores.sort(reverse=True, key=lambda x: x[0])
        return scores[0][1]

    def _try_overlap_fallback(
        self,
        category: str,
        block: TimeBlock,
        target_date: date,
        avail_map: Dict[str, EmployeeAvailability],
        employee_blocks: Dict[str, Set[TimeBlock]],
        existing_assignments: List[Assignment],
        force_overlap_on_weekend: bool = False
    ) -> Optional[Assignment]:
        """
        Try to assign using Salas+Helpdesk overlap as fallback.

        On weekdays: only allowed if there are missing employees.
        On weekends: always allowed (one person handles both categories).
        """
        # On weekends, always allow overlap
        if not force_overlap_on_weekend:
            # Check if we have absences today (weekday logic)
            has_absences = any(
                a.status in [WorkStatus.DAY_OFF, WorkStatus.VACATION]
                for a in avail_map.values()
            )

            if not has_absences:
                return None  # No fallback needed on weekdays

        # Find someone already assigned to the other category at this time
        other_category = "Helpdesk" if category == "Salas" else "Salas"

        for assignment in existing_assignments:
            if (assignment.category == other_category and
                assignment.time_block == block and
                assignment.date == target_date):

                # Check if this employee can do the requested category too
                employee = assignment.employee_name

                if category not in EMPLOYEE_ALLOWED_CATEGORIES.get(employee, set()):
                    continue

                # Create overlap assignment
                return Assignment(
                    employee_name=employee,
                    category=category,
                    date=target_date,
                    time_block=block,
                    is_overlap=True,
                    is_fallback=True,
                    confidence=0.5  # Lower confidence for overlap
                )

        return None

    def _assign_anderson_hd_supervisor(
        self,
        assignments: List[Assignment],
        employee_blocks: Dict[str, Set[TimeBlock]],
        avail_map: Dict[str, EmployeeAvailability],
        target_date: date
    ) -> List[Assignment]:
        """
        Assign Anderson to HD Supervisor for unassigned working blocks.

        NOTE: HD Supervisor only on weekdays, not weekends.

        Args:
            assignments: Current assignments
            employee_blocks: Blocks assigned per employee
            avail_map: Employee availability
            target_date: Date being scheduled

        Returns:
            Updated assignments with HD Supervisor
        """
        # Check if HD Supervisor category exists
        if "HD Supervisor" not in self.categories:
            return assignments

        # Skip HD Supervisor on weekends (Anderson does Helpdesk on Sat only)
        if is_weekend(target_date):
            return assignments

        # Check if Anderson is working
        anderson_avail = avail_map.get("Anderson")
        if not anderson_avail or anderson_avail.status != WorkStatus.WORKING:
            return assignments

        # Get Anderson's working hours
        anderson_emp = self.employees.get("Anderson")
        if not anderson_emp:
            return assignments

        start_time = anderson_avail.start_time or anderson_emp.default_start
        end_time = anderson_avail.end_time or anderson_emp.default_end

        # Get Anderson's working blocks
        anderson_working_blocks = get_employee_working_blocks(start_time, end_time)

        # Get blocks Anderson is already assigned to
        anderson_assigned = employee_blocks.get("Anderson", set())

        # Assign HD Supervisor to unassigned blocks
        hd_supervisor_category = self.categories["HD Supervisor"]
        hd_required_blocks = hd_supervisor_category.get_required_blocks()

        for block in anderson_working_blocks:
            # Check if this block is in HD Supervisor coverage window
            in_coverage = any(
                req_block.start_time == block.start_time and
                req_block.end_time == block.end_time
                for req_block in hd_required_blocks
            )

            if not in_coverage:
                continue

            # Check if Anderson is already assigned at this block
            already_assigned = any(
                assigned_block.start_time == block.start_time and
                assigned_block.end_time == block.end_time
                for assigned_block in anderson_assigned
            )

            if not already_assigned:
                # Create HD Supervisor assignment
                assignment = Assignment(
                    employee_name="Anderson",
                    category="HD Supervisor",
                    date=target_date,
                    time_block=block,
                    is_overlap=False,
                    is_fallback=False
                )
                assignments.append(assignment)
                employee_blocks["Anderson"].add(block)

        return assignments

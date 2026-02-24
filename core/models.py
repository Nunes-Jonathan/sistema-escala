"""Pydantic data models for the scheduling system."""

from datetime import date, time, datetime, timedelta
from typing import Optional, List, Dict, Set
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class WorkStatus(str, Enum):
    """Employee work status for a given day."""
    WORKING = "Working"
    DAY_OFF = "DayOff"
    VACATION = "Vacation"


class TimeBlock(BaseModel):
    """Represents a 30-minute time block."""
    start_time: time
    end_time: time

    def __str__(self) -> str:
        return f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    def __hash__(self) -> int:
        return hash((self.start_time, self.end_time))


class Employee(BaseModel):
    """Employee definition with default working hours and constraints."""
    name: str
    default_start: time
    default_end: time
    is_fixed: bool = False  # Cannot change hours
    allowed_categories: Set[str] = Field(default_factory=set)
    works_weekends: bool = True  # Can work weekends
    is_last_resort: bool = False  # Use only when needed

    class Config:
        frozen = False


class Category(BaseModel):
    """Work category with required coverage window."""
    name: str
    coverage_start: time
    coverage_end: time
    exclusive_employees: Optional[Set[str]] = None  # Only these employees can do this

    def get_required_blocks(self, block_size_minutes: int = 30) -> List[TimeBlock]:
        """Generate list of time blocks that need coverage."""
        blocks = []
        current = datetime.combine(date.today(), self.coverage_start)
        end = datetime.combine(date.today(), self.coverage_end)

        # Handle midnight crossing
        if self.coverage_end < self.coverage_start:
            end = datetime.combine(date.today(), self.coverage_end)
            end = end + timedelta(days=1)

        while current < end:
            next_time = current + timedelta(minutes=block_size_minutes)
            blocks.append(TimeBlock(
                start_time=current.time(),
                end_time=next_time.time()
            ))
            current = next_time

        return blocks


class EmployeeAvailability(BaseModel):
    """Employee availability for a specific date."""
    employee_name: str
    date: date
    status: WorkStatus = WorkStatus.WORKING
    start_time: Optional[time] = None  # Override default start
    end_time: Optional[time] = None    # Override default end
    notes: str = ""

    class Config:
        use_enum_values = True


class Assignment(BaseModel):
    """Assignment of an employee to a category for a time block."""
    employee_name: str
    category: str
    date: date
    time_block: TimeBlock
    is_overlap: bool = False  # True if doing Salas+Helpdesk simultaneously
    is_fallback: bool = False  # True if this is a fallback assignment
    confidence: float = 1.0  # Assignment confidence score


class DaySchedule(BaseModel):
    """Complete schedule for a single day."""
    date: date
    day_of_week: str
    assignments: List[Assignment] = Field(default_factory=list)
    availability: List[EmployeeAvailability] = Field(default_factory=list)

    def get_assignments_by_category(self, category: str) -> List[Assignment]:
        """Get all assignments for a specific category."""
        return [a for a in self.assignments if a.category == category]

    def get_assignments_by_employee(self, employee: str) -> List[Assignment]:
        """Get all assignments for a specific employee."""
        return [a for a in self.assignments if a.employee_name == employee]


class WeekSchedule(BaseModel):
    """Complete schedule for a week."""
    week_start: date  # Monday
    days: List[DaySchedule] = Field(default_factory=list)

    @field_validator('week_start')
    @classmethod
    def validate_monday(cls, v: date) -> date:
        """Ensure week_start is a Monday."""
        if v.weekday() != 0:
            raise ValueError(f"week_start must be a Monday, got {v.strftime('%A')}")
        return v

    def get_day_schedule(self, target_date: date) -> Optional[DaySchedule]:
        """Get schedule for a specific date."""
        for day in self.days:
            if day.date == target_date:
                return day
        return None


class MonthSchedule(BaseModel):
    """Complete schedule for a calendar month."""
    month_start: date  # First day of month
    days: List[DaySchedule] = Field(default_factory=list)

    @field_validator('month_start')
    @classmethod
    def validate_first_of_month(cls, v: date) -> date:
        """Ensure month_start is the first day of a month."""
        if v.day != 1:
            raise ValueError(f"month_start must be the 1st of the month, got day {v.day}")
        return v

    def get_day_schedule(self, target_date: date) -> Optional[DaySchedule]:
        """Get schedule for a specific date."""
        for day in self.days:
            if day.date == target_date:
                return day
        return None

    @property
    def month_name(self) -> str:
        """Get month name (e.g., 'January 2026')."""
        return self.month_start.strftime("%B %Y")


class VacationPeriod(BaseModel):
    """Vacation period for an employee."""
    employee_name: str
    start_date: date
    end_date: date
    notes: str = ""

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: date, info) -> date:
        """Ensure end_date is after or equal to start_date."""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError("end_date must be after or equal to start_date")
        return v

    def contains_date(self, check_date: date) -> bool:
        """Check if a date falls within this vacation period."""
        return self.start_date <= check_date <= self.end_date


class ValidationResult(BaseModel):
    """Results from schedule validation."""
    is_valid: bool
    uncovered_blocks: Dict[str, List[str]] = Field(default_factory=dict)  # category -> list of "date: time_block"
    rule_violations: List[str] = Field(default_factory=list)
    double_bookings: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def add_uncovered(self, category: str, date: date, time_block: TimeBlock):
        """Add an uncovered time block."""
        key = category
        if key not in self.uncovered_blocks:
            self.uncovered_blocks[key] = []
        self.uncovered_blocks[key].append(f"{date.strftime('%Y-%m-%d')} {time_block}")

    def add_violation(self, message: str):
        """Add a rule violation."""
        self.rule_violations.append(message)
        self.is_valid = False

    def add_double_booking(self, employee: str, date: date, time_block: TimeBlock):
        """Add a double-booking error."""
        msg = f"{employee} double-booked on {date.strftime('%Y-%m-%d')} at {time_block}"
        self.double_bookings.append(msg)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a warning (doesn't invalidate schedule)."""
        self.warnings.append(message)


class WeekendTracking(BaseModel):
    """Track weekend work for an employee in a month."""
    employee_name: str
    month: date  # First day of month
    weekends_off: int = 0
    weekends_worked_saturday: int = 0
    weekends_worked_sunday: int = 0

    @property
    def total_weekends_worked(self) -> int:
        """Total weekends worked (partial or full)."""
        return self.weekends_worked_saturday + self.weekends_worked_sunday

    @property
    def is_compliant(self) -> bool:
        """Check if weekend rules are satisfied."""
        # Should have exactly 2 weekends off and 2 weekends working 1 day
        return self.weekends_off == 2 and self.total_weekends_worked == 2

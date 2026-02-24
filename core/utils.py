"""Utility functions for the scheduling system."""

from datetime import date, time, datetime, timedelta
from typing import List, Tuple
from core.models import TimeBlock


def generate_time_blocks(
    start_hour: int = 8,
    end_hour: int = 24,
    block_size_minutes: int = 30
) -> List[TimeBlock]:
    """
    Generate time blocks for a day.

    Args:
        start_hour: Starting hour (0-23)
        end_hour: Ending hour (1-24)
        block_size_minutes: Size of each block in minutes

    Returns:
        List of TimeBlock objects
    """
    blocks = []
    current = datetime.combine(date.today(), time(start_hour, 0))
    end_time = datetime.combine(date.today(), time(0, 0)) if end_hour == 24 else datetime.combine(date.today(), time(end_hour, 0))

    if end_hour == 24:
        end_time = end_time + timedelta(days=1)

    while current < end_time:
        next_time = current + timedelta(minutes=block_size_minutes)
        blocks.append(TimeBlock(
            start_time=current.time(),
            end_time=next_time.time()
        ))
        current = next_time

    return blocks


def time_in_range(check_time: time, start: time, end: time) -> bool:
    """
    Check if a time falls within a range, handling midnight crossing.

    Args:
        check_time: Time to check
        start: Range start time
        end: Range end time

    Returns:
        True if check_time is in range
    """
    if end < start:  # Crosses midnight
        return check_time >= start or check_time < end
    else:
        return start <= check_time < end


def blocks_overlap(block1: TimeBlock, block2: TimeBlock) -> bool:
    """Check if two time blocks overlap."""
    # Convert to minutes for easier comparison
    b1_start = block1.start_time.hour * 60 + block1.start_time.minute
    b1_end = block1.end_time.hour * 60 + block1.end_time.minute
    b2_start = block2.start_time.hour * 60 + block2.start_time.minute
    b2_end = block2.end_time.hour * 60 + block2.end_time.minute

    # Handle midnight crossing
    if block1.end_time < block1.start_time:
        b1_end += 24 * 60
    if block2.end_time < block2.start_time:
        b2_end += 24 * 60

    return not (b1_end <= b2_start or b2_end <= b1_start)


def get_employee_working_blocks(
    start_time: time,
    end_time: time,
    block_size_minutes: int = 30
) -> List[TimeBlock]:
    """
    Generate time blocks for an employee's working hours.

    Args:
        start_time: Employee start time
        end_time: Employee end time
        block_size_minutes: Block size in minutes

    Returns:
        List of TimeBlock objects covering working hours
    """
    blocks = []
    current = datetime.combine(date.today(), start_time)
    end = datetime.combine(date.today(), end_time)

    # Handle midnight crossing
    if end_time < start_time:
        end = end + timedelta(days=1)

    while current < end:
        next_time = current + timedelta(minutes=block_size_minutes)
        blocks.append(TimeBlock(
            start_time=current.time(),
            end_time=next_time.time()
        ))
        current = next_time

    return blocks


def get_week_dates(monday: date) -> List[Tuple[date, str]]:
    """
    Get all dates for a week starting from Monday.

    Args:
        monday: Monday date (week start)

    Returns:
        List of (date, day_name) tuples
    """
    days = []
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for i in range(7):
        current_date = monday + timedelta(days=i)
        days.append((current_date, day_names[i]))

    return days


def is_weekend(target_date: date) -> bool:
    """Check if a date is Saturday or Sunday."""
    return target_date.weekday() in [5, 6]  # 5=Saturday, 6=Sunday


def get_month_start(target_date: date) -> date:
    """Get the first day of the month for a given date."""
    return target_date.replace(day=1)


def format_time_range(start: time, end: time) -> str:
    """Format a time range as a string."""
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


def get_month_dates(month_start: date) -> List[Tuple[date, str]]:
    """
    Get all dates for a calendar month starting from the first day.

    Args:
        month_start: First day of the month

    Returns:
        List of (date, day_name) tuples for entire month
    """
    days = []
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Calculate last day of month
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1, day=1)

    last_day = next_month - timedelta(days=1)
    total_days = last_day.day

    # Generate all dates in month
    for i in range(total_days):
        current_date = month_start + timedelta(days=i)
        day_name = day_names[current_date.weekday()]
        days.append((current_date, day_name))

    return days


def get_first_of_month(target_date: date) -> date:
    """Get the first day of the month for a given date."""
    return target_date.replace(day=1)


def get_last_of_month(target_date: date) -> date:
    """Get the last day of the month for a given date."""
    if target_date.month == 12:
        next_month = target_date.replace(year=target_date.year + 1, month=1, day=1)
    else:
        next_month = target_date.replace(month=target_date.month + 1, day=1)
    return next_month - timedelta(days=1)


def count_weekends_in_month(month_start: date) -> int:
    """
    Count the number of complete weekends (Sat+Sun) in a month.

    Args:
        month_start: First day of the month

    Returns:
        Number of weekends in the month
    """
    month_dates = get_month_dates(month_start)
    saturdays = sum(1 for _, day_name in month_dates if day_name == "Saturday")
    sundays = sum(1 for _, day_name in month_dates if day_name == "Sunday")

    # A weekend is counted if both Sat and Sun are present
    return min(saturdays, sundays)

"""Schedule visualization components."""

import streamlit as st
import pandas as pd
from datetime import date
from typing import List, Dict

from core.models import WeekSchedule, DaySchedule, ValidationResult
from core.constants import CATEGORIES
from core.utils import generate_time_blocks, is_weekend


def render_validation_results(validation: ValidationResult):
    """Display validation results with appropriate styling."""
    if validation.is_valid:
        st.success("✅ Schedule is valid!")
    else:
        st.error("❌ Schedule has validation errors!")

    # Uncovered blocks
    if validation.uncovered_blocks:
        st.subheader("⚠️ Uncovered Time Blocks")

        for category, blocks in validation.uncovered_blocks.items():
            st.markdown(f"**{category}** - {len(blocks)} uncovered blocks")
            for block_info in blocks[:10]:  # Show first 10
                st.text(f"  • {block_info}")
            if len(blocks) > 10:
                st.text(f"  ... and {len(blocks) - 10} more")
            st.markdown("---")

    # Rule violations
    if validation.rule_violations:
        st.subheader(f"❌ Rule Violations ({len(validation.rule_violations)})")

        for violation in validation.rule_violations:
            st.text(f"  • {violation}")

    # Double bookings
    if validation.double_bookings:
        st.subheader(f"⚠️ Double Bookings ({len(validation.double_bookings)})")

        for booking in validation.double_bookings:
            st.text(f"  • {booking}")

    # Warnings
    if validation.warnings:
        st.subheader(f"⚡ Warnings ({len(validation.warnings)})")

        for warning in validation.warnings:
            st.text(f"  • {warning}")


def render_daily_schedule(day_schedule: DaySchedule):
    """Render schedule for a single day as a table."""
    st.subheader(f"{day_schedule.day_of_week} - {day_schedule.date.strftime('%Y-%m-%d')}")

    # Generate time blocks
    time_blocks = generate_time_blocks(8, 24, 30)

    # Create data for table
    data = []

    for block in time_blocks:
        row = {"Time": str(block)}

        for category in CATEGORIES:
            # Find assignments
            assignments = [
                a for a in day_schedule.assignments
                if a.category == category and a.time_block == block
            ]

            if assignments:
                employees = []
                for a in assignments:
                    emp = a.employee_name
                    if a.is_overlap:
                        emp += " (overlap)"
                    employees.append(emp)
                row[category] = ", ".join(sorted(employees))
            else:
                row[category] = ""

        data.append(row)

    df = pd.DataFrame(data)

    # Style the dataframe
    st.dataframe(
        df,
        use_container_width=True,
        height=400,
        hide_index=True
    )

    # Coverage summary
    with st.expander("Coverage Summary"):
        coverage_data = []

        for category in CATEGORIES:
            covered, total = _calculate_coverage_counts(day_schedule, category)
            percentage = (covered / total * 100) if total > 0 else 0

            coverage_data.append({
                "Category": category,
                "Covered": covered,
                "Total": total,
                "Coverage %": f"{percentage:.1f}%"
            })

        coverage_df = pd.DataFrame(coverage_data)
        st.dataframe(coverage_df, hide_index=True)


def render_week_schedule(week_schedule: WeekSchedule):
    """Render full week schedule with tabs."""
    # Separate weekdays and weekends
    weekday_schedules = [
        day for day in week_schedule.days
        if not is_weekend(day.date)
    ]

    weekend_schedules = [
        day for day in week_schedule.days
        if is_weekend(day.date)
    ]

    # Create tabs
    tabs = st.tabs(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])

    for i, day_schedule in enumerate(week_schedule.days):
        with tabs[i]:
            render_daily_schedule(day_schedule)


def render_weekend_summary(weekend_summary: Dict[str, dict]):
    """Render weekend work summary table."""
    st.subheader("Weekend Work Summary")

    if not weekend_summary:
        st.info("No weekend data available.")
        return

    data = []

    for employee, summary in sorted(weekend_summary.items()):
        data.append({
            "Employee": employee,
            "Weekends Off": summary["weekends_off"],
            "Worked Saturday": summary["weekends_worked_saturday"],
            "Worked Sunday": summary["weekends_worked_sunday"],
            "Total Worked": summary["total_worked"],
            "Compliant": "✓" if summary["is_compliant"] else "✗"
        })

    df = pd.DataFrame(data)

    # Color code non-compliant rows
    def highlight_non_compliant(row):
        if row["Compliant"] == "✗":
            return ["background-color: #ffcccc"] * len(row)
        return [""] * len(row)

    styled_df = df.style.apply(highlight_non_compliant, axis=1)

    st.dataframe(styled_df, hide_index=True, use_container_width=True)


def render_employee_schedule_summary(week_schedule: WeekSchedule):
    """Render per-employee schedule summary."""
    st.subheader("Employee Schedule Summary")

    # Collect all employees
    all_employees = set()
    for day in week_schedule.days:
        for avail in day.availability:
            all_employees.add(avail.employee_name)

    # Create summary data
    data = []

    for employee in sorted(all_employees):
        row = {"Employee": employee}

        for day in week_schedule.days:
            day_name = day.day_of_week[:3]  # Mon, Tue, etc.

            # Get availability
            avail = next((a for a in day.availability if a.employee_name == employee), None)

            if avail:
                if avail.status == "Working":
                    # Count hours/assignments
                    assignments = day.get_assignments_by_employee(employee)
                    categories = set(a.category for a in assignments)
                    row[day_name] = ", ".join(sorted(categories)) if categories else "Available"
                else:
                    row[day_name] = avail.status

        data.append(row)

    df = pd.DataFrame(data)
    st.dataframe(df, hide_index=True, use_container_width=True)


def _calculate_coverage_counts(day_schedule: DaySchedule, category: str) -> tuple:
    """Calculate covered and total blocks for a category."""
    from core.constants import CATEGORY_COVERAGE

    if category not in CATEGORY_COVERAGE:
        return 0, 0

    coverage_start, coverage_end = CATEGORY_COVERAGE[category]

    # Generate required blocks
    required_blocks = generate_time_blocks(8, 24, 30)

    # Filter to coverage window
    relevant_blocks = [
        b for b in required_blocks
        if _time_in_range(b.start_time, coverage_start, coverage_end)
    ]

    if not relevant_blocks:
        return 0, 0

    # Count covered
    covered = 0
    for block in relevant_blocks:
        assignments = [
            a for a in day_schedule.assignments
            if a.category == category and a.time_block == block
        ]
        if assignments:
            covered += 1

    return covered, len(relevant_blocks)


def _time_in_range(check_time, start, end):
    """Check if time is in range, handling midnight crossing."""
    if end < start:
        return check_time >= start or check_time < end
    else:
        return start <= check_time < end

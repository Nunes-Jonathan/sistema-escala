"""Timeline visualization for employee schedules."""

import streamlit as st
import pandas as pd
from datetime import date, time
from typing import List, Dict

from core.models import DaySchedule, MonthSchedule, WorkStatus
from core.constants import CATEGORIES
from core.utils import generate_time_blocks


# Category color mapping
CATEGORY_COLORS = {
    "Salas": "#FF6B6B",           # Red
    "Helpdesk": "#4ECDC4",        # Teal
    "Tech": "#45B7D1",            # Blue
    "Supervisor/Marketing": "#FFA07A",  # Light Salmon
    "Marketing": "#98D8C8",       # Mint
    "HD Supervisor": "#F7DC6F",   # Yellow
}


def render_timeline_view(day_schedule: DaySchedule):
    """
    Render timeline view with employees as rows and time as columns.

    Args:
        day_schedule: Schedule for one day
    """
    st.subheader(f"Timeline: {day_schedule.day_of_week} - {day_schedule.date.strftime('%Y-%m-%d')}")

    # Generate time blocks
    time_blocks = generate_time_blocks(8, 24, 30)

    # Get all employees from availability
    employees = sorted([a.employee_name for a in day_schedule.availability])

    # Build HTML table
    html = '<table style="width:100%; border-collapse: collapse; font-size: 12px;">'

    # Header row
    html += '<tr><th style="border: 1px solid #ddd; padding: 8px; background-color: #366092; color: white;">Employee</th>'
    for block in time_blocks:
        html += f'<th style="border: 1px solid #ddd; padding: 4px; background-color: #366092; color: white; writing-mode: vertical-rl; transform: rotate(180deg); font-size: 10px;">{block.start_time.strftime("%H:%M")}</th>'
    html += '</tr>'

    # Data rows
    for employee in employees:
        html += f'<tr><td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{employee}</td>'

        # Get employee availability
        employee_avail = next(
            (a for a in day_schedule.availability if a.employee_name == employee),
            None
        )

        # If not working, show status across all cells
        if employee_avail and employee_avail.status != WorkStatus.WORKING:
            status = employee_avail.status.value if hasattr(employee_avail.status, 'value') else str(employee_avail.status)
            status_color = "#FFE6E6" if status == "Vacation" else "#E6E6E6"

            for block in time_blocks:
                html += f'<td style="border: 1px solid #ddd; padding: 4px; background-color: {status_color}; text-align: center; font-size: 9px;">{status[:3]}</td>'
            html += '</tr>'
            continue

        # For working employees, show assignments with colors
        employee_assignments = day_schedule.get_assignments_by_employee(employee)

        # Track previous category to show label only at start
        prev_category = None

        for i, block in enumerate(time_blocks):
            # Find assignment for this block
            assignment = next(
                (a for a in employee_assignments
                 if a.time_block.start_time == block.start_time and
                    a.time_block.end_time == block.end_time),
                None
            )

            if assignment:
                category = assignment.category
                color = CATEGORY_COLORS.get(category, "#CCCCCC")

                # Show category name only if it's different from previous or first block
                if category != prev_category:
                    label = category[:4]  # Abbreviated
                    prev_category = category
                else:
                    label = ""

                html += f'<td style="border: 1px solid #ddd; padding: 4px; background-color: {color}; text-align: center; font-size: 9px;">{label}</td>'
            else:
                html += '<td style="border: 1px solid #ddd; padding: 4px; background-color: #f9f9f9;"></td>'
                prev_category = None

        html += '</tr>'

    html += '</table>'

    # Display HTML table
    st.markdown(html, unsafe_allow_html=True)

    # Legend
    st.markdown("### Category Legend")
    cols = st.columns(len(CATEGORY_COLORS))
    for i, (category, color) in enumerate(CATEGORY_COLORS.items()):
        with cols[i]:
            st.markdown(
                f'<div style="background-color: {color}; padding: 8px; margin: 2px; '
                f'border-radius: 3px; text-align: center; color: #333; font-weight: bold;">{category}</div>',
                unsafe_allow_html=True
            )


def render_monthly_timeline(month_schedule: MonthSchedule, selected_date: date = None):
    """
    Render timeline view for a specific day in the month.

    Args:
        month_schedule: Complete month schedule
        selected_date: Optional date to display (defaults to first day)
    """
    if selected_date is None:
        selected_date = month_schedule.month_start

    # Get day schedule
    day_schedule = month_schedule.get_day_schedule(selected_date)

    if day_schedule:
        render_timeline_view(day_schedule)
    else:
        st.warning(f"No schedule found for {selected_date}")


def render_employee_bar_chart(month_schedule: MonthSchedule, employee_name: str):
    """
    Render a bar chart showing one employee's assignments across the month.

    Args:
        month_schedule: Complete month schedule
        employee_name: Employee to visualize
    """
    st.subheader(f"{employee_name} - Monthly Timeline")

    # Create data structure: date -> time_block -> category
    employee_data = []

    for day_schedule in month_schedule.days:
        # Get employee availability
        employee_avail = next(
            (a for a in day_schedule.availability if a.employee_name == employee_name),
            None
        )

        if not employee_avail:
            continue

        # Check status
        if employee_avail.status != WorkStatus.WORKING:
            status_str = employee_avail.status.value if hasattr(employee_avail.status, 'value') else str(employee_avail.status)
            employee_data.append({
                "Date": day_schedule.date.strftime("%m/%d"),
                "Day": day_schedule.day_of_week[:3],
                "Time": "All Day",
                "Category": status_str,
                "Status": status_str
            })
            continue

        # Get assignments
        assignments = day_schedule.get_assignments_by_employee(employee_name)

        for assignment in assignments:
            employee_data.append({
                "Date": day_schedule.date.strftime("%m/%d"),
                "Day": day_schedule.day_of_week[:3],
                "Time": str(assignment.time_block),
                "Category": assignment.category,
                "Status": "Working"
            })

    if employee_data:
        df = pd.DataFrame(employee_data)

        # Display summary
        st.write(f"**Total assignments:** {len(df[df['Status'] == 'Working'])}")

        # Group by category
        category_counts = df[df['Status'] == 'Working']['Category'].value_counts()
        if not category_counts.empty:
            st.write("**Assignments by category:**")
            for category, count in category_counts.items():
                st.write(f"  - {category}: {count} blocks")

        # Show detailed table
        with st.expander("📅 Detailed Schedule"):
            st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info(f"No data found for {employee_name}")


def render_coverage_heatmap(month_schedule: MonthSchedule):
    """
    Render a heatmap showing coverage across the month.

    Args:
        month_schedule: Complete month schedule
    """
    st.subheader("Coverage Heatmap")

    # Create heatmap data: category x date
    heatmap_data = {}

    for category in CATEGORIES:
        heatmap_data[category] = []

        for day_schedule in month_schedule.days:
            # Count covered blocks for this category
            category_assignments = day_schedule.get_assignments_by_category(category)
            coverage_count = len(category_assignments)
            heatmap_data[category].append(coverage_count)

    # Create DataFrame
    dates = [d.date.strftime("%m/%d") for d in month_schedule.days]
    df = pd.DataFrame(heatmap_data, index=dates)

    # Display
    st.dataframe(
        df.T,  # Transpose so categories are rows
        use_container_width=True
    )

    st.caption("Shows number of assigned time blocks per category per day")

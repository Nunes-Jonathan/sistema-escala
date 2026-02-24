"""Streamlit sidebar components."""

import streamlit as st
from datetime import date, timedelta, time
from typing import Dict, List, Tuple

from core.models import EmployeeAvailability, WorkStatus


def render_sidebar(employee_names: List[str]) -> Tuple[date, Dict[str, dict]]:
    """
    Render sidebar with week selection and configuration.

    Args:
        employee_names: List of employee names

    Returns:
        Tuple of (week_start_date, settings_dict)
    """
    st.sidebar.title("Schedule Configuration")

    # Week selection
    st.sidebar.subheader("Week Selection")

    # Find next Monday
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0 and today.weekday() != 0:
        days_until_monday = 7

    default_monday = today if today.weekday() == 0 else today + timedelta(days=days_until_monday)

    week_start = st.sidebar.date_input(
        "Week Start (Monday)",
        value=default_monday,
        help="Select a Monday to start the week"
    )

    # Validate it's a Monday
    if week_start.weekday() != 0:
        st.sidebar.error("Please select a Monday!")
        # Adjust to nearest Monday
        days_to_subtract = week_start.weekday()
        week_start = week_start - timedelta(days=days_to_subtract)
        st.sidebar.info(f"Adjusted to Monday: {week_start}")

    # Block size configuration
    st.sidebar.subheader("Time Block Settings")
    block_size = st.sidebar.selectbox(
        "Block Size (minutes)",
        options=[30, 60],
        index=0,
        help="Time block granularity"
    )

    # Scenario selection
    st.sidebar.subheader("Demo Scenarios")
    scenario = st.sidebar.selectbox(
        "Load Scenario",
        options=["Normal Week", "Ana Vacation (Tue-Thu)", "Multiple Absences"],
        index=0,
        help="Load a pre-configured scenario"
    )

    settings = {
        "block_size": block_size,
        "scenario": scenario
    }

    return week_start, settings


def render_absence_editor(
    week_start: date,
    employee_names: List[str]
) -> Dict[date, Dict[str, dict]]:
    """
    Render absence and override editor in sidebar.

    Args:
        week_start: Monday of the week
        employee_names: List of employee names

    Returns:
        Dict of date -> employee -> {status, start_time, end_time, notes}
    """
    st.sidebar.subheader("Absences & Overrides")

    absences = {}

    # Create expandable sections for each day
    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_name = current_date.strftime("%A")

        with st.sidebar.expander(f"{day_name} ({current_date.strftime('%m/%d')})"):
            day_absences = {}

            for employee in employee_names:
                col1, col2 = st.columns([2, 1])

                with col1:
                    status = st.selectbox(
                        f"{employee}",
                        options=["Working", "DayOff", "Vacation"],
                        key=f"status_{current_date}_{employee}",
                        label_visibility="visible"
                    )

                with col2:
                    override_hours = st.checkbox(
                        "Override",
                        key=f"override_{current_date}_{employee}",
                        help="Override default hours"
                    )

                start_time = None
                end_time = None
                notes = ""

                if status == "Working" and override_hours:
                    col_s, col_e = st.columns(2)
                    with col_s:
                        start_time = st.time_input(
                            "Start",
                            value=time(9, 0),
                            key=f"start_{current_date}_{employee}",
                            label_visibility="visible"
                        )
                    with col_e:
                        end_time = st.time_input(
                            "End",
                            value=time(17, 0),
                            key=f"end_{current_date}_{employee}",
                            label_visibility="visible"
                        )

                if status != "Working":
                    notes = st.text_input(
                        "Notes",
                        key=f"notes_{current_date}_{employee}",
                        placeholder="Optional notes..."
                    )

                day_absences[employee] = {
                    "status": status,
                    "start_time": start_time,
                    "end_time": end_time,
                    "notes": notes
                }

            absences[current_date] = day_absences

    return absences

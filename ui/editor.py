"""Editable table components for schedule modification."""

import streamlit as st
import pandas as pd
from datetime import date, time, timedelta
from typing import Dict, List

from core.models import EmployeeAvailability, WorkStatus
from core.constants import EMPLOYEE_DEFAULT_HOURS


def render_availability_editor(
    week_start: date,
    employee_names: List[str],
    current_availability: Dict[date, List[EmployeeAvailability]]
) -> Dict[date, List[EmployeeAvailability]]:
    """
    Render editable availability table.

    Args:
        week_start: Monday of the week
        employee_names: List of employees
        current_availability: Current availability data

    Returns:
        Updated availability dictionary
    """
    st.subheader("Edit Employee Availability")

    # Prepare data for editing
    data_rows = []

    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_name = current_date.strftime("%A")

        if current_date not in current_availability:
            continue

        for avail in current_availability[current_date]:
            # Get default hours
            default_start, default_end = EMPLOYEE_DEFAULT_HOURS.get(
                avail.employee_name,
                (time(9, 0), time(17, 0))
            )

            start_time = avail.start_time or default_start
            end_time = avail.end_time or default_end

            data_rows.append({
                "Date": current_date.strftime("%Y-%m-%d"),
                "Day": day_name,
                "Employee": avail.employee_name,
                "Status": avail.status,
                "StartTime": start_time.strftime("%H:%M"),
                "EndTime": end_time.strftime("%H:%M"),
                "Notes": avail.notes or ""
            })

    df = pd.DataFrame(data_rows)

    # Editable dataframe
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Date": st.column_config.TextColumn("Date", disabled=True),
            "Day": st.column_config.TextColumn("Day", disabled=True),
            "Employee": st.column_config.TextColumn("Employee", disabled=True),
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=["Working", "DayOff", "Vacation"],
                required=True
            ),
            "StartTime": st.column_config.TextColumn("Start Time"),
            "EndTime": st.column_config.TextColumn("End Time"),
            "Notes": st.column_config.TextColumn("Notes")
        },
        hide_index=True,
        key="availability_editor"
    )

    # Convert back to availability objects
    updated_availability = {}

    for _, row in edited_df.iterrows():
        row_date = pd.to_datetime(row["Date"]).date()

        if row_date not in updated_availability:
            updated_availability[row_date] = []

        # Parse times
        try:
            start_time = pd.to_datetime(row["StartTime"], format="%H:%M").time()
            end_time = pd.to_datetime(row["EndTime"], format="%H:%M").time()
        except:
            # Use defaults if parsing fails
            default_start, default_end = EMPLOYEE_DEFAULT_HOURS.get(
                row["Employee"],
                (time(9, 0), time(17, 0))
            )
            start_time = default_start
            end_time = default_end

        avail = EmployeeAvailability(
            employee_name=row["Employee"],
            date=row_date,
            status=row["Status"],
            start_time=start_time if row["Status"] == "Working" else None,
            end_time=end_time if row["Status"] == "Working" else None,
            notes=row["Notes"] or ""
        )

        updated_availability[row_date].append(avail)

    return updated_availability


def render_quick_absence_form(
    week_start: date,
    employee_names: List[str]
) -> Dict[str, any]:
    """
    Render quick form for marking absences.

    Returns:
        Dict with absence information or None
    """
    st.subheader("Quick Absence Entry")

    with st.form("quick_absence"):
        col1, col2, col3 = st.columns(3)

        with col1:
            employee = st.selectbox("Employee", options=employee_names)

        with col2:
            absence_type = st.selectbox("Type", options=["DayOff", "Vacation"])

        with col3:
            # Date range
            start_date = st.date_input(
                "Start Date",
                value=week_start,
                min_value=week_start,
                max_value=week_start + timedelta(days=6)
            )

        end_date = st.date_input(
            "End Date",
            value=start_date,
            min_value=start_date,
            max_value=week_start + timedelta(days=6)
        )

        notes = st.text_input("Notes", placeholder="Optional notes...")

        submitted = st.form_submit_button("Add Absence")

        if submitted:
            return {
                "employee": employee,
                "type": absence_type,
                "start_date": start_date,
                "end_date": end_date,
                "notes": notes
            }

    return None

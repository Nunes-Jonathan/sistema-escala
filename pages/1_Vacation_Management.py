"""Vacation Management Page for Sistema de Escala."""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
import json
from pathlib import Path

from core.models import VacationPeriod
from tests.demo_scenarios import create_employees
from core.constants import WEEKEND_NEVER_WORK

# Page configuration
st.set_page_config(
    page_title="Vacation Management - Sistema de Escala",
    page_icon="🏖️",
    layout="wide"
)

# Initialize session state
if "vacation_periods" not in st.session_state:
    st.session_state.vacation_periods = []

# Always initialize employee names
employees = create_employees()
st.session_state.employee_names = [emp.name for emp in employees]


def save_vacations_to_file():
    """Save vacation periods to JSON file."""
    data = [
        {
            "employee_name": vp.employee_name,
            "start_date": vp.start_date.isoformat(),
            "end_date": vp.end_date.isoformat(),
            "notes": vp.notes
        }
        for vp in st.session_state.vacation_periods
    ]

    save_path = Path("vacation_data.json")
    with open(save_path, "w") as f:
        json.dump(data, f, indent=2)

    return save_path


def load_vacations_from_file():
    """Load vacation periods from JSON file."""
    load_path = Path("vacation_data.json")

    if not load_path.exists():
        return []

    with open(load_path, "r") as f:
        data = json.load(f)

    vacation_periods = []
    for item in data:
        vp = VacationPeriod(
            employee_name=item["employee_name"],
            start_date=date.fromisoformat(item["start_date"]),
            end_date=date.fromisoformat(item["end_date"]),
            notes=item.get("notes", "")
        )
        vacation_periods.append(vp)

    return vacation_periods


def get_weekend_days_in_vacation(vp: VacationPeriod) -> list:
    """Return all Sat/Sun dates that fall within a vacation period."""
    days = []
    current = vp.start_date
    while current <= vp.end_date:
        if current.weekday() in (5, 6):
            days.append(current)
        current += timedelta(days=1)
    return days


def analyze_weekend_impact(vacation: VacationPeriod, all_vacations: list) -> dict:
    """
    Check how a vacation affects weekend coverage.

    Returns a dict with:
      - weekend_days: list of Sat/Sun inside the vacation
      - works_weekends: whether this employee is part of the weekend crew
      - conflicting: dict mapping each weekend day to list of other absent weekend-crew employees
    """
    weekend_days = get_weekend_days_in_vacation(vacation)
    works_weekends = vacation.employee_name not in WEEKEND_NEVER_WORK

    conflicting = {}
    if works_weekends:
        for day in weekend_days:
            others = [
                v.employee_name
                for v in all_vacations
                if v.employee_name != vacation.employee_name
                and v.employee_name not in WEEKEND_NEVER_WORK
                and v.contains_date(day)
            ]
            conflicting[day] = others

    return {
        "weekend_days": weekend_days,
        "works_weekends": works_weekends,
        "conflicting": conflicting,
    }


# Main content
st.title("🏖️ Vacation Management")
st.markdown("Manage employee vacation periods for schedule generation")

st.markdown("---")

# Add new vacation period
st.subheader("➕ Add Vacation Period")

with st.form("add_vacation"):
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        employee = st.selectbox(
            "Employee",
            options=st.session_state.employee_names,
            key="new_vacation_employee"
        )

    with col2:
        start_date = st.date_input(
            "Start Date",
            value=date.today(),
            key="new_vacation_start"
        )

    with col3:
        end_date = st.date_input(
            "End Date",
            value=max(start_date, date.today()) + timedelta(days=7),
            min_value=start_date,
            key="new_vacation_end"
        )

    notes = st.text_input(
        "Notes (optional)",
        placeholder="e.g., Family vacation, Medical leave, etc.",
        key="new_vacation_notes"
    )

    # Submit button (must be inside form)
    submitted = st.form_submit_button("Add Vacation", type="primary", use_container_width=False)

    if submitted:
        # Validate dates
        if end_date < start_date:
            st.error("End date must be after or equal to start date!")
        else:
            # Create vacation period
            new_vacation = VacationPeriod(
                employee_name=employee,
                start_date=start_date,
                end_date=end_date,
                notes=notes
            )

            st.session_state.vacation_periods.append(new_vacation)
            st.success(f"✅ Added vacation for {employee} ({start_date} to {end_date})")
            st.rerun()

st.markdown("---")

# Display existing vacations
st.subheader("📋 Current Vacation Periods")

if st.session_state.vacation_periods:
    # Create table data
    vacation_data = []

    for i, vp in enumerate(st.session_state.vacation_periods):
        duration = (vp.end_date - vp.start_date).days + 1

        vacation_data.append({
            "ID": i,
            "Employee": vp.employee_name,
            "Start Date": vp.start_date.strftime("%Y-%m-%d"),
            "End Date": vp.end_date.strftime("%Y-%m-%d"),
            "Duration (days)": duration,
            "Notes": vp.notes or "-"
        })

    df = pd.DataFrame(vacation_data)

    # Display table
    st.dataframe(
        df.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True
    )

    # Delete vacation section
    st.subheader("🗑️ Remove Vacation")

    col1, col2 = st.columns([2, 4])

    with col1:
        vacation_to_delete = st.selectbox(
            "Select vacation to remove",
            options=range(len(st.session_state.vacation_periods)),
            format_func=lambda i: f"{st.session_state.vacation_periods[i].employee_name} ({st.session_state.vacation_periods[i].start_date} to {st.session_state.vacation_periods[i].end_date})"
        )

    with col2:
        if st.button("🗑️ Remove Selected Vacation", type="secondary"):
            removed = st.session_state.vacation_periods.pop(vacation_to_delete)
            st.success(f"Removed vacation for {removed.employee_name}")
            st.rerun()

else:
    st.info("No vacation periods added yet. Use the form above to add vacations.")

st.markdown("---")

# Weekend Impact Analysis
st.subheader("📅 Weekend Impact Analysis")

if st.session_state.vacation_periods:
    # Total weekend-crew size (employees who work weekends)
    all_employees = create_employees()
    weekend_crew = [e.name for e in all_employees if e.name not in WEEKEND_NEVER_WORK]
    weekend_crew_size = len(weekend_crew)

    for vp in st.session_state.vacation_periods:
        impact = analyze_weekend_impact(vp, st.session_state.vacation_periods)

        with st.expander(
            f"{vp.employee_name}  |  {vp.start_date} → {vp.end_date}",
            expanded=True,
        ):
            if not impact["weekend_days"]:
                st.success("No weekend days in this vacation — no weekend coverage impact.")
            elif not impact["works_weekends"]:
                st.success(
                    f"{vp.employee_name} does not work weekends, so this vacation "
                    "has no effect on weekend coverage."
                )
            else:
                for day in impact["weekend_days"]:
                    day_name = day.strftime("%A %d/%m/%Y")
                    others_off = impact["conflicting"][day]
                    # available = crew minus this employee minus anyone else on vacation
                    available = weekend_crew_size - 1 - len(others_off)

                    if others_off:
                        st.warning(
                            f"**{day_name}** — {available}/{weekend_crew_size} weekend crew "
                            f"available. Also absent: {', '.join(others_off)}."
                        )
                    else:
                        st.info(
                            f"**{day_name}** — {available}/{weekend_crew_size} weekend crew "
                            "available. No other conflicts."
                        )
else:
    st.info("Add vacation periods above to see weekend impact.")

st.markdown("---")

# Save/Load section
st.subheader("💾 Save/Load Vacation Data")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💾 Save to File", use_container_width=True):
        if st.session_state.vacation_periods:
            save_path = save_vacations_to_file()
            st.success(f"Saved {len(st.session_state.vacation_periods)} vacation periods to {save_path}")
        else:
            st.warning("No vacation periods to save")

with col2:
    if st.button("📂 Load from File", use_container_width=True):
        loaded_vacations = load_vacations_from_file()
        if loaded_vacations:
            st.session_state.vacation_periods = loaded_vacations
            st.success(f"Loaded {len(loaded_vacations)} vacation periods")
            st.rerun()
        else:
            st.info("No vacation data file found")

with col3:
    if st.button("🗑️ Clear All", use_container_width=True):
        if st.session_state.vacation_periods:
            count = len(st.session_state.vacation_periods)
            st.session_state.vacation_periods = []
            st.success(f"Cleared {count} vacation periods")
            st.rerun()
        else:
            st.info("No vacations to clear")

# Summary statistics
if st.session_state.vacation_periods:
    st.markdown("---")
    st.subheader("📊 Summary Statistics")

    # Count by employee
    employee_counts = {}
    total_days = {}

    for vp in st.session_state.vacation_periods:
        employee_counts[vp.employee_name] = employee_counts.get(vp.employee_name, 0) + 1
        duration = (vp.end_date - vp.start_date).days + 1
        total_days[vp.employee_name] = total_days.get(vp.employee_name, 0) + duration

    summary_data = [
        {
            "Employee": emp,
            "Vacation Periods": count,
            "Total Days": total_days[emp]
        }
        for emp, count in employee_counts.items()
    ]

    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, hide_index=True, use_container_width=True)

# Instructions
with st.expander("ℹ️ How to Use"):
    st.markdown("""
    ### Adding Vacations

    1. Select an employee from the dropdown
    2. Choose start and end dates
    3. Optionally add notes
    4. Click "Add Vacation"

    ### Managing Vacations

    - View all current vacation periods in the table
    - Remove individual vacations using the removal section
    - Clear all vacations at once

    ### Saving/Loading

    - **Save to File**: Saves current vacation periods to `vacation_data.json`
    - **Load from File**: Loads vacation periods from `vacation_data.json`
    - **Clear All**: Removes all vacation periods from memory

    ### Using Vacations in Schedules

    - Vacation periods are automatically applied when generating monthly schedules
    - Employees on vacation will be marked as "Vacation" status
    - The system will adjust other employees' hours to cover gaps

    **Note**: Vacation data is saved in the current directory as `vacation_data.json`
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Sistema de Escala v2.0 | Vacation Management"
    "</div>",
    unsafe_allow_html=True
)

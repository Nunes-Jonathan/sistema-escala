"""
Sistema de Escala v2.0 - Monthly Work Schedule Management System

A desktop-app feel scheduling tool built with Python + Streamlit.
Generates monthly work-hours sheets per category, supports editing,
validation, and Excel/CSV export.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
import tempfile
import json

# Core imports
from core.models import Employee, Category, EmployeeAvailability, WorkStatus, MonthSchedule, VacationPeriod
from core.constants import EMPLOYEE_DEFAULT_HOURS
from core.utils import get_first_of_month

# Engine imports
from engine.scheduler import Scheduler

# Export imports
from export.excel_exporter import ExcelExporter
from export.csv_exporter import CSVExporter

# UI imports
from ui.schedule_view import render_validation_results, render_weekend_summary, render_employee_schedule_summary
from ui.timeline_view import render_monthly_timeline, render_employee_bar_chart, render_coverage_heatmap

# Test scenarios
from tests.demo_scenarios import create_employees, create_categories


# Page configuration
st.set_page_config(
    page_title="Sistema de Escala",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "scheduler" not in st.session_state:
        employees = create_employees()
        categories = create_categories()
        st.session_state.scheduler = Scheduler(employees, categories)
        st.session_state.employees = employees
        st.session_state.categories = categories

    if "month_schedule" not in st.session_state:
        st.session_state.month_schedule = None

    if "validation_result" not in st.session_state:
        st.session_state.validation_result = None

    if "vacation_periods" not in st.session_state:
        # Try to restore from file on first load; fall back to empty list
        st.session_state.vacation_periods = load_vacations()


def load_vacations():
    """Load vacation periods from file if exists."""
    vacation_file = Path("vacation_data.json")
    if vacation_file.exists():
        try:
            with open(vacation_file, "r") as f:
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
        except Exception as e:
            st.sidebar.warning(f"Could not load vacation data: {e}")
            return []
    return []


def main():
    """Main application entry point."""
    initialize_session_state()

    # Title
    st.title("📅 Sistema de Escala v2.0")
    st.markdown("**Monthly Work Schedule Management System**")
    st.markdown("---")

    # Sidebar - Month selection
    st.sidebar.title("Schedule Configuration")
    st.sidebar.subheader("Month Selection")

    # Get current month
    today = date.today()
    default_month_start = get_first_of_month(today)

    month_date = st.sidebar.date_input(
        "Select Month",
        value=default_month_start,
        help="Select any date in the month to schedule"
    )

    # Convert to first of month
    month_start = get_first_of_month(month_date)

    st.sidebar.info(f"📅 Scheduling for: **{month_start.strftime('%B %Y')}**")

    # Load vacations
    st.sidebar.subheader("Vacation Periods")
    vacation_count = len(st.session_state.vacation_periods)

    if st.sidebar.button("🔄 Reload Vacations from File"):
        st.session_state.vacation_periods = load_vacations()
        st.sidebar.success(f"Loaded {len(st.session_state.vacation_periods)} vacation periods")

    st.sidebar.info(f"**{vacation_count}** vacation periods loaded")
    st.sidebar.caption("Manage vacations in the Vacation Management page →")

    # Main content area
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔄 Generate Schedule", type="primary", use_container_width=True):
            with st.spinner("Generating monthly schedule..."):
                # Use vacation periods already in session state (set via Vacation Management page).
                # Do NOT reload from file here — that would discard unsaved in-memory vacations.
                vacation_periods = st.session_state.vacation_periods

                # Generate schedule
                month_schedule = st.session_state.scheduler.generate_month_schedule(
                    month_start,
                    vacation_periods=vacation_periods
                )
                st.session_state.month_schedule = month_schedule

                st.success(f"✅ Schedule generated for {month_start.strftime('%B %Y')}!")
                st.rerun()

    with col2:
        if st.button("✅ Validate Schedule", use_container_width=True):
            if st.session_state.month_schedule:
                with st.spinner("Validating..."):
                    validation = st.session_state.scheduler.validate_month_schedule(
                        st.session_state.month_schedule
                    )
                    st.session_state.validation_result = validation
                    st.rerun()
            else:
                st.warning("Generate a schedule first!")

    with col3:
        if st.button("📊 Export Excel", use_container_width=True):
            if st.session_state.month_schedule:
                with st.spinner("Generating Excel..."):
                    temp_dir = tempfile.mkdtemp()
                    output_path = Path(temp_dir) / f"schedule_{month_start.strftime('%Y%m')}.xlsx"

                    exporter = ExcelExporter(st.session_state.scheduler.weekend_tracker)
                    # Convert MonthSchedule to WeekSchedule for export (temporary compatibility)
                    from core.models import WeekSchedule
                    temp_week = WeekSchedule(week_start=month_start, days=st.session_state.month_schedule.days[:7])
                    exporter.export_schedule(temp_week, str(output_path))

                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Excel",
                            data=f,
                            file_name=f"schedule_{month_start.strftime('%Y%m')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                    st.success("Excel file ready!")
            else:
                st.warning("Generate a schedule first!")

    with col4:
        if st.button("📄 Export CSV", use_container_width=True):
            if st.session_state.month_schedule:
                with st.spinner("Generating CSV..."):
                    temp_dir = tempfile.mkdtemp()

                    exporter = CSVExporter(st.session_state.scheduler.weekend_tracker)
                    # Convert MonthSchedule to WeekSchedule for export (temporary compatibility)
                    from core.models import WeekSchedule
                    temp_week = WeekSchedule(week_start=month_start, days=st.session_state.month_schedule.days[:7])
                    zip_path = exporter.export_schedule(temp_week, temp_dir)

                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download CSV (Zip)",
                            data=f,
                            file_name=f"schedule_{month_start.strftime('%Y%m')}.zip",
                            mime="application/zip",
                            use_container_width=True
                        )

                    st.success("CSV files ready!")
            else:
                st.warning("Generate a schedule first!")

    st.markdown("---")

    # Display validation results if available
    if st.session_state.validation_result:
        with st.expander("🔍 Validation Results", expanded=False):
            render_validation_results(st.session_state.validation_result)

    # Display schedule if available
    if st.session_state.month_schedule:
        st.markdown(f"## 📋 Monthly Schedule - {month_start.strftime('%B %Y')}")

        # Tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📅 Timeline View",
            "👥 Employee Schedules",
            "📊 Coverage Heatmap",
            "🏖️ Weekend Summary",
            "ℹ️ Schedule Info"
        ])

        with tab1:
            st.subheader("Timeline View")
            st.caption("Select a date to view the timeline for that day")

            # Date selector
            month_dates = [d.date for d in st.session_state.month_schedule.days]
            selected_date = st.selectbox(
                "Select Date",
                options=month_dates,
                format_func=lambda d: d.strftime("%A, %B %d, %Y")
            )

            if selected_date:
                render_monthly_timeline(st.session_state.month_schedule, selected_date)

        with tab2:
            st.subheader("Employee Schedules")

            employee_names = [emp.name for emp in st.session_state.employees]
            selected_employee = st.selectbox(
                "Select Employee",
                options=employee_names
            )

            if selected_employee:
                render_employee_bar_chart(st.session_state.month_schedule, selected_employee)

        with tab3:
            render_coverage_heatmap(st.session_state.month_schedule)

        with tab4:
            weekend_summary = st.session_state.scheduler.get_weekend_summary(month_start)
            render_weekend_summary(weekend_summary)

        with tab5:
            st.subheader("Schedule Information")

            col1, col2, col3 = st.columns(3)

            with col1:
                total_days = len(st.session_state.month_schedule.days)
                st.metric("Total Days", total_days)

            with col2:
                total_assignments = sum(len(day.assignments) for day in st.session_state.month_schedule.days)
                st.metric("Total Assignments", total_assignments)

            with col3:
                vacation_count = len(st.session_state.vacation_periods)
                st.metric("Vacation Periods", vacation_count)

            # Day-by-day summary
            st.markdown("### Day-by-Day Summary")

            summary_data = []
            for day in st.session_state.month_schedule.days:
                working_count = sum(
                    1 for a in day.availability
                    if a.status == WorkStatus.WORKING
                )

                summary_data.append({
                    "Date": day.date.strftime("%Y-%m-%d"),
                    "Day": day.day_of_week,
                    "Working Employees": working_count,
                    "Total Assignments": len(day.assignments)
                })

            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, hide_index=True, use_container_width=True, height=400)

    else:
        # Instructions
        st.info("👈 Select a month and click 'Generate Schedule' to begin.")

        with st.expander("ℹ️ How to Use"):
            st.markdown("""
            ### Getting Started

            1. **Select Month**: Choose any date in the month you want to schedule
            2. **Manage Vacations**: Go to Vacation Management page to add employee vacations
            3. **Generate**: Click "Generate Schedule" to create the monthly schedule
            4. **Review**: Use the Timeline View to see daily schedules
            5. **Validate**: Check for coverage gaps and rule violations
            6. **Export**: Download as Excel (.xlsx) or CSV files

            ### New Features in v2.0

            - **Monthly Scheduling**: Full calendar month scheduling (28-31 days)
            - **Auto Hour Adjustment**: System automatically adjusts flexible employee hours to ensure coverage
            - **HD Supervisor**: Anderson assigned to HD Supervisor role when not covering for others
            - **Timeline View**: Visual bar-chart style view of employee schedules
            - **Vacation Management**: Dedicated page for managing employee vacations
            - **Coverage Enforcement**: All required coverage windows are guaranteed to be filled

            ### Priority Rules

            When coverage is needed, the system adjusts hours in this order:
            1. **Anderson** - First priority (morning coverage)
            2. **Gabriel** - Second priority (afternoon/night)
            3. **Pedro** - Third priority (afternoon/night)
            4. **Other flexible employees** - As needed

            **Note**: Fixed employees (Cesar, Roberto, Oscar, Amanda) never change hours.
            """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Sistema de Escala v2.0 | Built with Streamlit + Python | Monthly Scheduling Engine"
    "</div>",
    unsafe_allow_html=True
)


if __name__ == "__main__":
    main()

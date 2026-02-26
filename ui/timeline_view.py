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
    "Salas": "#FF6B6B",
    "Helpdesk": "#4ECDC4",
    "Tech": "#45B7D1",
    "Supervisor/Marketing": "#FFA07A",
    "Marketing": "#98D8C8",
    "HD Supervisor": "#F7DC6F",
}

STATUS_PT = {
    "Vacation": "Férias",
    "DayOff": "Folga",
    "Working": "Trabalhando",
}


def render_timeline_view(day_schedule: DaySchedule):
    """
    Render timeline view with employees as rows and time as columns.
    """
    st.subheader(f"Linha do Tempo: {day_schedule.day_of_week} - {day_schedule.date.strftime('%d/%m/%Y')}")

    time_blocks = generate_time_blocks(8, 24, 30)

    employees = sorted([a.employee_name for a in day_schedule.availability])

    html = '<table style="width:100%; border-collapse: collapse; font-size: 12px;">'

    # Header row
    html += '<tr><th style="border: 1px solid #ddd; padding: 8px; background-color: #366092; color: white;">Funcionário</th>'
    for block in time_blocks:
        html += f'<th style="border: 1px solid #ddd; padding: 4px; background-color: #366092; color: white; writing-mode: vertical-rl; transform: rotate(180deg); font-size: 10px;">{block.start_time.strftime("%H:%M")}</th>'
    html += '</tr>'

    # Data rows
    for employee in employees:
        html += f'<tr><td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{employee}</td>'

        employee_avail = next(
            (a for a in day_schedule.availability if a.employee_name == employee),
            None
        )

        if employee_avail and employee_avail.status != WorkStatus.WORKING:
            status_raw = employee_avail.status.value if hasattr(employee_avail.status, 'value') else str(employee_avail.status)
            status_label = STATUS_PT.get(status_raw, status_raw)
            status_color = "#FFE6E6" if status_raw == "Vacation" else "#E6E6E6"

            for block in time_blocks:
                html += f'<td style="border: 1px solid #ddd; padding: 4px; background-color: {status_color}; text-align: center; font-size: 9px;">{status_label[:3]}</td>'
            html += '</tr>'
            continue

        employee_assignments = day_schedule.get_assignments_by_employee(employee)

        prev_category = None

        for i, block in enumerate(time_blocks):
            assignment = next(
                (a for a in employee_assignments
                 if a.time_block.start_time == block.start_time and
                    a.time_block.end_time == block.end_time),
                None
            )

            if assignment:
                category = assignment.category
                color = CATEGORY_COLORS.get(category, "#CCCCCC")

                if category != prev_category:
                    label = category[:4]
                    prev_category = category
                else:
                    label = ""

                html += f'<td style="border: 1px solid #ddd; padding: 4px; background-color: {color}; text-align: center; font-size: 9px;">{label}</td>'
            else:
                html += '<td style="border: 1px solid #ddd; padding: 4px; background-color: #f9f9f9;"></td>'
                prev_category = None

        html += '</tr>'

    html += '</table>'

    st.markdown(html, unsafe_allow_html=True)

    # Legend
    st.markdown("### Legenda de Categorias")
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
    """
    if selected_date is None:
        selected_date = month_schedule.month_start

    day_schedule = month_schedule.get_day_schedule(selected_date)

    if day_schedule:
        render_timeline_view(day_schedule)
    else:
        st.warning(f"Nenhuma escala encontrada para {selected_date.strftime('%d/%m/%Y')}")


def render_employee_bar_chart(month_schedule: MonthSchedule, employee_name: str):
    """
    Render a bar chart showing one employee's assignments across the month.
    """
    st.subheader(f"{employee_name} - Linha do Tempo Mensal")

    employee_data = []

    for day_schedule in month_schedule.days:
        employee_avail = next(
            (a for a in day_schedule.availability if a.employee_name == employee_name),
            None
        )

        if not employee_avail:
            continue

        if employee_avail.status != WorkStatus.WORKING:
            status_raw = employee_avail.status.value if hasattr(employee_avail.status, 'value') else str(employee_avail.status)
            status_label = STATUS_PT.get(status_raw, status_raw)
            employee_data.append({
                "Data": day_schedule.date.strftime("%d/%m"),
                "Dia": day_schedule.day_of_week[:3],
                "Horário": "Dia Todo",
                "Categoria": status_label,
                "Status": status_label
            })
            continue

        assignments = day_schedule.get_assignments_by_employee(employee_name)

        for assignment in assignments:
            employee_data.append({
                "Data": day_schedule.date.strftime("%d/%m"),
                "Dia": day_schedule.day_of_week[:3],
                "Horário": str(assignment.time_block),
                "Categoria": assignment.category,
                "Status": "Trabalhando"
            })

    if employee_data:
        df = pd.DataFrame(employee_data)

        st.write(f"**Total de atribuições:** {len(df[df['Status'] == 'Trabalhando'])}")

        category_counts = df[df['Status'] == 'Trabalhando']['Categoria'].value_counts()
        if not category_counts.empty:
            st.write("**Atribuições por categoria:**")
            for category, count in category_counts.items():
                st.write(f"  - {category}: {count} blocos")

        with st.expander("📅 Escala Detalhada"):
            st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info(f"Nenhum dado encontrado para {employee_name}")


def render_coverage_heatmap(month_schedule: MonthSchedule):
    """
    Render a heatmap showing coverage across the month.
    """
    st.subheader("Mapa de Cobertura")

    heatmap_data = {}

    for category in CATEGORIES:
        heatmap_data[category] = []

        for day_schedule in month_schedule.days:
            category_assignments = day_schedule.get_assignments_by_category(category)
            coverage_count = len(category_assignments)
            heatmap_data[category].append(coverage_count)

    dates = [d.date.strftime("%d/%m") for d in month_schedule.days]
    df = pd.DataFrame(heatmap_data, index=dates)

    st.dataframe(
        df.T,
        use_container_width=True
    )

    st.caption("Número de blocos de tempo atribuídos por categoria por dia")

"""Schedule visualization components."""

import streamlit as st
import pandas as pd
from datetime import date
from typing import List, Dict

from core.models import WeekSchedule, DaySchedule, ValidationResult
from core.constants import CATEGORIES
from core.utils import generate_time_blocks, is_weekend

STATUS_PT = {
    "Working": "Trabalhando",
    "DayOff": "Folga",
    "Vacation": "Férias",
}


def render_validation_results(validation: ValidationResult):
    """Display validation results with appropriate styling."""
    if validation.is_valid:
        st.success("✅ Escala válida!")
    else:
        st.error("❌ A escala possui erros de validação!")

    if validation.uncovered_blocks:
        st.subheader("⚠️ Blocos de Tempo Não Cobertos")

        for category, blocks in validation.uncovered_blocks.items():
            st.markdown(f"**{category}** - {len(blocks)} blocos não cobertos")
            for block_info in blocks[:10]:
                st.text(f"  • {block_info}")
            if len(blocks) > 10:
                st.text(f"  ... e mais {len(blocks) - 10}")
            st.markdown("---")

    if validation.rule_violations:
        st.subheader(f"❌ Violações de Regras ({len(validation.rule_violations)})")

        for violation in validation.rule_violations:
            st.text(f"  • {violation}")

    if validation.double_bookings:
        st.subheader(f"⚠️ Conflitos de Horário ({len(validation.double_bookings)})")

        for booking in validation.double_bookings:
            st.text(f"  • {booking}")

    if validation.warnings:
        st.subheader(f"⚡ Avisos ({len(validation.warnings)})")

        for warning in validation.warnings:
            st.text(f"  • {warning}")


def render_daily_schedule(day_schedule: DaySchedule):
    """Render schedule for a single day as a table."""
    st.subheader(f"{day_schedule.day_of_week} - {day_schedule.date.strftime('%d/%m/%Y')}")

    time_blocks = generate_time_blocks(8, 24, 30)

    data = []

    for block in time_blocks:
        row = {"Horário": str(block)}

        for category in CATEGORIES:
            assignments = [
                a for a in day_schedule.assignments
                if a.category == category and a.time_block == block
            ]

            if assignments:
                employees = []
                for a in assignments:
                    emp = a.employee_name
                    if a.is_overlap:
                        emp += " (sobreposição)"
                    employees.append(emp)
                row[category] = ", ".join(sorted(employees))
            else:
                row[category] = ""

        data.append(row)

    df = pd.DataFrame(data)

    st.dataframe(
        df,
        use_container_width=True,
        height=400,
        hide_index=True
    )

    with st.expander("Resumo de Cobertura"):
        coverage_data = []

        for category in CATEGORIES:
            covered, total = _calculate_coverage_counts(day_schedule, category)
            percentage = (covered / total * 100) if total > 0 else 0

            coverage_data.append({
                "Categoria": category,
                "Coberto": covered,
                "Total": total,
                "Cobertura %": f"{percentage:.1f}%"
            })

        coverage_df = pd.DataFrame(coverage_data)
        st.dataframe(coverage_df, hide_index=True)


def render_week_schedule(week_schedule: WeekSchedule):
    """Render full week schedule with tabs."""
    tabs = st.tabs([
        "Segunda-feira", "Terça-feira", "Quarta-feira",
        "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"
    ])

    for i, day_schedule in enumerate(week_schedule.days):
        with tabs[i]:
            render_daily_schedule(day_schedule)


def render_weekend_summary(weekend_summary: Dict[str, dict]):
    """Render weekend work summary table."""
    st.subheader("Resumo de Trabalho nos Fins de Semana")

    if not weekend_summary:
        st.info("Nenhum dado de fim de semana disponível.")
        return

    data = []

    for employee, summary in sorted(weekend_summary.items()):
        data.append({
            "Funcionário": employee,
            "Fins de Semana de Folga": summary["weekends_off"],
            "Trabalhou Sábado": summary["weekends_worked_saturday"],
            "Trabalhou Domingo": summary["weekends_worked_sunday"],
            "Total Trabalhado": summary["total_worked"],
            "Conforme": "✓" if summary["is_compliant"] else "✗"
        })

    df = pd.DataFrame(data)

    def highlight_non_compliant(row):
        if row["Conforme"] == "✗":
            return ["background-color: #ffcccc"] * len(row)
        return [""] * len(row)

    styled_df = df.style.apply(highlight_non_compliant, axis=1)

    st.dataframe(styled_df, hide_index=True, use_container_width=True)


def render_employee_schedule_summary(week_schedule: WeekSchedule):
    """Render per-employee schedule summary."""
    st.subheader("Resumo de Escala dos Funcionários")

    all_employees = set()
    for day in week_schedule.days:
        for avail in day.availability:
            all_employees.add(avail.employee_name)

    data = []

    for employee in sorted(all_employees):
        row = {"Funcionário": employee}

        for day in week_schedule.days:
            day_name = day.day_of_week[:3]

            avail = next((a for a in day.availability if a.employee_name == employee), None)

            if avail:
                if avail.status == "Working":
                    assignments = day.get_assignments_by_employee(employee)
                    categories = set(a.category for a in assignments)
                    row[day_name] = ", ".join(sorted(categories)) if categories else "Disponível"
                else:
                    row[day_name] = STATUS_PT.get(avail.status, avail.status)

        data.append(row)

    df = pd.DataFrame(data)
    st.dataframe(df, hide_index=True, use_container_width=True)


def _calculate_coverage_counts(day_schedule: DaySchedule, category: str) -> tuple:
    """Calculate covered and total blocks for a category."""
    from core.constants import CATEGORY_COVERAGE

    if category not in CATEGORY_COVERAGE:
        return 0, 0

    coverage_start, coverage_end = CATEGORY_COVERAGE[category]

    required_blocks = generate_time_blocks(8, 24, 30)

    relevant_blocks = [
        b for b in required_blocks
        if _time_in_range(b.start_time, coverage_start, coverage_end)
    ]

    if not relevant_blocks:
        return 0, 0

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

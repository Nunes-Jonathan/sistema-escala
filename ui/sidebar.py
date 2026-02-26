"""Streamlit sidebar components."""

import streamlit as st
from datetime import date, timedelta, time
from typing import Dict, List, Tuple

from core.models import EmployeeAvailability, WorkStatus


def render_sidebar(employee_names: List[str]) -> Tuple[date, Dict[str, dict]]:
    """
    Render sidebar with week selection and configuration.
    """
    st.sidebar.title("Configuração da Escala")

    st.sidebar.subheader("Seleção da Semana")

    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0 and today.weekday() != 0:
        days_until_monday = 7

    default_monday = today if today.weekday() == 0 else today + timedelta(days=days_until_monday)

    week_start = st.sidebar.date_input(
        "Início da Semana (Segunda-feira)",
        value=default_monday,
        help="Selecione uma segunda-feira para iniciar a semana"
    )

    if week_start.weekday() != 0:
        st.sidebar.error("Por favor, selecione uma segunda-feira!")
        days_to_subtract = week_start.weekday()
        week_start = week_start - timedelta(days=days_to_subtract)
        st.sidebar.info(f"Ajustado para segunda-feira: {week_start.strftime('%d/%m/%Y')}")

    st.sidebar.subheader("Configurações de Bloco de Tempo")
    block_size = st.sidebar.selectbox(
        "Tamanho do Bloco (minutos)",
        options=[30, 60],
        index=0,
        help="Granularidade do bloco de tempo"
    )

    st.sidebar.subheader("Cenários de Demonstração")
    scenario = st.sidebar.selectbox(
        "Carregar Cenário",
        options=["Semana Normal", "Férias Ana (Ter-Qui)", "Múltiplas Ausências"],
        index=0,
        help="Carregar um cenário pré-configurado"
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
    """
    st.sidebar.subheader("Ausências e Substituições")

    absences = {}

    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_name = current_date.strftime("%A")

        with st.sidebar.expander(f"{day_name} ({current_date.strftime('%d/%m')})"):
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
                        "Substituir",
                        key=f"override_{current_date}_{employee}",
                        help="Substituir horários padrão"
                    )

                start_time = None
                end_time = None
                notes = ""

                if status == "Working" and override_hours:
                    col_s, col_e = st.columns(2)
                    with col_s:
                        start_time = st.time_input(
                            "Entrada",
                            value=time(9, 0),
                            key=f"start_{current_date}_{employee}",
                            label_visibility="visible"
                        )
                    with col_e:
                        end_time = st.time_input(
                            "Saída",
                            value=time(17, 0),
                            key=f"end_{current_date}_{employee}",
                            label_visibility="visible"
                        )

                if status != "Working":
                    notes = st.text_input(
                        "Observações",
                        key=f"notes_{current_date}_{employee}",
                        placeholder="Observações opcionais..."
                    )

                day_absences[employee] = {
                    "status": status,
                    "start_time": start_time,
                    "end_time": end_time,
                    "notes": notes
                }

            absences[current_date] = day_absences

    return absences

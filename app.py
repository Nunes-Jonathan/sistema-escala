"""
Sistema de Escala v2.0 - Sistema de Gestão de Escalas Mensais

Ferramenta de agendamento com visual de aplicativo desktop construída com Python + Streamlit.
Gera planilhas mensais de horas de trabalho por categoria, suporta edição,
validação e exportação para Excel/CSV.
"""

import sys
import os

# Ensure the project root is always on sys.path (required on Streamlit Cloud)
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
import tempfile
import json

# Core imports
from core.models import Employee, Category, EmployeeAvailability, WorkStatus, MonthSchedule, VacationPeriod
from core.constants import EMPLOYEE_DEFAULT_HOURS
from core.utils import get_first_of_month, formatar_mes_ano

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
            st.sidebar.warning(f"Não foi possível carregar os dados de férias: {e}")
            return []
    return []


def main():
    """Main application entry point."""
    initialize_session_state()

    # Title
    st.title("📅 Sistema de Escala v2.0")
    st.markdown("**Sistema de Gestão de Escalas Mensais**")
    st.markdown("---")

    # Sidebar - Month selection
    st.sidebar.title("Configuração da Escala")
    st.sidebar.subheader("Seleção do Mês")

    today = date.today()
    default_month_start = get_first_of_month(today)

    month_date = st.sidebar.date_input(
        "Selecionar Mês",
        value=default_month_start,
        help="Selecione qualquer data do mês para escalar"
    )

    month_start = get_first_of_month(month_date)

    st.sidebar.info(f"📅 Escalando para: **{formatar_mes_ano(month_start)}**")

    # Load vacations
    st.sidebar.subheader("Períodos de Férias")
    vacation_count = len(st.session_state.vacation_periods)

    if st.sidebar.button("🔄 Recarregar Férias do Arquivo"):
        st.session_state.vacation_periods = load_vacations()
        st.sidebar.success(f"{len(st.session_state.vacation_periods)} períodos de férias carregados")

    st.sidebar.info(f"**{vacation_count}** período(s) de férias carregado(s)")
    st.sidebar.caption("Gerencie férias na página de Gestão de Férias →")

    # Main content area
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔄 Gerar Escala", type="primary", use_container_width=True):
            with st.spinner("Gerando escala mensal..."):
                # Use vacation periods already in session state (set via Vacation Management page).
                # Do NOT reload from file here — that would discard unsaved in-memory vacations.
                vacation_periods = st.session_state.vacation_periods

                # Generate schedule
                month_schedule = st.session_state.scheduler.generate_month_schedule(
                    month_start,
                    vacation_periods=vacation_periods
                )
                st.session_state.month_schedule = month_schedule

                st.success(f"✅ Escala gerada para {formatar_mes_ano(month_start)}!")
                st.rerun()

    with col2:
        if st.button("✅ Validar Escala", use_container_width=True):
            if st.session_state.month_schedule:
                with st.spinner("Validando..."):
                    validation = st.session_state.scheduler.validate_month_schedule(
                        st.session_state.month_schedule
                    )
                    st.session_state.validation_result = validation
                    st.rerun()
            else:
                st.warning("Gere uma escala primeiro!")

    with col3:
        if st.button("📊 Exportar Excel", use_container_width=True):
            if st.session_state.month_schedule:
                with st.spinner("Gerando Excel..."):
                    temp_dir = tempfile.mkdtemp()
                    output_path = Path(temp_dir) / f"escala_{month_start.strftime('%Y%m')}.xlsx"

                    exporter = ExcelExporter(st.session_state.scheduler.weekend_tracker)
                    exporter.export_schedule(st.session_state.month_schedule, str(output_path))

                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Baixar Excel",
                            data=f,
                            file_name=f"escala_{month_start.strftime('%Y%m')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                    st.success("Arquivo Excel pronto!")
            else:
                st.warning("Gere uma escala primeiro!")

    with col4:
        if st.button("📄 Exportar CSV", use_container_width=True):
            if st.session_state.month_schedule:
                with st.spinner("Gerando CSV..."):
                    temp_dir = tempfile.mkdtemp()

                    exporter = CSVExporter(st.session_state.scheduler.weekend_tracker)
                    zip_path = exporter.export_schedule(st.session_state.month_schedule, temp_dir)

                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Baixar CSV (Zip)",
                            data=f,
                            file_name=f"escala_{month_start.strftime('%Y%m')}.zip",
                            mime="application/zip",
                            use_container_width=True
                        )

                    st.success("Arquivos CSV prontos!")
            else:
                st.warning("Gere uma escala primeiro!")

    st.markdown("---")

    # Display validation results if available
    if st.session_state.validation_result:
        with st.expander("🔍 Resultados da Validação", expanded=False):
            render_validation_results(st.session_state.validation_result)

    # Display schedule if available
    if st.session_state.month_schedule:
        st.markdown(f"## 📋 Escala Mensal - {formatar_mes_ano(month_start)}")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📅 Linha do Tempo",
            "👥 Escalas dos Funcionários",
            "📊 Mapa de Cobertura",
            "🏖️ Resumo dos Fins de Semana",
            "ℹ️ Informações da Escala"
        ])

        with tab1:
            st.subheader("Linha do Tempo")
            st.caption("Selecione uma data para ver a linha do tempo daquele dia")

            month_dates = [d.date for d in st.session_state.month_schedule.days]
            selected_date = st.selectbox(
                "Selecionar Data",
                options=month_dates,
                format_func=lambda d: d.strftime("%A, %d de %B de %Y")
            )

            if selected_date:
                render_monthly_timeline(st.session_state.month_schedule, selected_date)

        with tab2:
            st.subheader("Escalas dos Funcionários")

            employee_names = [emp.name for emp in st.session_state.employees]
            selected_employee = st.selectbox(
                "Selecionar Funcionário",
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
            st.subheader("Informações da Escala")

            col1, col2, col3 = st.columns(3)

            with col1:
                total_days = len(st.session_state.month_schedule.days)
                st.metric("Total de Dias", total_days)

            with col2:
                total_assignments = sum(len(day.assignments) for day in st.session_state.month_schedule.days)
                st.metric("Total de Atribuições", total_assignments)

            with col3:
                vacation_count = len(st.session_state.vacation_periods)
                st.metric("Períodos de Férias", vacation_count)

            st.markdown("### Resumo Dia a Dia")

            summary_data = []
            for day in st.session_state.month_schedule.days:
                working_count = sum(
                    1 for a in day.availability
                    if a.status == WorkStatus.WORKING
                )

                summary_data.append({
                    "Data": day.date.strftime("%d/%m/%Y"),
                    "Dia": day.day_of_week,
                    "Funcionários Trabalhando": working_count,
                    "Total de Atribuições": len(day.assignments)
                })

            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, hide_index=True, use_container_width=True, height=400)

    else:
        st.info("👈 Selecione um mês e clique em 'Gerar Escala' para começar.")

        with st.expander("ℹ️ Como Usar"):
            st.markdown("""
            ### Primeiros Passos

            1. **Selecionar Mês**: Escolha qualquer data do mês que deseja escalar
            2. **Gerenciar Férias**: Acesse a página de Gestão de Férias para adicionar férias dos funcionários
            3. **Gerar**: Clique em "Gerar Escala" para criar a escala mensal
            4. **Revisar**: Use a Linha do Tempo para visualizar as escalas diárias
            5. **Validar**: Verifique lacunas de cobertura e violações de regras
            6. **Exportar**: Baixe como Excel (.xlsx) ou arquivos CSV

            ### Novidades na v2.0

            - **Escala Mensal**: Agendamento para o mês calendário completo (28 a 31 dias)
            - **Ajuste Automático de Horas**: O sistema ajusta automaticamente as horas dos funcionários flexíveis para garantir a cobertura
            - **HD Supervisor**: Anderson atribuído à função de HD Supervisor quando não está cobrindo outros
            - **Linha do Tempo**: Visualização em estilo gráfico de barras das escalas dos funcionários
            - **Gestão de Férias**: Página dedicada ao gerenciamento de férias dos funcionários
            - **Garantia de Cobertura**: Todas as janelas de cobertura necessárias são garantidamente preenchidas

            ### Regras de Prioridade

            Quando a cobertura é necessária, o sistema ajusta as horas nesta ordem:
            1. **Anderson** — Primeira prioridade (cobertura matutina)
            2. **Gabriel** — Segunda prioridade (tarde/noite)
            3. **Pedro** — Terceira prioridade (tarde/noite)
            4. **Outros funcionários flexíveis** — Conforme necessário

            **Observação**: Funcionários fixos (Cesar, Roberto, Oscar, Amanda) nunca alteram seus horários.
            """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Sistema de Escala v2.0 | Desenvolvido com Streamlit + Python | Motor de Escala Mensal"
    "</div>",
    unsafe_allow_html=True
)


if __name__ == "__main__":
    main()

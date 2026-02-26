"""Página de Gestão de Férias - Sistema de Escala."""

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
    page_title="Gestão de Férias - Sistema de Escala",
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
    """Salva os períodos de férias em arquivo JSON."""
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
    """Carrega os períodos de férias do arquivo JSON."""
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
    """Retorna todos os sábados e domingos dentro de um período de férias."""
    days = []
    current = vp.start_date
    while current <= vp.end_date:
        if current.weekday() in (5, 6):
            days.append(current)
        current += timedelta(days=1)
    return days


def analyze_weekend_impact(vacation: VacationPeriod, all_vacations: list) -> dict:
    """
    Verifica o impacto das férias na cobertura dos fins de semana.

    Retorna um dict com:
      - weekend_days: lista de sáb/dom dentro das férias
      - works_weekends: se o funcionário faz parte da equipe de fim de semana
      - conflicting: dict mapeando cada dia de fim de semana para lista de outros
                     funcionários da equipe também ausentes
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
st.title("🏖️ Gestão de Férias")
st.markdown("Gerencie os períodos de férias dos funcionários para geração da escala")

st.markdown("---")

# Add new vacation period
st.subheader("➕ Adicionar Período de Férias")

with st.form("add_vacation"):
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        employee = st.selectbox(
            "Funcionário",
            options=st.session_state.employee_names,
            key="new_vacation_employee"
        )

    with col2:
        start_date = st.date_input(
            "Data de Início",
            value=date.today(),
            key="new_vacation_start"
        )

    with col3:
        end_date = st.date_input(
            "Data de Término",
            value=max(start_date, date.today()) + timedelta(days=7),
            min_value=start_date,
            key="new_vacation_end"
        )

    notes = st.text_input(
        "Observações (opcional)",
        placeholder="ex.: Férias em família, Licença médica, etc.",
        key="new_vacation_notes"
    )

    submitted = st.form_submit_button("Adicionar Férias", type="primary", use_container_width=False)

    if submitted:
        if end_date < start_date:
            st.error("A data de término deve ser igual ou posterior à data de início!")
        else:
            new_vacation = VacationPeriod(
                employee_name=employee,
                start_date=start_date,
                end_date=end_date,
                notes=notes
            )

            st.session_state.vacation_periods.append(new_vacation)
            st.success(
                f"✅ Férias adicionadas para {employee} "
                f"({start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')})"
            )
            st.rerun()

st.markdown("---")

# Display existing vacations
st.subheader("📋 Períodos de Férias Atuais")

if st.session_state.vacation_periods:
    vacation_data = []

    for i, vp in enumerate(st.session_state.vacation_periods):
        duration = (vp.end_date - vp.start_date).days + 1

        vacation_data.append({
            "ID": i,
            "Funcionário": vp.employee_name,
            "Data de Início": vp.start_date.strftime("%d/%m/%Y"),
            "Data de Término": vp.end_date.strftime("%d/%m/%Y"),
            "Duração (dias)": duration,
            "Observações": vp.notes or "-"
        })

    df = pd.DataFrame(vacation_data)

    st.dataframe(
        df.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True
    )

    # Delete vacation section
    st.subheader("🗑️ Remover Férias")

    col1, col2 = st.columns([2, 4])

    with col1:
        vacation_to_delete = st.selectbox(
            "Selecionar férias para remover",
            options=range(len(st.session_state.vacation_periods)),
            format_func=lambda i: (
                f"{st.session_state.vacation_periods[i].employee_name} "
                f"({st.session_state.vacation_periods[i].start_date.strftime('%d/%m/%Y')} "
                f"a {st.session_state.vacation_periods[i].end_date.strftime('%d/%m/%Y')})"
            )
        )

    with col2:
        if st.button("🗑️ Remover Férias Selecionadas", type="secondary"):
            removed = st.session_state.vacation_periods.pop(vacation_to_delete)
            st.success(f"Férias de {removed.employee_name} removidas")
            st.rerun()

else:
    st.info("Nenhum período de férias adicionado. Use o formulário acima para adicionar férias.")

st.markdown("---")

# Weekend Impact Analysis
st.subheader("📅 Análise de Impacto nos Fins de Semana")

if st.session_state.vacation_periods:
    all_employees = create_employees()
    weekend_crew = [e.name for e in all_employees if e.name not in WEEKEND_NEVER_WORK]
    weekend_crew_size = len(weekend_crew)

    for vp in st.session_state.vacation_periods:
        impact = analyze_weekend_impact(vp, st.session_state.vacation_periods)

        with st.expander(
            f"{vp.employee_name}  |  {vp.start_date.strftime('%d/%m/%Y')} → {vp.end_date.strftime('%d/%m/%Y')}",
            expanded=True,
        ):
            if not impact["weekend_days"]:
                st.success("Nenhum dia de fim de semana nessas férias — sem impacto na cobertura.")
            elif not impact["works_weekends"]:
                st.success(
                    f"{vp.employee_name} não trabalha nos fins de semana, portanto essas férias "
                    "não afetam a cobertura dos fins de semana."
                )
            else:
                for day in impact["weekend_days"]:
                    day_name = day.strftime("%A %d/%m/%Y")
                    others_off = impact["conflicting"][day]
                    available = weekend_crew_size - 1 - len(others_off)

                    if others_off:
                        st.warning(
                            f"**{day_name}** — {available}/{weekend_crew_size} da equipe de fim de semana "
                            f"disponível. Também ausente(s): {', '.join(others_off)}."
                        )
                    else:
                        st.info(
                            f"**{day_name}** — {available}/{weekend_crew_size} da equipe de fim de semana "
                            "disponível. Sem outros conflitos."
                        )
else:
    st.info("Adicione períodos de férias acima para ver o impacto nos fins de semana.")

st.markdown("---")

# Save/Load section
st.subheader("💾 Salvar/Carregar Dados de Férias")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💾 Salvar em Arquivo", use_container_width=True):
        if st.session_state.vacation_periods:
            save_path = save_vacations_to_file()
            st.success(f"{len(st.session_state.vacation_periods)} período(s) de férias salvos em {save_path}")
        else:
            st.warning("Nenhum período de férias para salvar")

with col2:
    if st.button("📂 Carregar do Arquivo", use_container_width=True):
        loaded_vacations = load_vacations_from_file()
        if loaded_vacations:
            st.session_state.vacation_periods = loaded_vacations
            st.success(f"{len(loaded_vacations)} período(s) de férias carregados")
            st.rerun()
        else:
            st.info("Nenhum arquivo de férias encontrado")

with col3:
    if st.button("🗑️ Limpar Tudo", use_container_width=True):
        if st.session_state.vacation_periods:
            count = len(st.session_state.vacation_periods)
            st.session_state.vacation_periods = []
            st.success(f"{count} período(s) de férias removidos")
            st.rerun()
        else:
            st.info("Nenhuma férias para limpar")

# Summary statistics
if st.session_state.vacation_periods:
    st.markdown("---")
    st.subheader("📊 Estatísticas Resumidas")

    employee_counts = {}
    total_days = {}

    for vp in st.session_state.vacation_periods:
        employee_counts[vp.employee_name] = employee_counts.get(vp.employee_name, 0) + 1
        duration = (vp.end_date - vp.start_date).days + 1
        total_days[vp.employee_name] = total_days.get(vp.employee_name, 0) + duration

    summary_data = [
        {
            "Funcionário": emp,
            "Períodos de Férias": count,
            "Total de Dias": total_days[emp]
        }
        for emp, count in employee_counts.items()
    ]

    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, hide_index=True, use_container_width=True)

# Instructions
with st.expander("ℹ️ Como Usar"):
    st.markdown("""
    ### Adicionando Férias

    1. Selecione um funcionário no menu suspenso
    2. Escolha as datas de início e término
    3. Adicione observações opcionais
    4. Clique em "Adicionar Férias"

    ### Gerenciando Férias

    - Visualize todos os períodos de férias atuais na tabela
    - Remova férias individualmente na seção de remoção
    - Limpe todas as férias de uma vez

    ### Salvando/Carregando

    - **Salvar em Arquivo**: Salva os períodos de férias atuais em `vacation_data.json`
    - **Carregar do Arquivo**: Carrega os períodos de férias de `vacation_data.json`
    - **Limpar Tudo**: Remove todos os períodos de férias da memória

    ### Usando Férias nas Escalas

    - Os períodos de férias são aplicados automaticamente ao gerar escalas mensais
    - Funcionários em férias serão marcados com status "Vacation"
    - O sistema ajustará as horas dos outros funcionários para cobrir as lacunas

    **Observação**: Os dados de férias são salvos no diretório atual como `vacation_data.json`
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Sistema de Escala v2.0 | Gestão de Férias"
    "</div>",
    unsafe_allow_html=True
)

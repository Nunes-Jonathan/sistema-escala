"""CSV export functionality."""

import pandas as pd
import zipfile
from datetime import time
from pathlib import Path
from typing import List, Dict

from core.models import MonthSchedule, DaySchedule
from core.constants import CATEGORIES, CATEGORY_COVERAGE, EMPLOYEE_DEFAULT_HOURS
from core.utils import generate_time_blocks, is_weekend
from engine.weekend_tracker import WeekendTracker


class CSVExporter:
    """Exports schedule to CSV format."""

    def __init__(self, weekend_tracker: WeekendTracker):
        self.weekend_tracker = weekend_tracker

    def export_schedule(
        self,
        month_schedule: MonthSchedule,
        output_dir: str
    ) -> str:
        """
        Export month schedule to CSV files (zipped).

        Args:
            month_schedule: Schedule to export
            output_dir: Directory to save CSV files

        Returns:
            Path to zip file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create individual CSV files
        workhours_path = output_path / "workhours.csv"
        weekdays_path = output_path / "weekdays_grid.csv"
        weekend_path = output_path / "weekend_grid.csv"

        self._export_workhours(month_schedule, str(workhours_path))
        self._export_weekdays_grid(month_schedule, str(weekdays_path))
        self._export_weekend_grid(month_schedule, str(weekend_path))

        # Create zip file
        zip_path = output_path / f"schedule_{month_schedule.month_start.strftime('%Y%m%d')}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(workhours_path, "workhours.csv")
            zipf.write(weekdays_path, "weekdays_grid.csv")
            zipf.write(weekend_path, "weekend_grid.csv")

        # Clean up individual files
        workhours_path.unlink()
        weekdays_path.unlink()
        weekend_path.unlink()

        return str(zip_path)

    def _export_workhours(self, month_schedule: MonthSchedule, output_path: str):
        """Export WorkHours data to CSV."""
        rows = []

        for day_schedule in month_schedule.days:
            for avail in day_schedule.availability:
                # Get actual times
                default_start, default_end = EMPLOYEE_DEFAULT_HOURS.get(
                    avail.employee_name,
                    (time(9, 0), time(17, 0))
                )

                start_time = avail.start_time or default_start
                end_time = avail.end_time or default_end

                rows.append({
                    "Data": day_schedule.date.strftime("%d/%m/%Y"),
                    "Dia da Semana": day_schedule.day_of_week,
                    "Funcionário": avail.employee_name,
                    "Status": avail.status,
                    "Entrada": start_time.strftime("%H:%M"),
                    "Saída": end_time.strftime("%H:%M"),
                    "Observações": avail.notes
                })

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)

    def _export_weekdays_grid(self, month_schedule: MonthSchedule, output_path: str):
        """Export WeekdaysGrid data to CSV."""
        rows = []

        # Get weekday schedules
        weekday_schedules = [
            day for day in month_schedule.days
            if not is_weekend(day.date)
        ]

        time_blocks = generate_time_blocks(8, 24, 30)

        for day_schedule in weekday_schedules:
            for block in time_blocks:
                row = {
                    "Data": day_schedule.date.strftime("%d/%m/%Y"),
                    "Dia da Semana": day_schedule.day_of_week,
                    "Bloco de Tempo": str(block)
                }

                for category in CATEGORIES:
                    assignments = [
                        a for a in day_schedule.assignments
                        if a.category == category and a.time_block == block
                    ]

                    if assignments:
                        employees = ", ".join(sorted(set(a.employee_name for a in assignments)))
                        row[category] = employees
                    else:
                        row[category] = ""

                rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)

    def _export_weekend_grid(self, month_schedule: MonthSchedule, output_path: str):
        """Export WeekendGrid data to CSV."""
        rows = []

        # Get weekend schedules
        weekend_schedules = [
            day for day in month_schedule.days
            if is_weekend(day.date)
        ]

        time_blocks = generate_time_blocks(8, 24, 30)

        # Grid data
        for day_schedule in weekend_schedules:
            for block in time_blocks:
                row = {
                    "Data": day_schedule.date.strftime("%d/%m/%Y"),
                    "Dia da Semana": day_schedule.day_of_week,
                    "Bloco de Tempo": str(block)
                }

                for category in CATEGORIES:
                    assignments = [
                        a for a in day_schedule.assignments
                        if a.category == category and a.time_block == block
                    ]

                    if assignments:
                        employees = ", ".join(sorted(set(a.employee_name for a in assignments)))
                        row[category] = employees
                    else:
                        row[category] = ""

                rows.append(row)

        # Weekend summary data
        month = month_schedule.month_start
        summary = self.weekend_tracker.get_weekend_summary(month)

        rows.append({})  # Empty row separator
        rows.append({"Data": "Resumo de Fins de Semana"})
        rows.append({})

        for employee, tracking in sorted(summary.items()):
            rows.append({
                "Data": employee,
                "Dia da Semana": f"Folga: {tracking.weekends_off}",
                "Bloco de Tempo": f"Sáb: {tracking.weekends_worked_saturday}",
                "Salas": f"Dom: {tracking.weekends_worked_sunday}",
                "Helpdesk": f"Total: {tracking.total_weekends_worked}",
                "Tech": "Conforme" if tracking.is_compliant else "Não Conforme"
            })

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)

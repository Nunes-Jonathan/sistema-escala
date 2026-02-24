"""
Demo script to generate a sample schedule and export to Excel.

Run this to test the system without starting the Streamlit UI.
"""

from datetime import date, timedelta
from pathlib import Path

from engine.scheduler import Scheduler
from export.excel_exporter import ExcelExporter
from export.csv_exporter import CSVExporter
from tests.demo_scenarios import create_employees, create_categories, get_scenario


def main():
    """Run demo schedule generation."""
    print("Sistema de Escala - Demo")
    print("=" * 50)

    # Initialize
    print("\n1. Initializing scheduler...")
    employees = create_employees()
    categories = create_categories()
    scheduler = Scheduler(employees, categories)

    print(f"   - {len(employees)} employees configured")
    print(f"   - {len(categories)} categories configured")

    # Get week start (next Monday)
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0 and today.weekday() != 0:
        days_until_monday = 7

    week_start = today if today.weekday() == 0 else today + timedelta(days=days_until_monday)
    print(f"\n2. Week start: {week_start.strftime('%Y-%m-%d (%A)')}")

    # Generate schedules for all scenarios
    scenarios = ["Normal Week", "Ana Vacation (Tue-Thu)", "Multiple Absences"]

    for scenario_name in scenarios:
        print(f"\n3. Generating schedule for: {scenario_name}")

        # Get availability
        availability = get_scenario(scenario_name, week_start)

        # Generate schedule
        week_schedule = scheduler.generate_week_schedule(week_start, availability)
        print(f"   - Generated schedule with {len(week_schedule.days)} days")

        # Count assignments
        total_assignments = sum(len(day.assignments) for day in week_schedule.days)
        print(f"   - Total assignments: {total_assignments}")

        # Validate
        print("\n4. Validating schedule...")
        validation = scheduler.validate_schedule(week_schedule)

        if validation.is_valid:
            print("   ✓ Schedule is valid!")
        else:
            print("   ✗ Schedule has issues:")

        if validation.uncovered_blocks:
            print(f"   - Uncovered blocks: {sum(len(blocks) for blocks in validation.uncovered_blocks.values())}")
            for category, blocks in list(validation.uncovered_blocks.items())[:3]:
                print(f"     • {category}: {len(blocks)} blocks")

        if validation.rule_violations:
            print(f"   - Rule violations: {len(validation.rule_violations)}")
            for violation in validation.rule_violations[:3]:
                print(f"     • {violation}")

        if validation.warnings:
            print(f"   - Warnings: {len(validation.warnings)}")
            for warning in validation.warnings[:3]:
                print(f"     • {warning}")

        # Export
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Excel export
        print("\n5. Exporting to Excel...")
        excel_exporter = ExcelExporter(scheduler.weekend_tracker)
        excel_path = output_dir / f"schedule_{scenario_name.replace(' ', '_')}_{week_start.strftime('%Y%m%d')}.xlsx"
        excel_exporter.export_schedule(week_schedule, str(excel_path))
        print(f"   ✓ Excel saved to: {excel_path}")

        # CSV export
        print("\n6. Exporting to CSV...")
        csv_exporter = CSVExporter(scheduler.weekend_tracker)
        csv_output = output_dir / scenario_name.replace(' ', '_')
        zip_path = csv_exporter.export_schedule(week_schedule, str(csv_output))
        print(f"   ✓ CSV (zipped) saved to: {zip_path}")

        # Weekend summary
        print("\n7. Weekend Summary:")
        weekend_summary = scheduler.get_weekend_summary(week_start)

        working_weekends = {
            emp: data for emp, data in weekend_summary.items()
            if data["total_worked"] > 0
        }

        if working_weekends:
            for employee, data in sorted(working_weekends.items()):
                status = "✓" if data["is_compliant"] else "✗"
                print(f"   {status} {employee}: {data['total_worked']} weekend(s) worked")

        print("\n" + "=" * 50)

    print("\n✓ Demo completed successfully!")
    print(f"\nCheck the 'output/' directory for generated files.")


if __name__ == "__main__":
    main()

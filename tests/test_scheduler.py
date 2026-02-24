"""Unit tests for the scheduling system."""

import unittest
from datetime import date, time, timedelta

from core.models import Employee, Category, EmployeeAvailability, WorkStatus
from engine.scheduler import Scheduler
from tests.demo_scenarios import create_employees, create_categories, get_scenario


class TestScheduler(unittest.TestCase):
    """Test cases for the scheduling system."""

    def setUp(self):
        """Set up test fixtures."""
        self.employees = create_employees()
        self.categories = create_categories()
        self.scheduler = Scheduler(self.employees, self.categories)

        # Use a known Monday
        self.test_monday = date(2026, 1, 5)  # A Monday in 2026

    def test_create_employees(self):
        """Test employee creation."""
        self.assertEqual(len(self.employees), 10)

        # Check specific employees
        ana = next(emp for emp in self.employees if emp.name == "Ana")
        self.assertEqual(ana.default_start, time(8, 0))
        self.assertEqual(ana.default_end, time(16, 0))
        self.assertFalse(ana.is_fixed)

        cesar = next(emp for emp in self.employees if emp.name == "Cesar")
        self.assertTrue(cesar.is_fixed)
        self.assertIn("Supervisor de Marketing", cesar.allowed_categories)

    def test_create_categories(self):
        """Test category creation."""
        self.assertEqual(len(self.categories), 5)

        # Check specific categories
        salas = next(cat for cat in self.categories if cat.name == "Salas")
        self.assertEqual(salas.coverage_start, time(12, 0))
        self.assertEqual(salas.coverage_end, time(0, 0))

    def test_scenario_normal_week(self):
        """Test normal week scenario."""
        availability = get_scenario("Normal Week", self.test_monday)

        # Should have 7 days
        self.assertEqual(len(availability), 7)

        # Check Monday availability
        monday_avail = availability[self.test_monday]
        self.assertEqual(len(monday_avail), 10)  # All employees

        # All should be working on Monday
        working_count = sum(1 for a in monday_avail if a.status == WorkStatus.WORKING)
        self.assertGreater(working_count, 5)  # Most should be working

    def test_scenario_ana_vacation(self):
        """Test Ana vacation scenario."""
        availability = get_scenario("Ana Vacation (Tue-Thu)", self.test_monday)

        # Check Tuesday (Ana should be on vacation)
        tuesday = self.test_monday + timedelta(days=1)
        tuesday_avail = availability[tuesday]

        ana_avail = next(a for a in tuesday_avail if a.employee_name == "Ana")
        self.assertEqual(ana_avail.status, WorkStatus.VACATION)

    def test_generate_schedule(self):
        """Test schedule generation."""
        availability = get_scenario("Normal Week", self.test_monday)

        week_schedule = self.scheduler.generate_week_schedule(
            self.test_monday,
            availability
        )

        # Should have 7 days
        self.assertEqual(len(week_schedule.days), 7)

        # Check each day has assignments
        for day in week_schedule.days:
            self.assertGreater(len(day.assignments), 0)

    def test_validate_schedule(self):
        """Test schedule validation."""
        availability = get_scenario("Normal Week", self.test_monday)

        week_schedule = self.scheduler.generate_week_schedule(
            self.test_monday,
            availability
        )

        validation = self.scheduler.validate_schedule(week_schedule)

        # Should have some validation results
        self.assertIsNotNone(validation)

        # Print results for debugging
        if validation.rule_violations:
            print(f"\nRule violations: {len(validation.rule_violations)}")
            for v in validation.rule_violations:
                print(f"  - {v}")

        if validation.uncovered_blocks:
            print(f"\nUncovered blocks: {len(validation.uncovered_blocks)}")
            for cat, blocks in validation.uncovered_blocks.items():
                print(f"  - {cat}: {len(blocks)} blocks")

    def test_weekend_tracking(self):
        """Test weekend tracking."""
        availability = get_scenario("Normal Week", self.test_monday)

        week_schedule = self.scheduler.generate_week_schedule(
            self.test_monday,
            availability
        )

        # Get weekend summary
        summary = self.scheduler.get_weekend_summary(self.test_monday)

        # Should have entries for all employees
        self.assertGreater(len(summary), 0)

        # Check that Cesar doesn't work weekends
        if "Cesar" in summary:
            cesar_summary = summary["Cesar"]
            self.assertEqual(cesar_summary["weekends_worked_saturday"], 0)
            self.assertEqual(cesar_summary["weekends_worked_sunday"], 0)

    def test_regenerate_schedule(self):
        """Test schedule regeneration with updates."""
        # Generate initial schedule
        availability = get_scenario("Normal Week", self.test_monday)

        week_schedule = self.scheduler.generate_week_schedule(
            self.test_monday,
            availability
        )

        # Modify availability (set Ana to vacation on Wednesday)
        wednesday = self.test_monday + timedelta(days=2)

        for avail in availability[wednesday]:
            if avail.employee_name == "Ana":
                avail.status = WorkStatus.VACATION
                break

        # Regenerate
        new_schedule = self.scheduler.regenerate_with_updates(
            week_schedule,
            availability
        )

        # Should be different
        self.assertIsNotNone(new_schedule)
        self.assertEqual(len(new_schedule.days), 7)


class TestDataModels(unittest.TestCase):
    """Test Pydantic data models."""

    def test_employee_model(self):
        """Test Employee model."""
        emp = Employee(
            name="Test",
            default_start=time(9, 0),
            default_end=time(17, 0),
            is_fixed=False,
            allowed_categories={"Salas", "Helpdesk"},
            works_weekends=True,
            is_last_resort=False
        )

        self.assertEqual(emp.name, "Test")
        self.assertIn("Salas", emp.allowed_categories)

    def test_category_model(self):
        """Test Category model."""
        cat = Category(
            name="Test Category",
            coverage_start=time(9, 0),
            coverage_end=time(17, 0),
            exclusive_employees=None
        )

        self.assertEqual(cat.name, "Test Category")

        # Test block generation
        blocks = cat.get_required_blocks(30)
        self.assertGreater(len(blocks), 0)

    def test_employee_availability_model(self):
        """Test EmployeeAvailability model."""
        avail = EmployeeAvailability(
            employee_name="Ana",
            date=date(2026, 1, 5),
            status=WorkStatus.WORKING,
            start_time=time(9, 0),
            end_time=time(17, 0),
            notes="Test"
        )

        self.assertEqual(avail.employee_name, "Ana")
        self.assertEqual(avail.status, WorkStatus.WORKING)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()

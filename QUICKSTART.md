# Quick Start Guide

Get up and running in 5 minutes.

## Installation (2 minutes)

```bash
# Navigate to project
cd sistema-escala

# Install dependencies
pip install -r requirements.txt
```

## Run the App (30 seconds)

```bash
streamlit run app.py
```

Browser opens to http://localhost:8501

## First Schedule (2 minutes)

1. **Select Week**: In sidebar, choose a Monday date
2. **Pick Scenario**: Select "Normal Week" from dropdown
3. **Generate**: Click "🔄 Generate Schedule" button
4. **View**: Navigate through Mon-Sun tabs to see assignments
5. **Validate**: Click "✅ Validate Schedule" to check coverage
6. **Export**: Click "📊 Export Excel" to download

Done! You have your first schedule.

## Try Other Scenarios

**Ana Vacation:**
- Select "Ana Vacation (Tue-Thu)"
- Generate and see how system handles absence

**Multiple Absences:**
- Select "Multiple Absences"
- See overlap fallback in action

## Edit and Regenerate

1. Go to "✏️ Edit Availability" tab
2. Change status or hours in table
3. Click "🔄 Regenerate with Edits"
4. See updated schedule instantly

## Understanding the Output

### Daily View
- Each tab = one day (Mon-Sun)
- Rows = time blocks (30-min from 08:00-24:00)
- Columns = categories (Salas, Helpdesk, Tech, etc.)
- Cells = employee names assigned

### Validation Results
- **Green**: Schedule is valid
- **Yellow**: Warnings (overlaps, preferences)
- **Red**: Errors (double-bookings, violations)

### Weekend Summary
- Shows who worked which weekends
- ✓ = compliant with 2-off/2-working rule
- ✗ = non-compliant

## Excel Export Format

**Tab 1: WorkHours**
- Employee availability data
- Import/edit this in Excel if needed

**Tab 2: WeekdaysGrid**
- Mon-Fri assignments by time block
- Coverage summary at bottom

**Tab 3: WeekendGrid**
- Sat-Sun assignments
- Weekend tracking compliance

## Common Tasks

### Add Employee Absence
1. Sidebar → expand the day
2. Select employee → change status to "DayOff" or "Vacation"
3. Regenerate

### Override Working Hours
1. Sidebar → expand the day
2. Check "Override" for employee
3. Set custom start/end times
4. Regenerate

### Export Both Formats
1. Click "📊 Export Excel" → download .xlsx
2. Click "📄 Export CSV" → download .zip
3. Unzip CSV to get 3 files

## Tips

- **Week Selection**: Must be a Monday (auto-corrects)
- **Validation First**: Always validate before exporting
- **Edit Tab**: Best for bulk changes
- **Sidebar**: Best for quick single changes
- **Scenarios**: Good starting points for customization

## Next Steps

- Read README.md for full features
- Check INSTALL.md for troubleshooting
- See ARCHITECTURE.md for technical details
- Modify core/constants.py to customize

## Help

**Can't install?**
→ See INSTALL.md

**Validation errors?**
→ Click validation expander to see details

**Export not working?**
→ Generate schedule first

**Want to customize?**
→ Edit core/constants.py

---

**You're ready to schedule!**

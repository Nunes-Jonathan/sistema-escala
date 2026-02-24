# Installation and Running Instructions

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- A modern web browser (Chrome, Firefox, Safari, or Edge)

## Installation Steps

### 1. Navigate to the project directory

```bash
cd sistema-escala
```

### 2. (Optional but Recommended) Create a virtual environment

#### On Linux/Mac:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### On Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This will install:
- streamlit==1.31.0 (Web UI framework)
- pandas==2.2.0 (Data manipulation)
- pydantic==2.6.0 (Data validation)
- openpyxl==3.1.2 (Excel export)
- python-dateutil==2.8.2 (Date utilities)
- pyyaml==6.0.1 (Configuration files)

### 4. Verify installation

```bash
python -c "import streamlit; print('Streamlit version:', streamlit.__version__)"
```

You should see: `Streamlit version: 1.31.0`

## Running the Application

### Main Streamlit App

```bash
streamlit run app.py
```

This will:
1. Start a local web server
2. Open your browser to http://localhost:8501
3. Display the Sistema de Escala interface

**First-time users:**
- Streamlit may ask for your email - you can skip this
- It may also ask about usage analytics - choose your preference

### Demo Script (No UI)

To test the system without the UI:

```bash
python demo.py
```

This will:
1. Generate schedules for all 3 demo scenarios
2. Export to Excel and CSV
3. Save files in the `output/` directory
4. Print validation results to console

### Running Tests

```bash
python -m pytest tests/test_scheduler.py -v
```

Or run directly:

```bash
python tests/test_scheduler.py
```

## Using the Application

### Step-by-Step Guide

1. **Select Week Start Date**
   - In the sidebar, choose a Monday date
   - If you select a non-Monday, it will auto-adjust

2. **Choose a Scenario**
   - Normal Week: All employees working default hours
   - Ana Vacation (Tue-Thu): Tests absence handling
   - Multiple Absences: Forces overlap fallback

3. **Generate Schedule**
   - Click "🔄 Generate Schedule" button
   - Wait for confirmation message

4. **Review Schedule**
   - Navigate through the daily view tabs (Mon-Sun)
   - Check employee summary for workload distribution
   - Review weekend summary for compliance

5. **Validate**
   - Click "✅ Validate Schedule"
   - Review uncovered blocks, violations, and warnings
   - Make adjustments if needed

6. **Edit Availability** (Optional)
   - Go to "✏️ Edit Availability" tab
   - Modify status, hours, or notes in the table
   - Click "🔄 Regenerate with Edits"

7. **Export**
   - Click "📊 Export Excel" for .xlsx file
   - Click "📄 Export CSV" for zipped CSV bundle
   - Files download automatically

## Troubleshooting

### "Module not found" errors

Make sure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

### "Port already in use" error

Streamlit default port (8501) is occupied. Specify a different port:
```bash
streamlit run app.py --server.port 8502
```

### Streamlit won't open browser

Manually navigate to: http://localhost:8501

### "Please select a Monday!" warning

The week start must be a Monday. The app will auto-adjust to the nearest Monday.

### Schedule generation is slow

For the given data size (10 employees, 5 categories, 7 days), generation should be instant (<1 second). If it's slow:
- Check system resources
- Close other applications
- Restart the Streamlit app

### Excel export not working

Ensure openpyxl is installed:
```bash
pip install openpyxl
```

### CSV export not working

The export creates a zip file. Ensure you have write permissions in the temp directory.

## File Locations

### Generated Files

**When using Streamlit:**
- Files are created in temporary directory
- Downloads handled by browser
- No persistent storage by default

**When using demo.py:**
- Files saved to `output/` directory
- Excel files: `output/schedule_*.xlsx`
- CSV files: `output/schedule_*.zip`

## Configuration

### Changing Block Size

In `core/constants.py`:
```python
BLOCK_SIZE_MINUTES = 30  # Change to 60 for hourly blocks
```

### Adding Employees

In `core/constants.py`:
```python
EMPLOYEE_DEFAULT_HOURS["NewName"] = (time(9, 0), time(17, 0))
EMPLOYEE_ALLOWED_CATEGORIES["NewName"] = {"Salas", "Helpdesk"}
```

### Modifying Categories

In `core/constants.py`:
```python
CATEGORY_COVERAGE["NewCategory"] = (time(10, 0), time(18, 0))
```

## Uninstalling

1. Deactivate virtual environment:
```bash
deactivate
```

2. Delete the project directory:
```bash
rm -rf sistema-escala
```

## Getting Help

- Check README.md for feature documentation
- Review ARCHITECTURE.md for technical details
- See ASSUMPTIONS.md for design decisions
- Modify code directly - it's well-commented!

## Next Steps

After installation:
1. Run the demo script to see it in action
2. Launch the Streamlit app and try each scenario
3. Edit availability and regenerate schedules
4. Export to Excel and review the 3 tabs
5. Customize for your own use case

---

**Happy Scheduling!**

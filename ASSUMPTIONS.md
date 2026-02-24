# Assumptions Documentation

This document lists all assumptions made during the development of Sistema de Escala.

## Time and Date Assumptions

1. **Week Definition**: All weeks start on Monday and end on Sunday (7 days)
2. **Time Blocks**: 30-minute blocks are sufficient granularity for all scheduling needs
3. **Coverage Window**: 08:00-24:00 covers all possible category coverage requirements
4. **Midnight Crossing**: Times like "06PM-12AM" are handled as crossing midnight (18:00 on day N to 00:00 on day N+1)
5. **Time Block Boundaries**: All employee hours and category coverage align to minimum 30-minute boundaries
6. **Weekend Definition**: Saturday and Sunday are considered weekend days (days 5 and 6 of the week)

## Employee Assumptions

7. **Fixed vs Flexible**: Fixed employees (Cesar, Roberto, Oscar, Amanda) can NEVER change their working hours under any circumstance
8. **Flexible Employee Hours**: Flexible employees can adjust their hours when needed, but prefer default hours
9. **Employee Availability**: Employees are either Working, on DayOff, or on Vacation for an entire day (no partial-day statuses)
10. **Anderson as Last Resort**: Anderson should only be used when other employees cannot cover (implemented via scoring)
11. **Amanda's 3-Hour Limit**: Amanda always works exactly 3 hours (06PM-09PM) and cannot be extended
12. **Employee Count**: The system has exactly 10 employees (can be extended, but demo uses 10)
13. **No Part-Time Employees**: All employees work full shifts on working days (no 2-hour shifts except Amanda)

## Category Assumptions

14. **Category Count**: The system handles exactly 5 categories (Salas, Helpdesk, Tech, Supervisor de Marketing, Marketing)
15. **Exclusive Categories**: Some categories can only be done by specific employees (Cesar→Supervisor de Marketing, Oscar→Marketing, Roberto→Tech)
16. **Non-Exclusive Categories**: Salas and Helpdesk can be done by multiple employees (Ana, Lilian, Luisa, Anderson, Pedro, Gabriel, Amanda)
17. **Category Priority**: Fixed-employee categories should be assigned first (prevents resource conflicts)
18. **Coverage Requirements**: Each category must be covered for ALL blocks in its coverage window (no partial coverage acceptable)

## Weekend Assumptions

19. **Weekend Count**: Each month has approximately 4 weekends (system doesn't adjust for 5-weekend months)
20. **Weekend Rule**: Each employee works 2 weekends off + 2 weekends working one day = 4 weekends/month
21. **Weekend Day Selection**: On working weekends, employees work EITHER Saturday OR Sunday (not both, except Anderson)
22. **Weekend Exemptions**: Cesar, Oscar, Roberto, Amanda NEVER work weekends (business rule)
23. **Anderson Weekend Rule**: When Anderson works weekends, it's ALWAYS Saturday, ALWAYS Helpdesk, ALWAYS 08:00-18:00
24. **Month Definition**: Weekend tracking is per calendar month (not rolling 30-day window)
25. **Weekend Compliance**: Non-compliance is flagged but doesn't prevent schedule generation (warning only)

## Overlap and Fallback Assumptions

26. **Overlap Justification**: Salas+Helpdesk overlap is only allowed when there are employee absences (vacation/day off)
27. **Overlap Detection**: The system can detect when overlap assignments are created
28. **Fallback Priority**: Overlaps are used as a last resort after all single-category assignments attempted
29. **No Triple Overlap**: An employee can do at most 2 categories simultaneously (Salas+Helpdesk only)
30. **Other Category Overlaps**: Categories other than Salas+Helpdesk cannot overlap (e.g., no Tech+Marketing)

## Scheduling Algorithm Assumptions

31. **Deterministic**: Same input availability always produces the same schedule (no randomness)
32. **Greedy Approach**: Simple greedy algorithm is sufficient (not using constraint programming solver)
33. **No Backtracking**: Once an assignment is made, it's not reconsidered (forward-only)
34. **Local Optimization**: Each day is optimized independently (no week-level optimization)
35. **Scoring Weights**: The scoring weights (10.0 for non-Anderson, 5.0 for default hours, etc.) are reasonable and balanced
36. **No Load Balancing**: The system doesn't explicitly balance workload across employees (emergent from rules)

## Validation Assumptions

37. **Validation Timing**: Validation happens after generation (not during)
38. **Validation Independence**: Validation logic is independent of assignment logic
39. **Error Recovery**: Validation errors don't trigger automatic re-generation (user must fix manually)
40. **Warning vs Error**: Warnings don't invalidate a schedule, errors do
41. **Uncovered Blocks**: Uncovered blocks are reported but don't cause generation to fail (best effort)

## Data Model Assumptions

42. **Pydantic Validation**: Pydantic models provide sufficient validation for all data
43. **No Database**: All data is in-memory during session (no persistence layer)
44. **Session State**: Streamlit session state is reliable for storing schedule data
45. **Data Consistency**: Users won't manually edit data in ways that violate constraints
46. **Date Formats**: Python's date/time objects are sufficient (no timezone complexity)

## UI Assumptions

47. **Single User**: The app is designed for single-user local use (no multi-user concurrency)
48. **Desktop Browser**: Users access via desktop browser (not optimized for mobile)
49. **Modern Browser**: Browser supports all Streamlit features (recent Chrome/Firefox/Safari)
50. **Screen Size**: Users have at least 1280px width for optimal viewing
51. **User Expertise**: Users understand scheduling concepts and business rules
52. **Edit Interface**: Users prefer table-based editing over form-based (hence data_editor)

## Export Assumptions

53. **Excel Compatibility**: openpyxl produces files compatible with Microsoft Excel and LibreOffice
54. **File Size**: Generated Excel/CSV files are small enough for easy download (<10MB)
55. **Three Tabs Sufficient**: The 3-tab structure (WorkHours, WeekdaysGrid, WeekendGrid) covers all needs
56. **CSV Encoding**: UTF-8 encoding is acceptable for all CSV files
57. **Zip Compression**: Users can handle .zip files for CSV downloads
58. **No Import**: The system doesn't need to import schedules from Excel/CSV (export only)

## Business Logic Assumptions

59. **Coverage Gaps Acceptable**: The system reports uncovered blocks but doesn't force coverage
60. **Cost Indifferent**: All employees have the same "cost" (no wage optimization)
61. **No Shift Preferences**: Employees don't have preferences for specific shifts
62. **No Skills Levels**: Within allowed categories, all employees are equally skilled
63. **No Break Time**: The system doesn't model break times within shifts
64. **No Shift Minimums**: No minimum shift length (except Amanda's 3-hour constraint)

## Extensibility Assumptions

65. **Easy Employee Addition**: Adding new employees requires only constant updates (no code changes)
66. **Easy Category Addition**: Adding new categories requires only constant updates
67. **Algorithm Swap**: The assignment algorithm can be replaced without changing other components
68. **Validation Extension**: New validation rules can be added without refactoring
69. **Export Format Addition**: New export formats can be added alongside existing ones

## Error Handling Assumptions

70. **User Correction**: Users can fix validation errors by editing availability and regenerating
71. **No Automatic Recovery**: System doesn't try to auto-fix impossible schedules
72. **Clear Error Messages**: Validation messages are clear enough for users to understand issues
73. **Graceful Degradation**: Partial schedules are acceptable if full coverage isn't possible

## Performance Assumptions

74. **Small Data**: ~10 employees, 5 categories, 7 days is small enough for instant processing
75. **No Caching Needed**: Schedule generation is fast enough without caching
76. **UI Responsiveness**: Streamlit reruns are fast enough for good UX
77. **Export Speed**: Excel/CSV generation is fast enough for synchronous operation

## Future Considerations (Not Currently Assumed)

These are NOT currently implemented but could be future enhancements:

- Multi-week scheduling
- Historical data and trends
- Shift swap requests
- Employee preferences
- Overtime tracking
- Budget constraints
- Skills matrix
- Training requirements
- Leave balance tracking
- Notification system
- Multi-location support
- Role-based access control
- Audit logging
- Schedule templates
- Recurring patterns

---

**Note**: These assumptions were made to deliver a working, production-quality system within scope. They can be revisited based on real-world usage feedback.

**Version**: 1.0
**Last Updated**: 2026-01-07

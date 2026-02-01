---
name: xlsx
description: Create, edit, and analyze Excel spreadsheets (.xlsx). Use when Claude needs to build financial models, data exports, or any spreadsheet with proper formulas and formatting.
---

# XLSX Spreadsheet Operations

## Requirements
- Zero formula errors (#REF!, #DIV/0!, #VALUE!, #N/A, #NAME?)
- Always use Excel formulas, never hardcode calculated values in Python

## Financial Model Standards

### Color Coding
- **Blue text**: Hardcoded inputs users will modify
- **Black text**: Formulas and calculations
- **Green text**: Internal worksheet links
- **Red text**: External file links
- **Yellow background**: Key assumptions

### Number Formatting
- Currency: `$#,##0` with units in headers ("Revenue ($mm)")
- Percentages: `0.0%`
- Zeros: displayed as dashes (`-`)
- Negatives: parentheses `(100)` not minus `-100`
- Years: text format `"2024"` not `2,024`

## Formula Rules
- Place ALL assumptions in separate assumption cells
- Use cell references instead of hardcoded values
- Document sources for any hardcoded value: `Source: [System], [Date], [Reference]`

## Tools

### pandas — For data analysis
```python
import pandas as pd
df = pd.read_excel("input.xlsx")
df.to_excel("output.xlsx", index=False)
```

### openpyxl — For formulas and formatting
```python
from openpyxl import load_workbook
wb = load_workbook("input.xlsx")
ws = wb.active
ws['A1'] = '=SUM(B1:B10)'
wb.save("output.xlsx")
```

**Warning**: `data_only=True` replaces formulas with cached values permanently if saved.

**Note**: Cell indices are 1-based in openpyxl.

## Formula Verification Checklist
- Test sample cell references manually
- Confirm column/row mapping matches data
- Check for NaN/None values in source data
- Verify denominators are non-zero
- Validate cross-sheet references

## Recalculation
After creating/modifying files with formulas:
```bash
python recalc.py output.xlsx
```
Returns JSON showing any error locations.

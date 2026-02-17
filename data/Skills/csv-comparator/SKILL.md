---
name: csv-comparator
description: >
  Compare two or more CSV files and generate a detailed Markdown diff report.
  Use this skill whenever the user asks to compare CSVs, verify CSV data,
  diff tabular data, validate OCR results against ground truth, or check
  for discrepancies between data files. Also trigger when the user mentions
  "CSV comparison", "data verification", "CSV diff", "CSV validation",
  "compare spreadsheets", "check differences", or asks to find mismatches
  between tabular datasets. Supports 1 reference ("correct") CSV vs N test CSVs.
---

# CSV Comparator

Compare CSV files and produce a structured Markdown report showing all differences.

## Overview

This skill compares a **reference CSV** (ground truth) against one or more **test CSVs**.
It detects value mismatches, missing/extra rows, duplicate keys, and structural issues,
then outputs a Markdown report with summary statistics and detailed diff tables.

## Workflow

### Step 1: Receive Files

User provides 2+ CSV files. Ask which file is the **reference** (correct/ground truth).
If only 2 files, confirm which is reference and which is test.

### Step 2: Column Classification (MUST confirm with user)

Read the CSV headers and ask the user to classify each column into one of three categories:

| Category | Purpose | Example |
|----------|---------|---------|
| **Key columns** | Uniquely identify each row. All key columns are concatenated to form a composite key for matching rows across files. | `pageNum`, `Date`, `category`, `label` |
| **Data columns** | Values to compare between files. Differences in these columns are reported as mismatches. | `amount`, `tax_rate` |
| **Ignored columns** | Excluded from comparison entirely. | `checksum`, `remarks` |

Present columns as a numbered list and ask the user to assign categories.
Example prompt:

```
The CSV has these columns:
1. pageNum
2. Date
3. category
4. label
5. amount
6. tax_rate
7. checksum

Please classify each column:
- Key columns (used to match rows): e.g., 1,2,3,4
- Data columns (values to compare): e.g., 5,6
- Ignored columns (skip): e.g., 7
```

### Step 3: Execute Comparison

Run the comparison script:

```bash
python3 scripts/compare_csv.py \
  --reference <path_to_reference.csv> \
  --test <path_to_test1.csv> [<path_to_test2.csv> ...] \
  --keys "col1,col2,col3" \
  --data "col4,col5" \
  --output <output_report.md>
```

**Arguments:**
- `--reference`: Path to the reference CSV
- `--test`: One or more test CSV paths (space-separated)
- `--keys`: Comma-separated key column names
- `--data`: Comma-separated data column names
- `--output`: Output Markdown file path (default: `comparison_report.md`)

### Step 4: Deliver Report

Present the generated Markdown report to the user.
Highlight critical findings (duplicate keys, missing rows, high mismatch rates).

## Report Structure

The output Markdown follows this template:

```markdown
# CSV Comparison Report

- Generated: {timestamp}
- Reference: {filename}
- Test files: {filenames}
- Key columns: {list}
- Data columns: {list}

## Summary

| Metric | Test File 1 | Test File 2 | ... |
|--------|------------|------------|-----|
| Total rows (reference) | N | N | |
| Total rows (test) | N | N | |
| Matched rows | N | N | |
| Rows only in reference | N | N | |
| Rows only in test | N | N | |
| Rows with differences | N | N | |
| Duplicate keys in test | N | N | |
| Match rate | X% | X% | |

## Errors

### Duplicate Keys
(Listed per file if any detected)

### Row Count Mismatches
(Listed per file if any detected)

## Detail: {test_filename}

### Rows Only in Reference (missing from test)
| key1 | key2 | ... | data1 | data2 | ... |
|------|------|-----|-------|-------|-----|

### Rows Only in Test (extra in test)
| key1 | key2 | ... | data1 | data2 | ... |
|------|------|-----|-------|-------|-----|

### Value Differences
| key1 | key2 | ... | Column | Reference | Test |
|------|------|-----|--------|-----------|------|

(Repeat Detail section for each test file)
```

## Edge Cases

- **Encoding**: All CSVs are read as UTF-8 with BOM handling.
- **Normalization (applied to ALL columns uniformly)**:
  - Full-width alphanumeric and symbols are converted to half-width (e.g., `Ａ→A`, `１→1`, `（→(`)
  - All spaces are removed (both half-width U+0020 and full-width U+3000)
  - Leading/trailing whitespace is stripped
  - This is a redundant safety measure; upstream CSV-generating systems should output half-width characters.
- **All values compared as strings**: No numeric coercion. `"1680"` ≠ `"1680.0"`.
- **Empty values**: Empty string and missing values are treated as equivalent.
- **Quoted fields**: Standard CSV quoting is handled by Python csv module.
- **Duplicate keys**: If a key appears more than once within a single file, it is reported as an error. The first occurrence is used for comparison; subsequent duplicates are listed in the Errors section.
- **Large files**: The script processes files row-by-row and should handle CSVs up to ~1M rows.

## Script Details

The main comparison logic is in `scripts/compare_csv.py`.
Read `references/algorithm.md` for the detailed matching algorithm.

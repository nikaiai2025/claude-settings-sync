# Comparison Algorithm

## Value Normalization

All cell values are normalized before comparison:
1. Strip leading/trailing ASCII whitespace (space, tab, newline)
2. Strip leading/trailing full-width space (U+3000)
3. Internal whitespace is preserved (may be meaningful data)
4. `None` and empty string are treated as equivalent (both become `""`)

## Key Generation

1. For each row, concatenate all key column values with **Unit Separator (U+001F)**
   - This ASCII control character is virtually never present in real CSV data
   - Avoids collision with pipe `|`, comma, space, tab, or any printable character
2. Each key component is normalized (see above) before joining
3. Example: `pageNum=1`, `category=入金`, `label=①売上高(店) 10%`
   → Key: `1\x1f入金\x1f①売上高(店) 10%`

## Duplicate Key Detection

Before comparison, scan each file independently:
- Build a dict of `composite_key → list[row_number]`
- If any key maps to >1 row, flag as duplicate
- Report all duplicates with row numbers
- Use only the FIRST occurrence for subsequent comparison

## Row Matching

1. Build key→row dict for reference file
2. Build key→row dict for each test file
3. Classify rows into:
   - **Matched**: key exists in both reference and test
   - **Reference-only**: key exists in reference but not in test
   - **Test-only**: key exists in test but not in reference

## Value Comparison

For each matched row:
1. Iterate over data columns
2. Normalize both values, compare as strings
3. If values differ, record: composite key, column name, reference value, test value

## Markdown Output Safety

When rendering values into Markdown tables:
- Pipe `|` is escaped as `\|` (prevents table column breakage)
- Newlines are replaced with spaces (prevents row breakage)

## Sorting

Output is sorted by composite key to ensure deterministic, readable reports.

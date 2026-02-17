#!/usr/bin/env python3
"""
CSV Comparator - Compare a reference CSV against one or more test CSVs.

Usage:
    python3 compare_csv.py \
        --reference ref.csv \
        --test test1.csv test2.csv \
        --keys "pageNum,Date,category,label" \
        --data "amount,tax_rate" \
        --output comparison_report.md
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from collections import OrderedDict


def read_csv(filepath: str) -> tuple[list[str], list[dict]]:
    """Read a CSV file and return (headers, rows_as_dicts).
    Handles UTF-8 with BOM."""
    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows




# Use ASCII Unit Separator (U+001F) as internal key delimiter.
# This character is virtually never present in real CSV data,
# avoiding collisions with pipe, comma, tab, or any printable character.
KEY_SEPARATOR = "\x1f"


def normalize_value(val: str) -> str:
    """Normalize a cell value for comparison.
    Applies the same normalization as key columns for consistency:
    1. Strip leading/trailing whitespace (half-width and full-width)
    2. Convert full-width alphanumeric/symbols to half-width
    3. Remove ALL spaces (half-width U+0020 and full-width U+3000)
    This ensures a simple, uniform rule: all values are normalized before comparison."""
    if val is None:
        return ""
    val = val.strip().strip("\u3000")
    val = _fullwidth_to_halfwidth(val)
    val = val.replace(" ", "").replace("\u3000", "")
    return val


def _fullwidth_to_halfwidth(text: str) -> str:
    """Convert full-width alphanumeric and common symbols to half-width.
    Covers: Ａ-Ｚ, ａ-ｚ, ０-９, and common full-width symbols like
    （）！？＋－＊／＝．，：；＠＃＄％＆ etc.
    Full-width range: U+FF01..U+FF5E → Half-width: U+0021..U+007E"""
    result = []
    for ch in text:
        cp = ord(ch)
        if 0xFF01 <= cp <= 0xFF5E:
            result.append(chr(cp - 0xFEE0))
        else:
            result.append(ch)
    return "".join(result)


def normalize_key(val: str) -> str:
    """Normalize a cell value for KEY column matching.
    Applies aggressive normalization to maximize matching:
    1. Strip leading/trailing whitespace (half-width and full-width)
    2. Convert full-width alphanumeric/symbols to half-width
    3. Remove ALL spaces (half-width U+0020 and full-width U+3000)
    This is intentionally lossy — it prioritizes matching over preserving
    exact formatting. Key values in the report still show original data."""
    if val is None:
        return ""
    val = val.strip().strip("\u3000")
    val = _fullwidth_to_halfwidth(val)
    val = val.replace(" ", "").replace("\u3000", "")
    return val


def make_composite_key(row: dict, key_columns: list[str]) -> str:
    """Build a composite key by joining NORMALIZED key column values with KEY_SEPARATOR.
    Uses U+001F (Unit Separator) to avoid collision with any printable character
    that might exist in actual data (pipe, comma, space, etc.).
    Key normalization: full-width→half-width, all spaces removed."""
    parts = []
    for col in key_columns:
        val = row.get(col, "")
        parts.append(normalize_key(val))
    return KEY_SEPARATOR.join(parts)


def build_key_index(rows: list[dict], key_columns: list[str]) -> tuple[OrderedDict, dict]:
    """Build key→row mapping and detect duplicates.
    Returns (key_to_row, key_to_duplicate_row_numbers)."""
    key_to_row = OrderedDict()
    key_to_row_nums = {}
    duplicates = {}

    for i, row in enumerate(rows):
        key = make_composite_key(row, key_columns)
        row_num = i + 2  # 1-based, +1 for header
        if key in key_to_row_nums:
            if key not in duplicates:
                duplicates[key] = [key_to_row_nums[key]]
            duplicates[key].append(row_num)
        else:
            key_to_row[key] = row
            key_to_row_nums[key] = row_num

    return key_to_row, duplicates


def compare_rows(ref_row: dict, test_row: dict, data_columns: list[str]) -> list[tuple[str, str, str]]:
    """Compare data columns between two rows.
    Returns list of (column, ref_value, test_value) for mismatches."""
    diffs = []
    for col in data_columns:
        ref_val = normalize_value(ref_row.get(col, "") or "")
        test_val = normalize_value(test_row.get(col, "") or "")
        if ref_val != test_val:
            diffs.append((col, ref_val, test_val))
    return diffs


def compare_files(
    ref_path: str,
    test_paths: list[str],
    key_columns: list[str],
    data_columns: list[str],
) -> dict:
    """Run the full comparison and return structured results."""

    # Read reference
    ref_headers, ref_rows = read_csv(ref_path)

    # Validate columns exist in reference
    all_needed = key_columns + data_columns
    missing = [c for c in all_needed if c not in ref_headers]
    if missing:
        print(f"ERROR: Columns not found in reference CSV: {missing}", file=sys.stderr)
        sys.exit(1)

    ref_index, ref_duplicates = build_key_index(ref_rows, key_columns)

    results = {
        "reference": {
            "path": ref_path,
            "filename": os.path.basename(ref_path),
            "total_rows": len(ref_rows),
            "duplicates": ref_duplicates,
        },
        "tests": [],
    }

    for test_path in test_paths:
        test_headers, test_rows = read_csv(test_path)

        # Validate columns exist in test
        missing_test = [c for c in all_needed if c not in test_headers]
        if missing_test:
            print(f"ERROR: Columns not found in {test_path}: {missing_test}", file=sys.stderr)
            sys.exit(1)

        test_index, test_duplicates = build_key_index(test_rows, key_columns)

        # Classify rows
        ref_only_keys = []
        test_only_keys = []
        matched_keys = []
        value_diffs = []

        for key in ref_index:
            if key in test_index:
                matched_keys.append(key)
            else:
                ref_only_keys.append(key)

        for key in test_index:
            if key not in ref_index:
                test_only_keys.append(key)

        # Compare matched rows
        for key in matched_keys:
            diffs = compare_rows(ref_index[key], test_index[key], data_columns)
            if diffs:
                value_diffs.append((key, diffs))

        total_comparisons = len(matched_keys) * len(data_columns) if data_columns else len(matched_keys)
        total_cell_diffs = sum(len(d) for _, d in value_diffs)
        match_rate_rows = (
            (len(matched_keys) - len(value_diffs)) / len(ref_index) * 100
            if ref_index
            else 100.0
        )

        results["tests"].append({
            "path": test_path,
            "filename": os.path.basename(test_path),
            "total_rows": len(test_rows),
            "duplicates": test_duplicates,
            "matched_count": len(matched_keys),
            "ref_only_keys": ref_only_keys,
            "test_only_keys": test_only_keys,
            "value_diffs": value_diffs,
            "rows_with_diffs": len(value_diffs),
            "cell_diffs": total_cell_diffs,
            "match_rate_rows": match_rate_rows,
        })

    return results


def format_key_display(key: str, key_columns: list[str]) -> list[str]:
    """Split composite key back into individual column values."""
    parts = key.split(KEY_SEPARATOR)
    # Pad if needed
    while len(parts) < len(key_columns):
        parts.append("")
    return parts


def escape_md_table(val: str) -> str:
    """Escape characters that break Markdown table rendering.
    - Pipe '|' is the column delimiter → escape as '\\|'
    - Newlines would break the row → replace with space
    """
    val = val.replace("|", "\\|")
    val = val.replace("\n", " ").replace("\r", " ")
    return val


def generate_report(
    results: dict,
    key_columns: list[str],
    data_columns: list[str],
    ref_index: OrderedDict,
    test_indices: list[OrderedDict],
) -> str:
    """Generate the Markdown report."""
    lines = []
    ref = results["reference"]
    tests = results["tests"]

    lines.append("# CSV Comparison Report")
    lines.append("")
    lines.append(f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **Reference**: `{ref['filename']}`")
    test_names = ", ".join(f"`{t['filename']}`" for t in tests)
    lines.append(f"- **Test files**: {test_names}")
    lines.append(f"- **Key columns**: {', '.join(key_columns)}")
    lines.append(f"- **Data columns**: {', '.join(data_columns)}")
    lines.append("")

    # === Summary ===
    lines.append("## Summary")
    lines.append("")

    # Build summary table
    header = ["Metric"] + [f"`{t['filename']}`" for t in tests]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    metrics = [
        ("Total rows (reference)", [str(ref["total_rows"])] * len(tests)),
        ("Total rows (test)", [str(t["total_rows"]) for t in tests]),
        ("Matched rows", [str(t["matched_count"]) for t in tests]),
        ("Rows only in reference", [str(len(t["ref_only_keys"])) for t in tests]),
        ("Rows only in test", [str(len(t["test_only_keys"])) for t in tests]),
        ("Rows with value differences", [str(t["rows_with_diffs"]) for t in tests]),
        ("Total cell differences", [str(t["cell_diffs"]) for t in tests]),
        ("Duplicate keys in reference", [str(len(ref["duplicates"]))] * len(tests)),
        ("Duplicate keys in test", [str(len(t["duplicates"])) for t in tests]),
        ("Row match rate", [f"{t['match_rate_rows']:.1f}%" for t in tests]),
    ]

    for label, values in metrics:
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    lines.append("")

    # === Errors ===
    has_errors = False
    error_lines = []
    error_lines.append("## Errors")
    error_lines.append("")

    # Duplicate keys
    if ref["duplicates"]:
        has_errors = True
        error_lines.append(f"### Duplicate Keys in Reference (`{ref['filename']}`)")
        error_lines.append("")
        error_lines.append("| Composite Key | Row Numbers |")
        error_lines.append("| --- | --- |")
        for key, row_nums in ref["duplicates"].items():
            display_key = escape_md_table(key.replace(KEY_SEPARATOR, " | "))
            error_lines.append(f"| `{display_key}` | {', '.join(str(r) for r in row_nums)} |")
        error_lines.append("")

    for t in tests:
        if t["duplicates"]:
            has_errors = True
            error_lines.append(f"### Duplicate Keys in Test (`{t['filename']}`)")
            error_lines.append("")
            error_lines.append("| Composite Key | Row Numbers |")
            error_lines.append("| --- | --- |")
            for key, row_nums in t["duplicates"].items():
                display_key = escape_md_table(key.replace(KEY_SEPARATOR, " | "))
                error_lines.append(f"| `{display_key}` | {', '.join(str(r) for r in row_nums)} |")
            error_lines.append("")

    # Row count mismatches
    for t in tests:
        if t["total_rows"] != ref["total_rows"]:
            has_errors = True
            diff = t["total_rows"] - ref["total_rows"]
            sign = "+" if diff > 0 else ""
            error_lines.append(
                f"### Row Count Mismatch: `{t['filename']}` ({sign}{diff} rows)"
            )
            error_lines.append("")
            error_lines.append(
                f"Reference has **{ref['total_rows']}** rows, "
                f"test has **{t['total_rows']}** rows."
            )
            error_lines.append("")

    if has_errors:
        lines.extend(error_lines)
    else:
        lines.append("## Errors")
        lines.append("")
        lines.append("No errors detected.")
        lines.append("")

    # === Detail per test file ===
    for idx, t in enumerate(tests):
        lines.append(f"## Detail: `{t['filename']}`")
        lines.append("")

        # Rows only in reference
        lines.append("### Rows Only in Reference (missing from test)")
        lines.append("")
        if t["ref_only_keys"]:
            cols = key_columns + data_columns
            lines.append("| " + " | ".join(cols) + " |")
            lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
            for key in sorted(t["ref_only_keys"]):
                row = ref_index[key]
                vals = [escape_md_table(normalize_value(row.get(c, "") or "")) for c in cols]
                lines.append("| " + " | ".join(vals) + " |")
            lines.append("")
        else:
            lines.append("None.")
            lines.append("")

        # Rows only in test
        lines.append("### Rows Only in Test (extra in test)")
        lines.append("")
        if t["test_only_keys"]:
            cols = key_columns + data_columns
            lines.append("| " + " | ".join(cols) + " |")
            lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
            for key in sorted(t["test_only_keys"]):
                row = test_indices[idx][key]
                vals = [escape_md_table(normalize_value(row.get(c, "") or "")) for c in cols]
                lines.append("| " + " | ".join(vals) + " |")
            lines.append("")
        else:
            lines.append("None.")
            lines.append("")

        # Value differences
        lines.append("### Value Differences")
        lines.append("")
        if t["value_diffs"]:
            diff_header = key_columns + ["Column", "Reference", "Test"]
            lines.append("| " + " | ".join(diff_header) + " |")
            lines.append("| " + " | ".join(["---"] * len(diff_header)) + " |")
            for key, diffs in sorted(t["value_diffs"], key=lambda x: x[0]):
                key_parts = format_key_display(key, key_columns)
                for col, ref_val, test_val in diffs:
                    # Mark empty values explicitly so they are visible in the table
                    display_ref = ref_val if ref_val != "" else "(empty)"
                    display_test = test_val if test_val != "" else "(empty)"
                    row_vals = key_parts + [col, display_ref, display_test]
                    row_vals = [escape_md_table(v) for v in row_vals]
                    lines.append("| " + " | ".join(row_vals) + " |")
            lines.append("")
        else:
            lines.append("All matched rows are identical.")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Report generated by csv-comparator*")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare CSV files and generate a Markdown diff report.")
    parser.add_argument("--reference", required=True, help="Path to reference CSV")
    parser.add_argument("--test", nargs="+", required=True, help="Path(s) to test CSV(s)")
    parser.add_argument("--keys", required=True, help="Comma-separated key column names")
    parser.add_argument("--data", required=True, help="Comma-separated data column names")
    parser.add_argument("--output", default="comparison_report.md", help="Output Markdown file path")
    args = parser.parse_args()

    key_columns = [c.strip() for c in args.keys.split(",")]
    data_columns = [c.strip() for c in args.data.split(",")]

    # Run comparison
    results = compare_files(args.reference, args.test, key_columns, data_columns)

    # Build indices for report generation
    _, ref_rows = read_csv(args.reference)
    ref_index, _ = build_key_index(ref_rows, key_columns)

    test_indices = []
    for tp in args.test:
        _, t_rows = read_csv(tp)
        t_idx, _ = build_key_index(t_rows, key_columns)
        test_indices.append(t_idx)

    # Generate report
    report = generate_report(results, key_columns, data_columns, ref_index, test_indices)

    # Write output
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report written to: {args.output}")

    # Print summary to stdout
    ref = results["reference"]
    for t in results["tests"]:
        status = "✓" if t["rows_with_diffs"] == 0 and not t["ref_only_keys"] and not t["test_only_keys"] else "✗"
        print(f"  {status} {t['filename']}: {t['rows_with_diffs']} rows with diffs, "
              f"{len(t['ref_only_keys'])} missing, {len(t['test_only_keys'])} extra")


if __name__ == "__main__":
    main()

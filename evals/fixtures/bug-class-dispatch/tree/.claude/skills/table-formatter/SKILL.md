---
name: table-formatter
description: Aligns the pipe characters in a markdown table so every column has the same width. Use when a markdown table in the repository has ragged columns and you want it padded without changing any cell. Do not use for CSV, for HTML tables, or when the table needs its rows sorted.
---

# table-formatter

Reads a markdown table, computes the widest cell per column, and pads every
other cell in that column to match. Cell contents and column order are left
alone.

The alignment rules it follows are listed in `reference/columns.md`.

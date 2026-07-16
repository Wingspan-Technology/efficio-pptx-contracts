// Cross-field + duplicate checks for efficio_table_config that JSON Schema cannot express — per cell and
// across cells/rows/columns. Structural validity (JSON shape, value types) is the schema's job, so this
// skips when the tag is absent/blank/unparseable/non-object, and each per-cell comparison is skipped when
// an operand is not a positive integer. Every issue is tagged efficio_table_config. Mirrors the Python
// SDK's table_config_issues, plus duplicate cell/row/column detection.

import type { ComponentSemanticIssue } from "./component-metadata";

const TABLE_CONFIG_TAG = "efficio_table_config";
const PLAIN_TEXT_FORMAT = "plain";

export function validateTableConfigSemantics(
  tags: Record<string, string>
): ComponentSemanticIssue[] {
  const raw = tags[TABLE_CONFIG_TAG];
  if (typeof raw !== "string" || raw.trim() === "") return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return []; // invalid JSON is a structural error the schema layer owns.
  }
  if (!isPlainObject(parsed)) return [];

  const issues: ComponentSemanticIssue[] = [];
  const cells = parsed.cells;
  if (Array.isArray(cells)) {
    for (const entry of cells) {
      if (isPlainObject(entry)) issues.push(...tableCellIssues(entry));
    }
    issues.push(...duplicateCoordinateIssues(cells));
  }
  issues.push(...duplicateAxisIssues(parsed.rows, "row"));
  issues.push(...duplicateAxisIssues(parsed.columns, "col"));
  return issues;
}

function tableCellIssues(entry: Record<string, unknown>): ComponentSemanticIssue[] {
  const value = (field: string): number | undefined => {
    const raw = entry[field];
    return typeof raw === "number" && Number.isInteger(raw) && raw >= 1 ? raw : undefined;
  };
  const maxChars = value("max_chars");
  const targetChars = value("target_chars");
  const minItems = value("min_items");
  const maxItems = value("max_items");
  const targetItems = value("target_items");
  const minPerItem = value("min_chars_per_item");
  const maxPerItem = value("max_chars_per_item");
  const targetPerItem = value("target_chars_per_item");

  const where = cellLabel(entry);
  const issues: ComponentSemanticIssue[] = [];
  const add = (code: string, message: string): void => {
    issues.push({ code, tag: TABLE_CONFIG_TAG, message: `${where} ${message}` });
  };
  const over = (a: number | undefined, b: number | undefined): boolean =>
    a !== undefined && b !== undefined && a > b;
  const under = (a: number | undefined, b: number | undefined): boolean =>
    a !== undefined && b !== undefined && a < b;

  if (over(targetChars, maxChars)) add("target_exceeds_max", "target_chars must not exceed max_chars.");
  if (over(targetItems, maxItems)) add("target_exceeds_max", "target_items must not exceed max_items.");
  if (under(targetItems, minItems)) add("target_below_min", "target_items must be at least min_items.");
  if (over(targetPerItem, maxPerItem))
    add("target_exceeds_max", "target_chars_per_item must not exceed max_chars_per_item.");
  if (under(targetPerItem, minPerItem))
    add("target_below_min", "target_chars_per_item must be at least min_chars_per_item.");
  if (over(minItems, maxItems)) add("min_exceeds_max", "min_items must not exceed max_items.");
  if (over(minPerItem, maxPerItem))
    add("min_exceeds_max", "min_chars_per_item must not exceed max_chars_per_item.");

  // A plain cell (explicit or defaulted) is exactly one item.
  if (entry.text_format === undefined || entry.text_format === PLAIN_TEXT_FORMAT) {
    if (minItems !== undefined && minItems !== 1)
      add("plain_requires_single_item", "min_items must be 1 for a plain cell.");
    if (maxItems !== undefined && maxItems !== 1)
      add("plain_requires_single_item", "max_items must be 1 for a plain cell.");
    if (targetItems !== undefined)
      add("plain_forbids_target_items", "target_items is not valid for a plain cell.");
  }
  return issues;
}

function duplicateCoordinateIssues(cells: unknown[]): ComponentSemanticIssue[] {
  const seen = new Set<string>();
  const reported = new Set<string>();
  const issues: ComponentSemanticIssue[] = [];
  for (const entry of cells) {
    if (!isPlainObject(entry)) continue;
    const row = asIndex(entry.row);
    const col = asIndex(entry.col);
    if (row === undefined || col === undefined) continue;
    const key = `${row},${col}`;
    if (seen.has(key) && !reported.has(key)) {
      issues.push({
        code: "duplicate_cell",
        tag: TABLE_CONFIG_TAG,
        message: `Cell (${row},${col}) is configured more than once.`,
      });
      reported.add(key);
    }
    seen.add(key);
  }
  return issues;
}

function duplicateAxisIssues(value: unknown, key: "row" | "col"): ComponentSemanticIssue[] {
  if (!Array.isArray(value)) return [];
  const label = key === "row" ? "Row" : "Column";
  const seen = new Set<number>();
  const reported = new Set<number>();
  const issues: ComponentSemanticIssue[] = [];
  for (const entry of value) {
    if (!isPlainObject(entry)) continue;
    const index = asIndex(entry[key]);
    if (index === undefined) continue;
    if (seen.has(index) && !reported.has(index)) {
      issues.push({
        code: key === "row" ? "duplicate_row" : "duplicate_column",
        tag: TABLE_CONFIG_TAG,
        message: `${label} ${index} is configured more than once.`,
      });
      reported.add(index);
    }
    seen.add(index);
  }
  return issues;
}

function cellLabel(entry: Record<string, unknown>): string {
  const row = asIndex(entry.row);
  const col = asIndex(entry.col);
  return row !== undefined && col !== undefined ? `Cell (${row},${col}):` : "Cell:";
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asIndex(value: unknown): number | undefined {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : undefined;
}

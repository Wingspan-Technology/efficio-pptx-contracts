// Cross-field + duplicate checks for efficio_table_config that JSON Schema cannot express — per cell and
// across cells/rows/columns. Structural validity (JSON shape, value types) is the schema's job, so this
// skips when the tag is absent/blank/unparseable/non-object, and each per-cell comparison is skipped when
// an operand is not a positive integer. Every issue is tagged efficio_table_config. Mirrors the Python
// SDK's table_config_issues, plus duplicate cell/row/column detection.

import type { ComponentSemanticIssue } from "./component-metadata.js";
import {
  type TextCapacity,
  type TextCapacityField,
  validateTextCapacity,
} from "./text-capacity.js";

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
  if (entry.render_action !== "render") return [];
  const where = cellLabel(entry);
  const capacity = readCapacity(entry);
  if (capacity === undefined) return [];
  const format =
    entry.text_format === undefined || entry.text_format === PLAIN_TEXT_FORMAT
      ? PLAIN_TEXT_FORMAT
      : "multi_item";
  return validateTextCapacity(capacity, format).map((issue) => ({
    code: issue.code,
    tag: TABLE_CONFIG_TAG,
    message: `${where} ${issue.message}`,
  }));
}

function readCapacity(entry: Record<string, unknown>): TextCapacity | undefined {
  const fields: readonly TextCapacityField[] = [
    "max_lines",
    "estimated_chars_per_line",
    "min_items",
    "max_items",
    "target_items",
  ];
  for (const field of fields) {
    const raw = entry[field];
    if (raw !== undefined && !(typeof raw === "number" && Number.isInteger(raw) && raw >= 1)) {
      return undefined;
    }
  }
  return {
    min_items: (entry.min_items as number | undefined) ?? 1,
    ...(entry.max_lines === undefined ? {} : { max_lines: entry.max_lines as number }),
    ...(entry.estimated_chars_per_line === undefined
      ? {}
      : { estimated_chars_per_line: entry.estimated_chars_per_line as number }),
    ...(entry.max_items === undefined ? {} : { max_items: entry.max_items as number }),
    ...(entry.target_items === undefined ? {} : { target_items: entry.target_items as number }),
  };
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

const COMPONENT_TYPE = "efficio_component_type";
const TABLE_CONFIG = "efficio_table_config";
const TEXT_FORMATS = new Set(["plain", "paragraph", "bullets", "numbered_list"]);
const MAX_LINES = "efficio_max_lines";
const CHARS_PER_LINE = "efficio_estimated_chars_per_line";
const MIN_ITEMS = "efficio_min_items";
const MAX_ITEMS = "efficio_max_items";
const TARGET_ITEMS = "efficio_target_items";

const RETIRED_TEXT_FIELDS = [
  "efficio_max_chars",
  "efficio_target_chars",
  "efficio_min_chars_per_item",
  "efficio_max_chars_per_item",
  "efficio_target_chars_per_item",
  "efficio_max_chars_per_line",
] as const;
const TABLE_RETIRED_FIELDS = RETIRED_TEXT_FIELDS.map((field) => field.replace("efficio_", ""));
const TABLE_CAPACITY_FIELDS = new Set([
  "max_lines",
  "estimated_chars_per_line",
  "min_items",
  "max_items",
  "target_items",
  ...TABLE_RETIRED_FIELDS,
]);
const TABLE_CELL_FIELDS = new Set([
  "row", "col", "render_action", "text_format", "instruction", ...TABLE_CAPACITY_FIELDS,
]);

type JsonObject = Record<string, unknown>;

export function migrateTextCapacity(tags: Record<string, string>): void {
  if (tags[COMPONENT_TYPE] === "text") migrateTextTags(tags);
  if (tags[COMPONENT_TYPE] === "table") migrateTableConfig(tags);
}

export function retiredTextCapacityTags(): readonly string[] {
  return RETIRED_TEXT_FIELDS;
}

export function containsRetiredTableCapacityFields(
  tags: Readonly<Record<string, string>>
): boolean {
  if (tags[COMPONENT_TYPE] !== "table") return false;
  const raw = tags[TABLE_CONFIG];
  if (raw === undefined) return false;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return false;
  }
  if (!isObject(parsed) || !Array.isArray(parsed.cells)) return false;
  return parsed.cells.some(
    (cell) =>
      isObject(cell) && Object.keys(cell).some((key) => TABLE_RETIRED_FIELDS.includes(key))
  );
}

function migrateTextTags(tags: Record<string, string>): void {
  const values = Object.fromEntries(textCapacityInputs().map((name) => [name, optionalTagInteger(tags, name)]));
  const maxLines = values[MAX_LINES] ?? values[MAX_ITEMS];
  if (maxLines === undefined) fail("text component has no value from which max_lines can be migrated");
  const charsPerLine = resolveCharsPerLine({
    current: values[CHARS_PER_LINE],
    legacy: values.efficio_max_chars_per_line,
    maxChars: values.efficio_max_chars,
    maxCharsPerItem: values.efficio_max_chars_per_item,
    maxLines,
    subject: "text component",
  });
  const textFormat = tags.efficio_text_format ?? "plain";
  if (!TEXT_FORMATS.has(textFormat)) fail("text component text format is invalid");
  const minItems = values[MIN_ITEMS] ?? 1;
  const maxItems = textFormat === "plain" ? 1 : values[MAX_ITEMS] ?? maxLines;
  const targetItems = values[TARGET_ITEMS];
  validateItemLimits(textFormat, minItems, maxItems, targetItems, maxLines, "text component");

  tags[MAX_LINES] = String(maxLines);
  tags[CHARS_PER_LINE] = String(charsPerLine);
  tags[MIN_ITEMS] = String(minItems);
  tags[MAX_ITEMS] = String(maxItems);
  if (targetItems !== undefined) tags[TARGET_ITEMS] = String(targetItems);
  for (const field of RETIRED_TEXT_FIELDS) delete tags[field];
}

function migrateTableConfig(tags: Record<string, string>): void {
  const raw = tags[TABLE_CONFIG];
  if (raw === undefined) fail("table component is missing efficio_table_config");
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    fail("efficio_table_config must be valid JSON");
  }
  if (!isObject(parsed) || Object.keys(parsed).some((key) => !["rows", "columns", "cells"].includes(key))) {
    fail("efficio_table_config must be a supported JSON object");
  }
  const cells = parsed.cells;
  if (!Array.isArray(cells)) fail("efficio_table_config must contain a cells array");
  cells.forEach((rawCell, index) => {
    if (!isObject(rawCell) || Object.keys(rawCell).some((key) => !TABLE_CELL_FIELDS.has(key))) {
      fail(`table cell ${index} contains unsupported fields`);
    }
    validateCoordinate(rawCell.row, index, "row");
    validateCoordinate(rawCell.col, index, "col");
    migrateTableCell(rawCell, index);
  });
  tags[TABLE_CONFIG] = JSON.stringify(sortJson(parsed));
}

function migrateTableCell(cell: JsonObject, index: number): void {
  if (!Object.keys(cell).some((key) => TABLE_CAPACITY_FIELDS.has(key))) return;
  const values = Object.fromEntries(
    [...TABLE_CAPACITY_FIELDS].map((name) => [name, optionalJsonInteger(cell, name, index)]),
  );
  if ((cell.render_action ?? "preserve") !== "render") {
    removeRetiredTableFields(cell);
    return;
  }

  const textFormat = cell.text_format ?? "plain";
  if (typeof textFormat !== "string" || !TEXT_FORMATS.has(textFormat)) {
    fail(`table cell ${index} text_format is invalid`);
  }
  const lineCapacity = resolveTableLineCapacity(values, textFormat, index);
  const minItems = values.min_items ?? 1;
  const maxItems = textFormat === "plain" ? 1 : values.max_items ?? lineCapacity?.maxLines;
  const targetItems = values.target_items;
  validateItemLimits(
    textFormat,
    minItems,
    maxItems,
    targetItems,
    lineCapacity?.maxLines,
    `table cell ${index}`,
  );

  removeRetiredTableFields(cell);
  if (lineCapacity !== undefined) {
    cell.max_lines = lineCapacity.maxLines;
    cell.estimated_chars_per_line = lineCapacity.charsPerLine;
    cell.min_items = minItems;
    cell.max_items = maxItems;
  }
}

function resolveTableLineCapacity(
  values: Record<string, number | undefined>,
  textFormat: string,
  index: number,
): { maxLines: number; charsPerLine: number } | undefined {
  let maxLines = values.max_lines ?? values.max_items;
  if (maxLines === undefined && textFormat === "plain") maxLines = 1;
  const hasWidthSource = [
    "estimated_chars_per_line",
    "max_chars_per_line",
    "max_chars",
    "max_chars_per_item",
  ].some((field) => values[field] !== undefined);
  if (values.max_lines !== undefined && !hasWidthSource) {
    fail(`table cell ${index} has max_lines without estimated_chars_per_line`);
  }
  if (hasWidthSource && maxLines === undefined) {
    fail(`table cell ${index} has a character capacity without max_lines`);
  }
  if (maxLines === undefined || !hasWidthSource) return undefined;
  return {
    maxLines,
    charsPerLine: resolveCharsPerLine({
      current: values.estimated_chars_per_line,
      legacy: values.max_chars_per_line,
      maxChars: values.max_chars,
      maxCharsPerItem: values.max_chars_per_item,
      maxLines,
      subject: `table cell ${index}`,
    }),
  };
}

function removeRetiredTableFields(cell: JsonObject): void {
  for (const field of TABLE_RETIRED_FIELDS) delete cell[field];
}

function resolveCharsPerLine(input: {
  current?: number; legacy?: number; maxChars?: number; maxCharsPerItem?: number;
  maxLines: number; subject: string;
}): number {
  if (input.current !== undefined && input.legacy !== undefined && input.current !== input.legacy) {
    fail(`${input.subject} has conflicting characters-per-line values`);
  }
  if (input.current !== undefined) return input.current;
  if (input.legacy !== undefined) return input.legacy;
  if (input.maxChars !== undefined) return Math.ceil(input.maxChars / input.maxLines);
  if (input.maxCharsPerItem !== undefined) return input.maxCharsPerItem;
  return fail(`${input.subject} has no value from which estimated_chars_per_line can be migrated`);
}

function validateItemLimits(
  textFormat: string, minimum: number, maximum: number | undefined, target: number | undefined,
  maxLines: number | undefined, subject: string,
): void {
  if (maximum !== undefined && minimum > maximum) {
    fail(`${subject} min_items must not exceed max_items`);
  }
  if (maximum !== undefined && maxLines !== undefined && maximum > maxLines) {
    fail(`${subject} max_items must not exceed max_lines`);
  }
  if (target !== undefined && (target < minimum || (maximum !== undefined && target > maximum))) {
    fail(`${subject} target_items must be within min_items and max_items`);
  }
  if (textFormat === "plain" && (minimum !== 1 || maximum !== 1 || target !== undefined)) {
    fail(`${subject} plain text must use exactly one item and no target_items`);
  }
}

function textCapacityInputs(): string[] {
  return [MAX_LINES, CHARS_PER_LINE, MIN_ITEMS, MAX_ITEMS, TARGET_ITEMS, ...RETIRED_TEXT_FIELDS];
}

function optionalTagInteger(tags: Record<string, string>, name: string): number | undefined {
  const raw = tags[name];
  if (raw === undefined) return undefined;
  const parsed = Number(raw);
  if (!/^[0-9]+$/.test(raw) || !Number.isSafeInteger(parsed) || parsed < 1) {
    fail(`tag ${name} must be a positive integer string`);
  }
  return parsed;
}

function optionalJsonInteger(value: JsonObject, name: string, index: number): number | undefined {
  const raw = value[name];
  if (raw === undefined) return undefined;
  if (typeof raw !== "number" || !Number.isSafeInteger(raw) || raw < 1) {
    fail(`table cell ${index} field ${name} must be a positive integer`);
  }
  return raw;
}

function validateCoordinate(value: unknown, index: number, name: string): void {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    fail(`table cell ${index} ${name} must be a non-negative integer`);
  }
}

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function sortJson(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortJson);
  if (!isObject(value)) return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, sortJson(value[key])]));
}

function fail(message: string): never {
  throw new Error(`text capacity migration failed: ${message}`);
}

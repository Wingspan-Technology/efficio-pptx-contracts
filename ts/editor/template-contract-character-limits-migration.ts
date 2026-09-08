const COMPONENT_TYPE = "efficio_component_type";
const TABLE_CONFIG = "efficio_table_config";
const MAX_LINES = "efficio_max_lines";
const CHARS_PER_LINE = "efficio_estimated_chars_per_line";
const MIN_CHARS = "efficio_min_chars";
const MAX_CHARS = "efficio_max_chars";
const MIN_CHARS_PER_ITEM = "efficio_min_chars_per_item";
const MAX_CHARS_PER_ITEM = "efficio_max_chars_per_item";

type JsonObject = Record<string, unknown>;

export function deriveTextCharacterLimits(tags: Record<string, string>): void {
  if (tags[COMPONENT_TYPE] === "text") deriveTextTags(tags);
  if (tags[COMPONENT_TYPE] === "table") deriveTableCells(tags);
}

function deriveTextTags(tags: Record<string, string>): void {
  const maxLines = positiveTag(tags, MAX_LINES);
  const charsPerLine = positiveTag(tags, CHARS_PER_LINE);
  const maximum = safeCapacity(maxLines, charsPerLine, "text component");
  tags[MIN_CHARS] = "1";
  tags[MAX_CHARS] = String(maximum);
  tags[MIN_CHARS_PER_ITEM] = "1";
  tags[MAX_CHARS_PER_ITEM] = String(maximum);
}

function deriveTableCells(tags: Record<string, string>): void {
  const raw = tags[TABLE_CONFIG];
  if (raw === undefined) fail("table component is missing efficio_table_config");
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    fail("efficio_table_config must be valid JSON");
  }
  if (!isObject(parsed) || !Array.isArray(parsed.cells)) {
    fail("efficio_table_config must contain a cells array");
  }
  let changed = false;
  parsed.cells.forEach((cell, index) => {
    if (!isObject(cell) || cell.render_action !== "render") return;
    const maxLines = optionalPositiveInteger(cell.max_lines, index, "max_lines");
    const charsPerLine = optionalPositiveInteger(
      cell.estimated_chars_per_line,
      index,
      "estimated_chars_per_line"
    );
    if ((maxLines === undefined) !== (charsPerLine === undefined)) {
      fail(
        `table cell ${index} max_lines and estimated_chars_per_line must be provided together`
      );
    }
    if (maxLines === undefined || charsPerLine === undefined) return;
    const maximum = safeCapacity(maxLines, charsPerLine, `table cell ${index}`);
    cell.min_chars = 1;
    cell.max_chars = maximum;
    cell.min_chars_per_item = 1;
    cell.max_chars_per_item = maximum;
    changed = true;
  });
  if (changed) tags[TABLE_CONFIG] = JSON.stringify(sortJson(parsed));
}

function positiveTag(tags: Record<string, string>, name: string): number {
  const raw = tags[name];
  const parsed = Number(raw);
  if (raw === undefined || !/^[0-9]+$/.test(raw) || !Number.isSafeInteger(parsed) || parsed < 1) {
    return fail(`text component requires positive integer tag ${name}`);
  }
  return parsed;
}

function optionalPositiveInteger(
  value: unknown,
  index: number,
  field: string
): number | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 1) {
    return fail(`table cell ${index} field ${field} must be a positive integer`);
  }
  return value;
}

function safeCapacity(maxLines: number, charsPerLine: number, subject: string): number {
  const maximum = maxLines * charsPerLine;
  if (!Number.isSafeInteger(maximum)) {
    return fail(`${subject} character capacity exceeds the supported integer range`);
  }
  return maximum;
}

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function sortJson(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortJson);
  if (!isObject(value)) return value;
  return Object.fromEntries(
    Object.keys(value).sort().map((key) => [key, sortJson(value[key])])
  );
}

function fail(message: string): never {
  throw new Error(`strict character-limit migration failed: ${message}`);
}

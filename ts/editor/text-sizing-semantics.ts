import type { ComponentSemanticIssue } from "./component-metadata.js";
import {
  type TextCapacity,
  type TextCapacityField,
  validateTextCapacity,
} from "./text-capacity.js";

const TEXT_FORMAT_TAG = "efficio_text_format";
const PLAIN_TEXT_FORMAT = "plain";
const TEXT_CAPACITY_TAGS: Record<TextCapacityField, string> = {
  max_lines: "efficio_max_lines",
  estimated_chars_per_line: "efficio_estimated_chars_per_line",
  min_items: "efficio_min_items",
  max_items: "efficio_max_items",
  target_items: "efficio_target_items",
};

export function validateTextSizingSemantics(
  tags: Record<string, string>
): ComponentSemanticIssue[] {
  const capacity = readCapacity(tags);
  if (capacity === undefined) return [];
  const textFormat = tags[TEXT_FORMAT_TAG] === PLAIN_TEXT_FORMAT ? PLAIN_TEXT_FORMAT : "multi_item";
  return validateTextCapacity(capacity, textFormat).map((issue) => {
    const tag = TEXT_CAPACITY_TAGS[issue.field];
    return { code: issue.code, tag, message: componentTagMessage(issue.message) };
  });
}

function componentTagMessage(message: string): string {
  return (Object.entries(TEXT_CAPACITY_TAGS) as [TextCapacityField, string][]).reduce(
    (result, [field, tag]) => result.replaceAll(field, `"${tag}"`),
    message
  );
}

function isPositiveIntegerString(value: string | undefined): boolean {
  if (typeof value !== "string") return false;
  const trimmed = value.trim();
  return /^\d+$/.test(trimmed) && Number(trimmed) >= 1;
}

function readCapacity(tags: Record<string, string>): TextCapacity | undefined {
  const value = (field: Exclude<TextCapacityField, "target_items">): number | undefined => {
    const raw = tags[TEXT_CAPACITY_TAGS[field]];
    return isPositiveIntegerString(raw) ? Number(raw.trim()) : undefined;
  };
  const maxLines = value("max_lines");
  const charsPerLine = value("estimated_chars_per_line");
  const minItems = value("min_items");
  const maxItems = value("max_items");
  if (
    maxLines === undefined ||
    charsPerLine === undefined ||
    minItems === undefined ||
    maxItems === undefined
  ) {
    return undefined;
  }
  const targetRaw = tags[TEXT_CAPACITY_TAGS.target_items];
  const targetItems = isPositiveIntegerString(targetRaw) ? Number(targetRaw.trim()) : undefined;
  return {
    max_lines: maxLines,
    estimated_chars_per_line: charsPerLine,
    min_items: minItems,
    max_items: maxItems,
    ...(targetItems === undefined ? {} : { target_items: targetItems }),
  };
}

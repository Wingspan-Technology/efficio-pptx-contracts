// Cross-field text sizing checks the per-tag schema cannot express. The `target_*` tags (including
// `target_items`) are OPTIONAL AI guidance that must fit within their strict min/max bounds; plain text
// additionally forbids `target_items` (always one item). Returned as plain issues so a consumer maps them
// into its own validation result. A no-op for non-text shapes (the tags are absent), and each check is
// skipped when an operand is not a positive integer (the per-tag schema owns those structural errors).
// Mirrors the Python SDK's `text_sizing_issues`.

import type { ComponentSemanticIssue } from "./component-metadata.js";

const TEXT_FORMAT_TAG = "efficio_text_format";
const PLAIN_TEXT_FORMAT = "plain";
const TEXT_MAX_CHARS_TAG = "efficio_max_chars";
const TEXT_TARGET_CHARS_TAG = "efficio_target_chars";
const TEXT_MIN_ITEMS_TAG = "efficio_min_items";
const TEXT_MAX_ITEMS_TAG = "efficio_max_items";
const TEXT_TARGET_ITEMS_TAG = "efficio_target_items";
const TEXT_MIN_CHARS_PER_ITEM_TAG = "efficio_min_chars_per_item";
const TEXT_MAX_CHARS_PER_ITEM_TAG = "efficio_max_chars_per_item";
const TEXT_TARGET_CHARS_PER_ITEM_TAG = "efficio_target_chars_per_item";

export function validateTextSizingSemantics(
  tags: Record<string, string>
): ComponentSemanticIssue[] {
  const value = (tag: string): number | undefined => {
    const raw = tags[tag];
    return isPositiveIntegerString(raw) ? Number(raw.trim()) : undefined;
  };
  const maxChars = value(TEXT_MAX_CHARS_TAG);
  const targetChars = value(TEXT_TARGET_CHARS_TAG);
  const minItems = value(TEXT_MIN_ITEMS_TAG);
  const maxItems = value(TEXT_MAX_ITEMS_TAG);
  const targetItems = value(TEXT_TARGET_ITEMS_TAG);
  const minPerItem = value(TEXT_MIN_CHARS_PER_ITEM_TAG);
  const maxPerItem = value(TEXT_MAX_CHARS_PER_ITEM_TAG);
  const targetPerItem = value(TEXT_TARGET_CHARS_PER_ITEM_TAG);

  const issues: ComponentSemanticIssue[] = [];
  const exceeds = (tag: string, other: string): void => {
    issues.push({ code: "target_exceeds_max", tag, message: `"${tag}" must not exceed "${other}".` });
  };

  // Optional targets must fit within their strict bounds.
  if (targetChars !== undefined && maxChars !== undefined && targetChars > maxChars) {
    exceeds(TEXT_TARGET_CHARS_TAG, TEXT_MAX_CHARS_TAG);
  }
  if (targetItems !== undefined && maxItems !== undefined && targetItems > maxItems) {
    exceeds(TEXT_TARGET_ITEMS_TAG, TEXT_MAX_ITEMS_TAG);
  }
  if (targetItems !== undefined && minItems !== undefined && targetItems < minItems) {
    issues.push({
      code: "target_below_min",
      tag: TEXT_TARGET_ITEMS_TAG,
      message: `"${TEXT_TARGET_ITEMS_TAG}" must be at least "${TEXT_MIN_ITEMS_TAG}".`,
    });
  }
  if (targetPerItem !== undefined && maxPerItem !== undefined && targetPerItem > maxPerItem) {
    exceeds(TEXT_TARGET_CHARS_PER_ITEM_TAG, TEXT_MAX_CHARS_PER_ITEM_TAG);
  }
  if (targetPerItem !== undefined && minPerItem !== undefined && targetPerItem < minPerItem) {
    issues.push({
      code: "target_below_min",
      tag: TEXT_TARGET_CHARS_PER_ITEM_TAG,
      message: `"${TEXT_TARGET_CHARS_PER_ITEM_TAG}" must be at least "${TEXT_MIN_CHARS_PER_ITEM_TAG}".`,
    });
  }
  // Strict min <= max ranges.
  if (minItems !== undefined && maxItems !== undefined && minItems > maxItems) {
    issues.push({
      code: "min_exceeds_max",
      tag: TEXT_MIN_ITEMS_TAG,
      message: `"${TEXT_MIN_ITEMS_TAG}" must not exceed "${TEXT_MAX_ITEMS_TAG}".`,
    });
  }
  if (minPerItem !== undefined && maxPerItem !== undefined && minPerItem > maxPerItem) {
    issues.push({
      code: "min_exceeds_max",
      tag: TEXT_MIN_CHARS_PER_ITEM_TAG,
      message: `"${TEXT_MIN_CHARS_PER_ITEM_TAG}" must not exceed "${TEXT_MAX_CHARS_PER_ITEM_TAG}".`,
    });
  }
  // plain text is exactly one item, so its counts are pinned to 1 and a preferred
  // item count is meaningless.
  if (tags[TEXT_FORMAT_TAG] === PLAIN_TEXT_FORMAT) {
    if (minItems !== undefined && minItems !== 1) issues.push(plainSingleItem(TEXT_MIN_ITEMS_TAG));
    if (maxItems !== undefined && maxItems !== 1) issues.push(plainSingleItem(TEXT_MAX_ITEMS_TAG));
    if (targetItems !== undefined) {
      issues.push({
        code: "plain_forbids_target_items",
        tag: TEXT_TARGET_ITEMS_TAG,
        message: `"${TEXT_TARGET_ITEMS_TAG}" is not valid for plain text, which is always one item.`,
      });
    }
  }
  return issues;
}

function plainSingleItem(tag: string): ComponentSemanticIssue {
  return { code: "plain_requires_single_item", tag, message: `"${tag}" must be 1 for plain text.` };
}

function isPositiveIntegerString(value: string | undefined): boolean {
  if (typeof value !== "string") return false;
  const trimmed = value.trim();
  return /^\d+$/.test(trimmed) && Number(trimmed) >= 1;
}

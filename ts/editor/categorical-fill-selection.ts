import { componentMetadata } from "../../generated/ts/components/componentMetadata.js";
import type { ClassificationScheme } from "./classification-schemes.js";

export const FILL_MODE_TAG = "efficio_fill_mode";
export const FILL_SELECTION_TAG = "efficio_fill_selection";
export const SELECTION_ITEM_ID_TAG = "efficio_selection_item_id";

export type CategoricalFillMode = "classification" | "selection";

export type CategoricalSelectionItem = {
  item_id: string;
  label: string;
  instruction?: string;
};

export type CategoricalFillSelection = {
  selected_case_id: string;
  unselected_case_id: string;
  items: readonly CategoricalSelectionItem[];
};

export class CategoricalFillSelectionError extends Error {
  override readonly name = "CategoricalFillSelectionError";
}

const definition = componentMetadata.categorical_fill.tags.efficio_fill_selection.schema;
const itemDefinition = definition.properties.items;
const idPattern = new RegExp(itemDefinition.items.properties.item_id.pattern);

export function resolveCategoricalFillMode(
  tags: Readonly<Record<string, string>>,
): CategoricalFillMode {
  const mode = tags[FILL_MODE_TAG] ?? "classification";
  if (mode !== "classification" && mode !== "selection") {
    throw invalidSelection("Fill mode must be classification or selection.");
  }
  return mode;
}

export function resolveCategoricalFillSelection(
  tags: Readonly<Record<string, string>>,
  scheme: ClassificationScheme,
): CategoricalFillSelection | undefined {
  const raw = tags[FILL_SELECTION_TAG];
  if (resolveCategoricalFillMode(tags) === "classification") {
    if (raw !== undefined) throw invalidSelection("Classification mode must not declare fill selection.");
    return undefined;
  }
  if (typeof raw !== "string") throw invalidSelection("Selection mode requires fill selection configuration.");
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw) as unknown;
  } catch {
    throw invalidSelection("Fill selection must contain valid JSON.");
  }
  if (!isClosedObject(parsed, ["selected_case_id", "unselected_case_id", "items"])) {
    throw invalidSelection();
  }
  const selected = requiredText(parsed.selected_case_id, definition.properties.selected_case_id.maxLength, idPattern);
  const unselected = requiredText(parsed.unselected_case_id, definition.properties.unselected_case_id.maxLength, idPattern);
  const cases = new Set(scheme.cases.map((item) => item.case_id));
  if (selected === unselected || scheme.cases.length !== 2 || cases.size !== 2 || !cases.has(selected) || !cases.has(unselected)) {
    throw invalidSelection("Selection requires exactly its distinct selected and unselected cases.");
  }
  if (!Array.isArray(parsed.items) || parsed.items.length < itemDefinition.minItems || parsed.items.length > itemDefinition.maxItems) {
    throw invalidSelection();
  }
  const items = parsed.items.map(parseItem);
  if (new Set(items.map((item) => item.item_id)).size !== items.length) {
    throw invalidSelection("Selection item IDs must be unique.");
  }
  return { selected_case_id: selected, unselected_case_id: unselected, items };
}

function parseItem(value: unknown): CategoricalSelectionItem {
  if (!isClosedObject(value, ["item_id", "label"], ["instruction"])) throw invalidSelection();
  const properties = itemDefinition.items.properties;
  return {
    item_id: requiredText(value.item_id, properties.item_id.maxLength, idPattern),
    label: requiredText(value.label, properties.label.maxLength),
    ...(value.instruction === undefined ? {} : { instruction: requiredText(value.instruction, properties.instruction.maxLength) }),
  };
}

function requiredText(value: unknown, maximum: number, pattern?: RegExp): string {
  if (typeof value !== "string" || !value.trim() || value.length > maximum || (pattern && value.match(pattern)?.[0] !== value)) {
    throw invalidSelection();
  }
  return pattern ? value : value.trim();
}

function isClosedObject(
  value: unknown, required: readonly string[], optional: readonly string[] = [],
): value is Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return required.every((key) => keys.includes(key)) && keys.every((key) => required.includes(key) || optional.includes(key));
}

function invalidSelection(message = "Fill selection does not match its tag contract."): CategoricalFillSelectionError {
  return new CategoricalFillSelectionError(message);
}

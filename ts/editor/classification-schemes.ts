import { deckTagSchema } from "../../generated/ts/presentation/deckTagSchema.js";

export const CLASSIFICATION_SCHEMES_TAG = "efficio_classification_schemes";
export const CLASSIFICATION_SCHEME_ID_TAG = "efficio_classification_scheme_id";

export type ClassificationPaletteMode = "rgb";

export type ClassificationFill = {
  value: string;
};

export type ClassificationCase = {
  case_id: string;
  label: string;
  description: string;
  fill: ClassificationFill;
};

export type ClassificationScheme = {
  scheme_id: string;
  instruction: string;
  palette_mode: ClassificationPaletteMode;
  cases: readonly ClassificationCase[];
};

export class ClassificationSchemeContractError extends Error {
  override readonly name = "ClassificationSchemeContractError";
}

const definition = deckTagSchema.tags.efficio_classification_schemes.schema;
const schemeDefinition = definition.items;
const caseDefinition = schemeDefinition.properties.cases;
const idPattern = new RegExp(schemeDefinition.properties.scheme_id.pattern);
const rgbPattern = new RegExp(
  caseDefinition.items.properties.fill.properties.value.pattern
);

export function parseClassificationSchemes(
  rawValue: string | readonly unknown[] | undefined
): readonly ClassificationScheme[] {
  if (rawValue === undefined || (typeof rawValue === "string" && rawValue.trim() === "")) {
    return [];
  }
  const parsed = decodeValue(rawValue);
  if (!Array.isArray(parsed) || parsed.length > definition.maxItems) {
    throw invalidSchemes();
  }

  const schemes = parsed.map(parseScheme);
  requireUnique(schemes.map((scheme) => scheme.scheme_id), "scheme IDs");
  return schemes;
}

export function resolveCategoricalFillScheme(
  componentTags: Readonly<Record<string, string>>,
  deckTags: Readonly<Record<string, string>>
): ClassificationScheme {
  const schemeId = componentTags[CLASSIFICATION_SCHEME_ID_TAG]?.trim();
  if (!schemeId) {
    throw new ClassificationSchemeContractError(
      `Categorical-fill components require ${CLASSIFICATION_SCHEME_ID_TAG}.`
    );
  }
  const scheme = parseClassificationSchemes(deckTags[CLASSIFICATION_SCHEMES_TAG]).find(
    (candidate) => candidate.scheme_id === schemeId
  );
  if (!scheme) {
    throw new ClassificationSchemeContractError(
      "The categorical-fill component references an unknown classification scheme."
    );
  }
  return scheme;
}

function decodeValue(rawValue: string | readonly unknown[]): unknown {
  if (typeof rawValue !== "string") return rawValue;
  try {
    return JSON.parse(rawValue) as unknown;
  } catch {
    throw new ClassificationSchemeContractError(
      "Classification schemes must contain valid JSON."
    );
  }
}

function parseScheme(value: unknown): ClassificationScheme {
  if (!isExactObject(value, ["scheme_id", "instruction", "palette_mode", "cases"])) {
    throw invalidSchemes();
  }
  const schemeId = requiredText(value.scheme_id, 120, idPattern);
  const instruction = requiredText(value.instruction, 2000);
  if (value.palette_mode !== "rgb" || !Array.isArray(value.cases)) {
    throw invalidSchemes();
  }
  if (
    value.cases.length < caseDefinition.minItems ||
    value.cases.length > caseDefinition.maxItems
  ) {
    throw invalidSchemes();
  }
  const cases = value.cases.map(parseCase);
  requireUnique(cases.map((item) => item.case_id), `case IDs in ${schemeId}`);
  return {
    scheme_id: schemeId,
    instruction,
    palette_mode: "rgb",
    cases,
  };
}

function parseCase(value: unknown): ClassificationCase {
  if (!isExactObject(value, ["case_id", "label", "description", "fill"])) {
    throw invalidSchemes();
  }
  if (!isExactObject(value.fill, ["value"])) {
    throw invalidSchemes();
  }
  const fillValue = requiredText(value.fill.value, 6, rgbPattern);
  return {
    case_id: requiredText(value.case_id, 120, idPattern),
    label: requiredText(value.label, 120),
    description: requiredText(value.description, 1000),
    fill: { value: fillValue },
  };
}

function requiredText(value: unknown, maximum: number, pattern?: RegExp): string {
  if (
    typeof value !== "string" ||
    value.trim() === "" ||
    [...value].length > maximum ||
    (pattern !== undefined && !pattern.test(value))
  ) {
    throw invalidSchemes();
  }
  return value.trim();
}

function isExactObject(
  value: unknown,
  keys: readonly string[]
): value is Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
}

function requireUnique(values: readonly string[], subject: string): void {
  if (new Set(values).size !== values.length) {
    throw new ClassificationSchemeContractError(`Classification ${subject} must be unique.`);
  }
}

function invalidSchemes(): ClassificationSchemeContractError {
  return new ClassificationSchemeContractError(
    "Classification schemes do not match the deck tag contract."
  );
}

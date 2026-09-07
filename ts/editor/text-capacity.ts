export type TextCapacity = {
  max_lines?: number;
  estimated_chars_per_line?: number;
  min_items: number;
  max_items?: number;
  target_items?: number;
};

export type TextCapacityField = keyof TextCapacity;

export type TextCapacityIssue = {
  code: string;
  field: TextCapacityField;
  message: string;
};

export type TextCapacityFormat = "plain" | "multi_item";

export function validateTextCapacity(
  capacity: TextCapacity,
  textFormat: TextCapacityFormat
): TextCapacityIssue[] {
  const issues: TextCapacityIssue[] = [];

  const fields: readonly TextCapacityField[] = [
    "min_items",
    ...(capacity.max_lines === undefined ? [] : (["max_lines"] as const)),
    ...(capacity.estimated_chars_per_line === undefined
      ? []
      : (["estimated_chars_per_line"] as const)),
    ...(capacity.max_items === undefined ? [] : (["max_items"] as const)),
    ...(capacity.target_items === undefined ? [] : (["target_items"] as const)),
  ];
  const validFields = new Set<TextCapacityField>();
  for (const field of fields) {
    const value = capacity[field];
    if (typeof value === "number" && Number.isInteger(value) && value >= 1) {
      validFields.add(field);
      continue;
    }
    issues.push({
      code: "invalid_positive_integer",
      field,
      message: `${field} must be a positive integer.`,
    });
  }

  const hasLines = capacity.max_lines !== undefined;
  const hasWidth = capacity.estimated_chars_per_line !== undefined;
  if (hasLines !== hasWidth) {
    const field = hasLines ? "estimated_chars_per_line" : "max_lines";
    issues.push({
      code: "incomplete_line_capacity",
      field,
      message: "max_lines and estimated_chars_per_line must be provided together.",
    });
  }

  const maximum = textFormat === "plain" ? 1 : capacity.max_items ?? capacity.max_lines;

  if (
    validFields.has("min_items") &&
    maximum !== undefined &&
    capacity.min_items > maximum
  ) {
    issues.push({
      code: "min_exceeds_max",
      field: "min_items",
      message: "min_items must not exceed max_items.",
    });
  }
  if (
    capacity.max_items !== undefined &&
    capacity.max_lines !== undefined &&
    validFields.has("max_items") &&
    validFields.has("max_lines") &&
    capacity.max_items > capacity.max_lines
  ) {
    issues.push({
      code: "items_exceed_line_capacity",
      field: "max_items",
      message: "max_items must not exceed max_lines because every item consumes a line.",
    });
  }
  if (
    validFields.has("target_items") &&
    validFields.has("min_items") &&
    capacity.target_items !== undefined &&
    capacity.target_items < capacity.min_items
  ) {
    issues.push({
      code: "target_below_min",
      field: "target_items",
      message: "target_items must be at least min_items.",
    });
  }
  if (
    validFields.has("target_items") &&
    maximum !== undefined &&
    capacity.target_items !== undefined &&
    capacity.target_items > maximum
  ) {
    issues.push({
      code: "target_exceeds_max",
      field: "target_items",
      message: "target_items must not exceed max_items.",
    });
  }

  if (textFormat === "plain") {
    if (validFields.has("min_items") && capacity.min_items !== 1) {
      issues.push(plainSingleItem("min_items"));
    }
    if (
      validFields.has("max_items") &&
      capacity.max_items !== undefined &&
      capacity.max_items !== 1
    ) {
      issues.push(plainSingleItem("max_items"));
    }
    if (validFields.has("target_items")) {
      issues.push({
        code: "plain_forbids_target_items",
        field: "target_items",
        message: "target_items is not valid for plain text, which is always one item.",
      });
    }
  }

  return issues;
}

export function estimateTextLineUse(
  items: readonly string[],
  estimatedCharsPerLine: number
): number {
  if (!Number.isInteger(estimatedCharsPerLine) || estimatedCharsPerLine < 1) {
    throw new RangeError("estimatedCharsPerLine must be a positive integer.");
  }

  return items.reduce((total, item) => {
    const normalized = item.replace(/\r\n?/g, "\n");
    return (
      total +
      normalized
        .split("\n")
        .reduce(
          (itemLines, line) =>
            itemLines + Math.max(1, Math.ceil(Array.from(line).length / estimatedCharsPerLine)),
          0
        )
    );
  }, 0);
}

function plainSingleItem(field: "min_items" | "max_items"): TextCapacityIssue {
  return {
    code: "plain_requires_single_item",
    field,
    message: `${field} must be 1 for plain text.`,
  };
}

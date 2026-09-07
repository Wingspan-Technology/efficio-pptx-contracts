export const componentTypes = [
  "categorical_fill",
  "category_chart",
  "table",
  "text"
] as const;
export type ComponentType = (typeof componentTypes)[number];

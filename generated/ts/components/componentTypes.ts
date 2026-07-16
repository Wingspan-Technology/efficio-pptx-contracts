export const componentTypes = [
  "category_chart",
  "table",
  "text"
] as const;
export type ComponentType = (typeof componentTypes)[number];

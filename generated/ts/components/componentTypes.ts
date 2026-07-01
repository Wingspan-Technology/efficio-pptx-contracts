export const componentTypes = [
  "approval_block",
  "grouped_checklist_table",
  "table",
  "text"
] as const;
export type ComponentType = (typeof componentTypes)[number];

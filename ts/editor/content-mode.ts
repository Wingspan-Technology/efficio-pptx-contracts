export const CONTENT_MODE_TAG = "efficio_content_mode";
export const LEGACY_RENDER_BEHAVIOR_TAG = "efficio_render_behavior";
export const CONTENT_MODES = ["ai_generated", "data_bound", "preserve", "remove"] as const;
export type ContentMode = (typeof CONTENT_MODES)[number];

export class ContentModeError extends Error {
  override readonly name = "ContentModeError";
}

const legacyModes: Readonly<Record<string, ContentMode>> = {
  render_by_component_type: "ai_generated",
  preserve: "preserve",
  remove_on_render: "remove",
};

export function resolveContentMode(tags: Readonly<Record<string, string>>): ContentMode | undefined {
  const currentRaw = tags[CONTENT_MODE_TAG];
  const legacyRaw = tags[LEGACY_RENDER_BEHAVIOR_TAG];
  const current = currentRaw === undefined ? undefined : parseCurrentMode(currentRaw);
  const legacy = legacyRaw === undefined ? undefined : parseLegacyMode(legacyRaw);
  if (current !== undefined && legacy !== undefined && current !== legacy) {
    throw new ContentModeError("Current and legacy component content modes conflict.");
  }
  return current ?? legacy;
}

export function isAiFacing(tags: Readonly<Record<string, string>>): boolean {
  return resolveContentMode(tags) === "ai_generated";
}

export function isDataBound(tags: Readonly<Record<string, string>>): boolean {
  return resolveContentMode(tags) === "data_bound";
}

export function isRenderable(tags: Readonly<Record<string, string>>): boolean {
  const mode = resolveContentMode(tags);
  return mode === "ai_generated" || mode === "data_bound";
}

function parseCurrentMode(value: string): ContentMode {
  if ((CONTENT_MODES as readonly string[]).includes(value)) return value as ContentMode;
  throw new ContentModeError(`Unsupported ${CONTENT_MODE_TAG} value.`);
}

function parseLegacyMode(value: string): ContentMode {
  const mode = legacyModes[value];
  if (mode !== undefined) return mode;
  throw new ContentModeError(`Unsupported ${LEGACY_RENDER_BEHAVIOR_TAG} value.`);
}

import { describe, expect, it } from "vitest";

import {
  CONTENT_MODES,
  ContentModeError,
  isAiFacing,
  isDataBound,
  isRenderable,
  resolveContentMode,
} from "../ts/editor";

describe("content mode compatibility", () => {
  it("exports the current modes and classifiers", () => {
    expect(CONTENT_MODES).toEqual(["ai_generated", "data_bound", "preserve", "remove"]);
    expect(isAiFacing({ efficio_content_mode: "ai_generated" })).toBe(true);
    expect(isDataBound({ efficio_content_mode: "data_bound" })).toBe(true);
    expect(isRenderable({ efficio_content_mode: "data_bound" })).toBe(true);
    expect(isRenderable({ efficio_content_mode: "preserve" })).toBe(false);
  });

  it("maps only exact legacy values and prefers an equivalent current tag", () => {
    expect(resolveContentMode({ efficio_render_behavior: "render_by_component_type" }))
      .toBe("ai_generated");
    expect(
      resolveContentMode({
        efficio_content_mode: "preserve",
        efficio_render_behavior: "preserve",
      }),
    ).toBe("preserve");
    expect(() => resolveContentMode({ efficio_render_behavior: "unknown" }))
      .toThrow(ContentModeError);
  });

  it("rejects conflicting current and legacy tags", () => {
    expect(() =>
      resolveContentMode({
        efficio_content_mode: "remove",
        efficio_render_behavior: "render_by_component_type",
      }),
    ).toThrow("conflict");
  });
});

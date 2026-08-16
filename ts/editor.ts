// Handwritten TypeScript SDK entrypoint for the Office editor.
//
// Apps import `@wingspan-technology/efficio-pptx-contracts/editor` instead of
// generated file paths; the generated TS under `generated/ts/*` stays a package
// internal. This module is a thin barrel that re-exports the SDK's public
// surface from focused internal modules under `./editor/`.
//
// Imports are extensionless to match the generated TS and the editor's bundler resolution; this file is
// type-checked by the editor's tsc, like generated TS.

export * from "./editor/component-metadata.js";
export * from "./editor/text-sizing-semantics.js";
export * from "./editor/table-config-semantics.js";
export * from "./editor/slide-deck-contracts.js";

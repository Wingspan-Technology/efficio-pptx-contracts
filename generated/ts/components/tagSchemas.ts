import type { ComponentType } from "./componentTypes";

export const tagSchemas = {
  "category_chart": {
    "generated_from": [
      "contracts/shared/render-behavior-tags.contract.json",
      "contracts/shared/component-base-tags.contract.json",
      "contracts/components/category_chart/tags.contract.json"
    ],
    "component_type": "category_chart",
    "description": "Category chart component tag contract. Flat tags define the chart to generate: its chart type, whether categories and series are fixed (labels/names supplied here) or AI-generated, count boundaries and targets, value formatting, and optional per-axis authoring guidance. There is no config object tag. Chart-shape validation, workbook data, and rendering are out of scope for this contract.",
    "required_tags": [
      "efficio_render_behavior",
      "efficio_component_id",
      "efficio_component_type",
      "efficio_chart_type",
      "efficio_category_mode",
      "efficio_min_categories",
      "efficio_max_categories",
      "efficio_target_categories",
      "efficio_series_mode",
      "efficio_min_series",
      "efficio_max_series",
      "efficio_target_series",
      "efficio_value_type",
      "efficio_allow_negative_values",
      "efficio_allow_decimal_values"
    ],
    "optional_tags": [
      "efficio_content_role",
      "efficio_prompt_instruction",
      "efficio_categories",
      "efficio_category_instruction",
      "efficio_series_names",
      "efficio_series_instruction",
      "efficio_value_unit"
    ],
    "enums": {
      "efficio_render_behavior": [
        "render_by_component_type",
        "preserve",
        "remove_on_render"
      ],
      "efficio_component_type": [
        "category_chart"
      ],
      "efficio_chart_type": [
        "CLUSTERED_COLUMN",
        "STACKED_COLUMN",
        "PERCENTS_STACKED_COLUMN",
        "CLUSTERED_BAR",
        "STACKED_BAR",
        "PERCENTS_STACKED_BAR"
      ],
      "efficio_category_mode": [
        "fixed",
        "ai_generated"
      ],
      "efficio_series_mode": [
        "fixed",
        "ai_generated"
      ],
      "efficio_value_type": [
        "number"
      ],
      "efficio_allow_negative_values": [
        "true",
        "false"
      ],
      "efficio_allow_decimal_values": [
        "true",
        "false"
      ]
    },
    "types": {
      "efficio_render_behavior": "enum",
      "efficio_component_id": "non_empty_string",
      "efficio_component_type": "enum",
      "efficio_content_role": "string",
      "efficio_prompt_instruction": "string",
      "efficio_chart_type": "enum",
      "efficio_category_mode": "enum",
      "efficio_categories": "json_array",
      "efficio_min_categories": "positive_integer_string",
      "efficio_max_categories": "positive_integer_string",
      "efficio_target_categories": "positive_integer_string",
      "efficio_category_instruction": "string",
      "efficio_series_mode": "enum",
      "efficio_series_names": "json_array",
      "efficio_min_series": "positive_integer_string",
      "efficio_max_series": "positive_integer_string",
      "efficio_target_series": "positive_integer_string",
      "efficio_series_instruction": "string",
      "efficio_value_type": "enum",
      "efficio_value_unit": "string",
      "efficio_allow_negative_values": "enum_boolean_string",
      "efficio_allow_decimal_values": "enum_boolean_string"
    },
    "json_schemas": {
      "efficio_categories": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "array",
        "minItems": 1,
        "items": {
          "type": "string",
          "minLength": 1
        }
      },
      "efficio_series_names": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "array",
        "minItems": 1,
        "items": {
          "type": "string",
          "minLength": 1
        }
      }
    },
    "example": {
      "efficio_render_behavior": "render_by_component_type",
      "efficio_component_id": "revenue_chart",
      "efficio_component_type": "category_chart",
      "efficio_content_role": "revenue_by_quarter",
      "efficio_chart_type": "CLUSTERED_COLUMN",
      "efficio_category_mode": "fixed",
      "efficio_categories": "[\"Q1\",\"Q2\",\"Q3\",\"Q4\"]",
      "efficio_min_categories": "4",
      "efficio_max_categories": "4",
      "efficio_target_categories": "4",
      "efficio_series_mode": "ai_generated",
      "efficio_min_series": "1",
      "efficio_max_series": "3",
      "efficio_target_series": "2",
      "efficio_value_type": "number",
      "efficio_allow_negative_values": "false",
      "efficio_allow_decimal_values": "true",
      "efficio_prompt_instruction": "Generate quarterly revenue series for the business units."
    }
  },
  "table": {
    "generated_from": [
      "contracts/shared/render-behavior-tags.contract.json",
      "contracts/shared/component-base-tags.contract.json",
      "contracts/components/table/tags.contract.json"
    ],
    "component_type": "table",
    "description": "Generic table component tag contract. Table-shape-level metadata only: a single object tag describing the table's cells and optional row/column policies. No nested child components.",
    "required_tags": [
      "efficio_render_behavior",
      "efficio_component_id",
      "efficio_component_type",
      "efficio_table_config"
    ],
    "optional_tags": [
      "efficio_content_role",
      "efficio_prompt_instruction"
    ],
    "enums": {
      "efficio_render_behavior": [
        "render_by_component_type",
        "preserve",
        "remove_on_render"
      ],
      "efficio_component_type": [
        "table"
      ]
    },
    "types": {
      "efficio_render_behavior": "enum",
      "efficio_component_id": "non_empty_string",
      "efficio_component_type": "enum",
      "efficio_content_role": "string",
      "efficio_prompt_instruction": "string",
      "efficio_table_config": "json_object"
    },
    "json_schemas": {
      "efficio_table_config": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": false,
        "required": [
          "cells"
        ],
        "properties": {
          "rows": {
            "type": "array",
            "description": "Optional per-row policies, keyed by row index.",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "row"
              ],
              "properties": {
                "row": {
                  "type": "integer",
                  "minimum": 0,
                  "description": "Zero-based row index this policy applies to."
                },
                "content_policy": {
                  "type": "string",
                  "enum": [
                    "required",
                    "optional"
                  ],
                  "default": "required",
                  "description": "Content policy for the row: required means its cells should be filled, optional means they may be filled. Does not control rendering."
                },
                "instruction": {
                  "type": "string",
                  "default": "",
                  "description": "Optional guidance for generating this row's cells."
                }
              }
            }
          },
          "columns": {
            "type": "array",
            "description": "Optional per-column policies, keyed by column index.",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "col"
              ],
              "properties": {
                "col": {
                  "type": "integer",
                  "minimum": 0,
                  "description": "Zero-based column index this policy applies to."
                },
                "content_policy": {
                  "type": "string",
                  "enum": [
                    "required",
                    "optional"
                  ],
                  "default": "required",
                  "description": "Content policy for the column: required means its cells should be filled, optional means they may be filled. Does not control rendering."
                },
                "instruction": {
                  "type": "string",
                  "default": "",
                  "description": "Optional guidance for generating this column's cells."
                }
              }
            }
          },
          "cells": {
            "type": "array",
            "description": "Per-cell configuration. May be empty when no cells are configured (every cell is then preserved / left as authored).",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "row",
                "col"
              ],
              "properties": {
                "row": {
                  "type": "integer",
                  "minimum": 0,
                  "description": "Zero-based row index of the cell."
                },
                "col": {
                  "type": "integer",
                  "minimum": 0,
                  "description": "Zero-based column index of the cell."
                },
                "render_action": {
                  "type": "string",
                  "enum": [
                    "render",
                    "preserve"
                  ],
                  "default": "preserve",
                  "description": "Whether the renderer writes into this cell: render allows AI-provided content to be written, preserve keeps the cell's existing content unchanged. Optional — a missing render_action means preserve."
                },
                "text_format": {
                  "type": "string",
                  "enum": [
                    "plain",
                    "paragraph",
                    "bullets",
                    "numbered_list"
                  ],
                  "default": "plain",
                  "description": "How the generated cell text should be structured."
                },
                "instruction": {
                  "type": "string",
                  "default": "",
                  "description": "Optional guidance for generating this cell's content."
                },
                "max_chars_per_item": {
                  "type": "integer",
                  "minimum": 1,
                  "description": "Maximum characters for each generated line/item in the cell — a strict limit that must never be exceeded; shorten or compact content until it fits."
                },
                "max_lines": {
                  "type": "integer",
                  "minimum": 1,
                  "description": "Maximum number of lines for this cell — a strict limit that must never be exceeded; shorten or compact content until it fits."
                },
                "max_chars_per_line": {
                  "type": "integer",
                  "minimum": 1,
                  "description": "Maximum characters per line for this cell — a strict limit that must never be exceeded; shorten or compact content until it fits."
                }
              }
            }
          }
        }
      }
    },
    "example": {
      "efficio_render_behavior": "render_by_component_type",
      "efficio_component_id": "comparison_table",
      "efficio_component_type": "table",
      "efficio_content_role": "comparison_table",
      "efficio_table_config": "{\"cells\":[{\"row\":0,\"col\":0,\"render_action\":\"preserve\"},{\"row\":1,\"col\":0,\"render_action\":\"render\",\"text_format\":\"bullets\",\"max_lines\":3}]}",
      "efficio_prompt_instruction": "Generate table content that respects each cell's render action."
    }
  },
  "text": {
    "generated_from": [
      "contracts/shared/render-behavior-tags.contract.json",
      "contracts/shared/component-base-tags.contract.json",
      "contracts/components/text/tags.contract.json"
    ],
    "component_type": "text",
    "description": "Text component tag contract.",
    "required_tags": [
      "efficio_render_behavior",
      "efficio_component_id",
      "efficio_component_type",
      "efficio_text_format",
      "efficio_sizing_mode",
      "efficio_max_chars",
      "efficio_min_items",
      "efficio_max_items",
      "efficio_min_chars_per_item",
      "efficio_max_chars_per_item"
    ],
    "optional_tags": [
      "efficio_content_role",
      "efficio_prompt_instruction",
      "efficio_target_chars",
      "efficio_target_chars_per_item"
    ],
    "enums": {
      "efficio_render_behavior": [
        "render_by_component_type",
        "preserve",
        "remove_on_render"
      ],
      "efficio_component_type": [
        "text"
      ],
      "efficio_text_format": [
        "plain",
        "paragraph",
        "bullets",
        "numbered_list"
      ],
      "efficio_sizing_mode": [
        "auto",
        "manual"
      ]
    },
    "types": {
      "efficio_render_behavior": "enum",
      "efficio_component_id": "non_empty_string",
      "efficio_component_type": "enum",
      "efficio_content_role": "string",
      "efficio_prompt_instruction": "string",
      "efficio_text_format": "enum",
      "efficio_sizing_mode": "enum",
      "efficio_max_chars": "positive_integer_string",
      "efficio_target_chars": "positive_integer_string",
      "efficio_min_items": "positive_integer_string",
      "efficio_max_items": "positive_integer_string",
      "efficio_min_chars_per_item": "positive_integer_string",
      "efficio_max_chars_per_item": "positive_integer_string",
      "efficio_target_chars_per_item": "positive_integer_string"
    },
    "json_schemas": {},
    "example": {
      "efficio_render_behavior": "render_by_component_type",
      "efficio_component_id": "title",
      "efficio_component_type": "text",
      "efficio_content_role": "slide_title",
      "efficio_text_format": "plain",
      "efficio_sizing_mode": "auto",
      "efficio_max_chars": "120",
      "efficio_target_chars": "90",
      "efficio_min_items": "1",
      "efficio_max_items": "3",
      "efficio_min_chars_per_item": "5",
      "efficio_max_chars_per_item": "48",
      "efficio_target_chars_per_item": "36",
      "efficio_prompt_instruction": "Generate a concise executive slide title."
    }
  }
} as const;

export type TagSchema = (typeof tagSchemas)[ComponentType];

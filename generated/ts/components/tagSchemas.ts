import type { ComponentType } from "./componentTypes";

export const tagSchemas = {
  "approval_block": {
    "generated_from": [
      "contracts/shared/render-behavior-tags.contract.json",
      "contracts/shared/component-base-tags.contract.json",
      "contracts/components/approval_block/tags.contract.json"
    ],
    "component_type": "approval_block",
    "description": "Approval / sign-off block component. Table-backed but semantically approval-specific: a person + role pair with an approval subtype (recommended/endorsed/approved). Cell tags map the semantic slots onto an existing table shape.",
    "required_tags": [
      "efficio_render_behavior",
      "efficio_component_id",
      "efficio_component_type",
      "efficio_manually_reviewed",
      "efficio_approval_block_layout",
      "efficio_label_cell",
      "efficio_name_cell",
      "efficio_role_cell",
      "efficio_default_subtype",
      "efficio_subtype_policy",
      "efficio_missing_content_behavior",
      "efficio_approval_block_subtypes"
    ],
    "optional_tags": [
      "efficio_content_role",
      "efficio_prompt_instruction",
      "efficio_requires_manual_review"
    ],
    "enums": {
      "efficio_render_behavior": [
        "render_by_component_type",
        "preserve",
        "remove_on_render"
      ],
      "efficio_manually_reviewed": [
        "true",
        "false"
      ],
      "efficio_requires_manual_review": [
        "true",
        "false"
      ],
      "efficio_component_type": [
        "approval_block"
      ],
      "efficio_approval_block_layout": [
        "table_2row_person_role"
      ],
      "efficio_default_subtype": [
        "recommended",
        "endorsed",
        "approved"
      ],
      "efficio_subtype_policy": [
        "ai_selectable"
      ],
      "efficio_missing_content_behavior": [
        "leave_as_is"
      ]
    },
    "types": {
      "efficio_render_behavior": "enum",
      "efficio_component_id": "non_empty_string",
      "efficio_component_type": "enum",
      "efficio_content_role": "string",
      "efficio_prompt_instruction": "string",
      "efficio_manually_reviewed": "enum_boolean_string",
      "efficio_requires_manual_review": "enum_boolean_string",
      "efficio_approval_block_layout": "enum",
      "efficio_label_cell": "json_object",
      "efficio_name_cell": "json_object",
      "efficio_role_cell": "json_object",
      "efficio_default_subtype": "enum",
      "efficio_subtype_policy": "enum",
      "efficio_missing_content_behavior": "enum",
      "efficio_approval_block_subtypes": "json_object"
    },
    "json_schemas": {
      "efficio_label_cell": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
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
            "maximum": 1,
            "description": "Zero-based table row."
          },
          "col": {
            "type": "integer",
            "minimum": 0,
            "maximum": 1,
            "description": "Zero-based table column."
          }
        }
      },
      "efficio_name_cell": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
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
            "maximum": 1,
            "description": "Zero-based table row."
          },
          "col": {
            "type": "integer",
            "minimum": 0,
            "maximum": 1,
            "description": "Zero-based table column."
          }
        }
      },
      "efficio_role_cell": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
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
            "maximum": 1,
            "description": "Zero-based table row."
          },
          "col": {
            "type": "integer",
            "minimum": 0,
            "maximum": 1,
            "description": "Zero-based table column."
          }
        }
      },
      "efficio_approval_block_subtypes": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": false,
        "required": [
          "recommended",
          "endorsed",
          "approved"
        ],
        "properties": {
          "recommended": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "label"
            ],
            "properties": {
              "label": {
                "type": "string",
                "minLength": 1
              }
            }
          },
          "endorsed": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "label"
            ],
            "properties": {
              "label": {
                "type": "string",
                "minLength": 1
              }
            }
          },
          "approved": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "label"
            ],
            "properties": {
              "label": {
                "type": "string",
                "minLength": 1
              }
            }
          }
        }
      }
    },
    "example": {
      "efficio_render_behavior": "render_by_component_type",
      "efficio_component_id": "approval_1",
      "efficio_component_type": "approval_block",
      "efficio_content_role": "approval_signoff",
      "efficio_approval_block_layout": "table_2row_person_role",
      "efficio_label_cell": "{\"row\":0,\"col\":0}",
      "efficio_name_cell": "{\"row\":0,\"col\":1}",
      "efficio_role_cell": "{\"row\":1,\"col\":1}",
      "efficio_default_subtype": "approved",
      "efficio_subtype_policy": "ai_selectable",
      "efficio_missing_content_behavior": "leave_as_is",
      "efficio_approval_block_subtypes": "{\"recommended\":{\"label\":\"Recommended\"},\"endorsed\":{\"label\":\"Endorsed\"},\"approved\":{\"label\":\"Approved\"}}",
      "efficio_manually_reviewed": "false"
    }
  },
  "grouped_checklist_table": {
    "generated_from": [
      "contracts/shared/render-behavior-tags.contract.json",
      "contracts/shared/component-base-tags.contract.json",
      "contracts/components/grouped_checklist_table/tags.contract.json"
    ],
    "component_type": "grouped_checklist_table",
    "description": "Grouped checklist table component tag contract. Table-shape-level metadata only: no cell, row, or slot tags and no nested child components.",
    "required_tags": [
      "efficio_render_behavior",
      "efficio_component_id",
      "efficio_component_type",
      "efficio_manually_reviewed",
      "efficio_groups"
    ],
    "optional_tags": [
      "efficio_content_role",
      "efficio_prompt_instruction",
      "efficio_requires_manual_review"
    ],
    "enums": {
      "efficio_render_behavior": [
        "render_by_component_type",
        "preserve",
        "remove_on_render"
      ],
      "efficio_manually_reviewed": [
        "true",
        "false"
      ],
      "efficio_requires_manual_review": [
        "true",
        "false"
      ],
      "efficio_component_type": [
        "grouped_checklist_table"
      ]
    },
    "types": {
      "efficio_render_behavior": "enum",
      "efficio_component_id": "non_empty_string",
      "efficio_component_type": "enum",
      "efficio_content_role": "string",
      "efficio_prompt_instruction": "string",
      "efficio_manually_reviewed": "enum_boolean_string",
      "efficio_requires_manual_review": "enum_boolean_string",
      "efficio_groups": "json_object"
    },
    "json_schemas": {
      "efficio_groups": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": false,
        "required": [
          "groups"
        ],
        "properties": {
          "groups": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "key",
                "label",
                "inclusion_policy"
              ],
              "properties": {
                "key": {
                  "type": "string",
                  "minLength": 1,
                  "description": "Stable identifier for the group within the table."
                },
                "label": {
                  "type": "string",
                  "minLength": 1,
                  "description": "Human-readable group heading."
                },
                "inclusion_policy": {
                  "type": "string",
                  "enum": [
                    "always",
                    "prefer_keep",
                    "when_relevant",
                    "prefer_drop",
                    "never"
                  ],
                  "description": "How strongly this group should be kept when generating content."
                },
                "min_items": {
                  "type": "integer",
                  "minimum": 1,
                  "description": "Minimum number of items this group should contain when generated."
                },
                "max_items": {
                  "type": "integer",
                  "minimum": 1,
                  "description": "Maximum number of items this group should contain when generated."
                },
                "max_chars_per_item": {
                  "type": "integer",
                  "minimum": 1,
                  "description": "Suggested maximum characters for each generated item — a sizing hint for generation, not a hard limit."
                },
                "prompt_instruction": {
                  "type": "string",
                  "minLength": 1,
                  "description": "Optional per-group guidance for generating this group's items."
                },
                "suggested_items": {
                  "type": "array",
                  "items": {
                    "type": "string",
                    "minLength": 1
                  },
                  "description": "Optional author-provided example items for the group."
                }
              }
            }
          }
        }
      }
    },
    "example": {
      "efficio_render_behavior": "render_by_component_type",
      "efficio_component_id": "action_groups",
      "efficio_component_type": "grouped_checklist_table",
      "efficio_content_role": "action_table",
      "efficio_groups": "{\"groups\":[{\"key\":\"now\",\"label\":\"Do now\",\"inclusion_policy\":\"always\",\"suggested_items\":[\"Confirm scope\"]},{\"key\":\"next\",\"label\":\"Do next\",\"inclusion_policy\":\"when_relevant\"}]}",
      "efficio_prompt_instruction": "Generate grouped action items that respect each group's inclusion policy.",
      "efficio_manually_reviewed": "false"
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
      "efficio_manually_reviewed",
      "efficio_table_config"
    ],
    "optional_tags": [
      "efficio_content_role",
      "efficio_prompt_instruction",
      "efficio_requires_manual_review"
    ],
    "enums": {
      "efficio_render_behavior": [
        "render_by_component_type",
        "preserve",
        "remove_on_render"
      ],
      "efficio_manually_reviewed": [
        "true",
        "false"
      ],
      "efficio_requires_manual_review": [
        "true",
        "false"
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
      "efficio_manually_reviewed": "enum_boolean_string",
      "efficio_requires_manual_review": "enum_boolean_string",
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
                "behavior": {
                  "type": "string",
                  "enum": [
                    "static",
                    "required",
                    "optional"
                  ],
                  "default": "required",
                  "description": "Generation policy for the row: static keeps existing content, required must be generated, optional may be generated."
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
                "behavior": {
                  "type": "string",
                  "enum": [
                    "static",
                    "required",
                    "optional"
                  ],
                  "default": "required",
                  "description": "Generation policy for the column: static keeps existing content, required must be generated, optional may be generated."
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
            "description": "Per-cell configuration. May be empty when no cells are configured (every cell is then left as authored / static).",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "row",
                "col",
                "behavior"
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
                "behavior": {
                  "type": "string",
                  "enum": [
                    "static",
                    "required",
                    "optional"
                  ],
                  "description": "Generation policy for the cell: static keeps existing content, required must be generated, optional may be generated."
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
                  "description": "Suggested maximum characters for each generated line/item in the cell — a sizing hint, not a hard limit."
                },
                "max_lines": {
                  "type": "integer",
                  "minimum": 1,
                  "description": "Suggested maximum number of lines for this cell — a sizing hint, not a hard limit."
                },
                "max_chars_per_line": {
                  "type": "integer",
                  "minimum": 1,
                  "description": "Suggested maximum characters per line for this cell — a sizing hint, not a hard limit."
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
      "efficio_table_config": "{\"cells\":[{\"row\":0,\"col\":0,\"behavior\":\"static\"},{\"row\":1,\"col\":0,\"behavior\":\"required\",\"text_format\":\"bullets\",\"max_lines\":3}]}",
      "efficio_prompt_instruction": "Generate table content that respects each cell's behavior.",
      "efficio_manually_reviewed": "false"
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
      "efficio_manually_reviewed",
      "efficio_text_format",
      "efficio_sizing_mode",
      "efficio_max_chars",
      "efficio_max_lines",
      "efficio_max_chars_per_line"
    ],
    "optional_tags": [
      "efficio_content_role",
      "efficio_prompt_instruction",
      "efficio_requires_manual_review"
    ],
    "enums": {
      "efficio_render_behavior": [
        "render_by_component_type",
        "preserve",
        "remove_on_render"
      ],
      "efficio_manually_reviewed": [
        "true",
        "false"
      ],
      "efficio_requires_manual_review": [
        "true",
        "false"
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
      "efficio_manually_reviewed": "enum_boolean_string",
      "efficio_requires_manual_review": "enum_boolean_string",
      "efficio_text_format": "enum",
      "efficio_sizing_mode": "enum",
      "efficio_max_chars": "positive_integer_string",
      "efficio_max_lines": "positive_integer_string",
      "efficio_max_chars_per_line": "positive_integer_string"
    },
    "json_schemas": {},
    "example": {
      "efficio_render_behavior": "render_by_component_type",
      "efficio_component_id": "title",
      "efficio_component_type": "text",
      "efficio_content_role": "slide_title",
      "efficio_text_format": "plain",
      "efficio_sizing_mode": "auto",
      "efficio_max_chars": "30",
      "efficio_max_lines": "30",
      "efficio_max_chars_per_line": "30",
      "efficio_prompt_instruction": "Generate a concise executive slide title.",
      "efficio_manually_reviewed": "true"
    }
  }
} as const;

export type TagSchema = (typeof tagSchemas)[ComponentType];

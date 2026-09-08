import path from "node:path";

import {
  assertEfficioTagNames,
  assertNoDefaults,
  assertObject,
  getRecord,
  publicTagAlias,
  validateTagEntityContract,
  type JsonObject,
} from "./contractLib.js";
import { readJson } from "./generatorIo.js";
import { sharedDir } from "./generatorPaths.js";

export const textCapacityContractName = "text-capacity-tags.contract.json";
export const textCapacityContractLabel = `contracts/shared/${textCapacityContractName}`;

const CAPACITY_TAGS = [
  "efficio_max_lines",
  "efficio_estimated_chars_per_line",
  "efficio_min_chars",
  "efficio_max_chars",
  "efficio_min_items",
  "efficio_max_items",
  "efficio_min_chars_per_item",
  "efficio_max_chars_per_item",
  "efficio_target_items",
] as const;

export async function loadTextCapacityTagContract(
  root = sharedDir,
): Promise<JsonObject> {
  const contract = await readJson(path.join(root, textCapacityContractName));
  assertObject(contract, textCapacityContractLabel);
  assertNoDefaults(contract, textCapacityContractLabel);
  validateTagEntityContract(contract, textCapacityContractLabel, {});
  assertEfficioTagNames(contract, textCapacityContractLabel);
  validateCapacityFields(contract);
  return contract;
}

export function composeTextCapacityContract(
  componentType: string,
  componentContract: JsonObject,
  capacityContract: JsonObject,
  label: string,
): JsonObject {
  const composed = structuredClone(componentContract);
  if (componentType === "text") {
    addTextCapacityTags(composed, capacityContract, label);
  } else if (componentType === "table") {
    addTableCellCapacityFields(composed, capacityContract, label);
  }
  return composed;
}

function validateCapacityFields(contract: JsonObject): void {
  const tags = getRecord(contract, "tags");
  if (JSON.stringify(Object.keys(tags)) !== JSON.stringify(CAPACITY_TAGS)) {
    throw new Error(
      `${textCapacityContractLabel}.tags must contain exactly ${CAPACITY_TAGS.join(", ")}.`,
    );
  }
  for (const tag of CAPACITY_TAGS) {
    const definition = getRecord(tags, tag);
    const expectedRequired = tag !== "efficio_target_items";
    if (
      definition.type !== "integer" ||
      definition.minimum !== 1 ||
      definition.required !== expectedRequired
    ) {
      throw new Error(
        `${textCapacityContractLabel}.tags.${tag} must be a ${expectedRequired ? "required" : "optional"} positive integer.`,
      );
    }
  }
}

function addTextCapacityTags(
  contract: JsonObject,
  capacityContract: JsonObject,
  label: string,
): void {
  const tags = getRecord(contract, "tags");
  for (const [tag, definition] of Object.entries(getRecord(capacityContract, "tags"))) {
    if (tag in tags) {
      throw new Error(`${label}.tags.${tag} duplicates the shared text-capacity contract.`);
    }
    tags[tag] = structuredClone(definition);
  }
}

function addTableCellCapacityFields(
  contract: JsonObject,
  capacityContract: JsonObject,
  label: string,
): void {
  const tableTag = getRecord(getRecord(contract, "tags"), "efficio_table_config");
  const schema = getRecord(tableTag, "schema");
  const rootProperties = getRecord(schema, "properties");
  const cells = getRecord(rootProperties, "cells");
  const cellItem = getRecord(cells, "items");
  const cellProperties = getRecord(cellItem, "properties");
  if (Object.keys(cellProperties).length === 0) {
    throw new Error(`${label} must declare efficio_table_config cell properties.`);
  }
  for (const [tag, rawDefinition] of Object.entries(getRecord(capacityContract, "tags"))) {
    const field = publicTagAlias(tag);
    if (field in cellProperties) {
      throw new Error(`${label} table cell field ${field} duplicates the shared capacity contract.`);
    }
    const definition = getRecord({ definition: rawDefinition }, "definition");
    const projected: JsonObject = {
      type: definition.type,
      minimum: definition.minimum,
      description: definition.description,
    };
    if (field === "min_items") projected.default = 1;
    cellProperties[field] = projected;
  }
}

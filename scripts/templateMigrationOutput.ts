import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { buildConstSource, writeJson } from "./generatorIo.js";
import {
  generatedPresentationSchemasDir,
  tsPresentationDir,
} from "./generatorPaths.js";
import type { TemplateContractMigrationCatalog } from "./templateMigrationContract.js";

export const TEMPLATE_MIGRATIONS_FILE = "template-contract-migrations.json";

export async function buildTemplateMigrationOutputs(
  catalog: TemplateContractMigrationCatalog,
): Promise<void> {
  await mkdir(generatedPresentationSchemasDir, { recursive: true });
  await writeJson(path.join(generatedPresentationSchemasDir, TEMPLATE_MIGRATIONS_FILE), catalog);
  await mkdir(tsPresentationDir, { recursive: true });
  await writeFile(
    path.join(tsPresentationDir, "templateContractMigrations.ts"),
    buildConstSource("templateContractMigrationCatalog", catalog, [
      "export type TemplateContractMigrationCatalogData = typeof templateContractMigrationCatalog;",
    ]),
  );
}

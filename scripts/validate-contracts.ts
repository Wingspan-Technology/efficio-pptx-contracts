// CLI entrypoint for standalone, pre-import contract validation. Reads and
// validates every authored contract without touching generated outputs. Exits
// non-zero (listing every problem) when validation fails. Pass --quiet to
// suppress the success line.
//
// Usage:  tsx scripts/validate-contracts.ts [--quiet]

import { validateAllContracts } from "./contractValidation.js";

const quiet = process.argv.includes("--quiet");
const report = await validateAllContracts();

if (!report.ok) {
  console.error(`✖ contract validation failed (${report.issues.length} issue(s)):`);
  for (const issue of report.issues) {
    console.error(`  - ${issue.contract}: ${issue.message}`);
  }
  process.exit(1);
}

if (!quiet) {
  console.log(`✓ contracts valid (${report.checked} checks)`);
}

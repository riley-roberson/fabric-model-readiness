/**
 * Runs the docs-site TypeScript rule engine over a model supplied as JSON and
 * prints the resulting findings as JSON.
 *
 * Exists so test_check_parity.py can compare the two rule implementations on
 * identical input. The TS parser is bypassed deliberately -- it depends on the
 * File System Access API, and parser differences are not what this is testing.
 *
 * Usage:  node run_ts_rules.mjs <model.json>
 */
import { build } from "esbuild";
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..", "..", "..", "..");
const rulesEntry = path.join(repoRoot, "docs", "src", "scanner", "rules", "index.ts");

const modelPath = process.argv[2];
if (!modelPath) {
  console.error("usage: node run_ts_rules.mjs <model.json>");
  process.exit(2);
}

const result = await build({
  entryPoints: [rulesEntry],
  bundle: true,
  format: "esm",
  platform: "node",
  write: false,
  logLevel: "silent",
});

// Load the bundle without touching disk.
const dataUrl = "data:text/javascript;base64," +
  Buffer.from(result.outputFiles[0].text).toString("base64");
const rules = await import(dataUrl);

const model = JSON.parse(readFileSync(modelPath, "utf8"));
const findings = rules.runAllChecks(model);

process.stdout.write(JSON.stringify({
  findings: findings.map((f) => ({
    check: f.check,
    category: f.category,
    severity: f.severity,
    object: f.object,
    object_type: f.object_type,
    auto_fixable: f.auto_fixable,
  })),
  check_profiles: rules.CHECK_PROFILES,
}));

import assert from "node:assert/strict";
import { after, test } from "node:test";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join } from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const cache = join(root, "node_modules/.cache");
mkdirSync(cache, { recursive: true });
const output = mkdtempSync(join(cache, "mixer-workspace-binding-"));
after(() => rmSync(output, { recursive: true, force: true }));
try {
  execFileSync(process.execPath, [join(root, "node_modules/typescript/bin/tsc"), "src/state/workspace-binding.ts", "src/state/workspace-creation.ts",
    "--target", "ES2022", "--module", "ESNext", "--moduleResolution", "Bundler", "--strict", "--skipLibCheck",
    "--noUncheckedIndexedAccess", "--exactOptionalPropertyTypes", "--outDir", output], { cwd: root, stdio: "pipe" });
} catch (error) { rmSync(output, { recursive: true, force: true }); throw error; }
writeFileSync(join(output, "package.json"), '{"type":"module"}\n');

test("Solid client owner joins actual workspace client, scoped selection and session/disposal cancellation", () => {
  const environment = { ...process.env,
    MIXER_WORKSPACE_BINDING_MODULE: pathToFileURL(join(output, "state/workspace-binding.js")).href,
    MIXER_WORKSPACE_CREATION_MODULE: pathToFileURL(join(output, "state/workspace-creation.js")).href,
    MIXER_WORKSPACE_CLIENT_MODULE: pathToFileURL(join(output, "api/workspace-client.js")).href };
  // This is a separate child test process with different module conditions.
  delete environment.NODE_TEST_CONTEXT;
  const result = spawnSync(process.execPath, ["--conditions=browser", "--test", join(root, "tests/workspace-binding-runner.mjs")], {
    cwd: root, encoding: "utf8", timeout: 30000,
    env: environment,
  });
  if (result.error) throw result.error;
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /# tests 6\b/);
  assert.match(result.stdout, /# fail 0\b/);
  process.stdout.write(result.stdout);
});

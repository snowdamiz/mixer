import assert from "node:assert/strict";
import { after } from "node:test";
import { execFile, execFileSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const root = fileURLToPath(new URL("../../", import.meta.url));
const execute = promisify(execFile);

export function compileBuildSelectionTests() {
  const cache = join(root, "node_modules/.cache");
  mkdirSync(cache, { recursive: true });
  const output = mkdtempSync(join(cache, "build-selection-compiled-"));
  const cleanup = () => {
    rmSync(output, { recursive: true, force: true });
    assert.equal(existsSync(output), false);
  };
  after(cleanup);
  try {
    execFileSync(process.execPath, [join(root, "node_modules/typescript/bin/tsc"),
      "src/state/build-selection-binding.ts", "src/state/browser-session-controller.ts",
      "src/api/cookie-build-catalog-client.ts", "--target", "ES2022", "--module", "ESNext",
      "--moduleResolution", "Bundler", "--strict", "--skipLibCheck",
      "--noUncheckedIndexedAccess", "--exactOptionalPropertyTypes", "--outDir", output],
    { cwd: root, stdio: "pipe", timeout: 15000 });
    writeFileSync(join(output, "package.json"), '{"type":"module"}\n');
    symlinkSync(join(root, "node_modules"), join(output, "node_modules"), "dir");
    return output;
  } catch (error) {
    if (error.stdout) process.stderr.write(error.stdout);
    if (error.stderr) process.stderr.write(error.stderr);
    cleanup();
    throw error;
  }
}

export function isBrowserTestChild(file) {
  return process.env.MIXER_BUILD_SELECTION_BROWSER_TEST === fileURLToPath(file)
    && process.execArgv.includes("--conditions=browser");
}

export async function runBrowserTests(file, output) {
  const env = { ...process.env, MIXER_BUILD_SELECTION_BROWSER_TEST: fileURLToPath(file),
    MIXER_BUILD_CATALOG_COMPILED: output };
  delete env.NODE_TEST_CONTEXT;
  delete env.NODE_OPTIONS;
  delete env.MIXER_BUILD_CLIENT_COMPILED;
  try {
    const result = await execute(process.execPath,
      ["--conditions=browser", "--test", fileURLToPath(file)],
      { cwd: root, env, detached: false, timeout: 60000, maxBuffer: 2 * 1024 * 1024 });
    process.stdout.write(result.stdout);
    process.stderr.write(result.stderr);
    // A zero exit can mean Node skipped a recursively inherited test context.
    process.stdout.write("BROWSER_CHILD_RAW " + JSON.stringify({ file: fileURLToPath(file), stdout: result.stdout, stderr: result.stderr }) + "\n");
    const cases = {
      "build-selection-controller.test.mjs": [
            "only matching ready workspace pages admit a project; caller IDs cannot fabricate selection",
            "two applications including one empty lead only stored selection into independently checked queued and failed details",
            "applications and build cursors derive from validated current page and clear child selections",
            "all eight detail identity mismatches and same-selection revision rollback fail closed",
            "401,403,404,503 clear applications, build rows and detail, without stale good data",
            "late project, application, client and session responses cannot publish",
            "abort reentry and listener disposal install new ownership before callbacks and prevent dispatch",
            "same project on a new workspace page clears prior details; malformed internal rows cannot become selectable",
            "actual metadata owner yields one frozen bundle whose catalog/read share workspace epoch, 401 and revalidation",
            "new catalog and read delegates enforce synchronous and postawait expiry and backwards clocks",
            "retained request_failed detail retries preserve the accepted floor",
            "security and availability failures erase retained detail retry ownership",
            "catalog failures never retain detail ownership",
            "explicit workspace session application and page resets admit a new revision floor",
            "actual Solid owner catalog and transport preserve revision floor after invalid detail",
            "actual HTTP500 clears retry ownership and explicit workspace reset permits revision3"
      ],
      "build-selection-binding.test.mjs": [
            "actual Solid owner fences reads/actions before effects and disposes owned requests"
      ]
};
    const filename = fileURLToPath(file).split("/").at(-1);
    const names = cases[filename];
    assert(names, "unknown build-selection child test file");
    const lines = result.stdout.split("\n");
    for (const line of [`# tests ${names.length}`, `# pass ${names.length}`,
      "# fail 0", "# cancelled 0", "# skipped 0", "# todo 0"])
      assert(lines.includes(line), `${filename}: missing executed summary ${line}`);
    for (const [index, name] of names.entries()) {
      assert(lines.includes(`# Subtest: ${name}`), `${filename}: missing original case ${name}`);
      assert(lines.includes(`ok ${index + 1} - ${name}`), `${filename}: original case did not pass ${name}`);
    }
    assert(!(result.stdout + result.stderr).includes("skipping running files"), "recursive Node test execution skipped");
    process.stdout.write("BROWSER_CHILD_SUMMARY " + JSON.stringify({ file: filename,
      tests: names.length, pass: names.length, fail: 0, cancelled: 0, skipped: 0, todo: 0,
      names, actualNamedPassed: names.length, childContextRemoved: !("NODE_TEST_CONTEXT" in env) }) + "\n");
  } catch (error) {
    if (error.stdout) process.stdout.write(error.stdout);
    if (error.stderr) process.stderr.write(error.stderr);
    throw error;
  }
}

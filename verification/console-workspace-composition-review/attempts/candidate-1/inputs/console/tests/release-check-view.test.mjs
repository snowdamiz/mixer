import assert from "node:assert/strict";
import { after, test } from "node:test";
import { mkdtemp, mkdir, rm } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join } from "node:path";
import { build } from "vite";

const root = fileURLToPath(new URL("../", import.meta.url));
const cache = join(root, "node_modules/.cache");
await mkdir(cache, { recursive: true });
const output = await mkdtemp(join(cache, "mixer-render-"));
after(() => rm(output, { recursive: true, force: true }));
await build({ root, logLevel: "error", build: {
  ssr: join(root, "tests/render-release-checks.tsx"), outDir: output,
  emptyOutDir: false, minify: false,
} });
const { renderChecks: renderWithMarkers, example } = await import(pathToFileURL(join(output, "render-release-checks.js")));
// Solid SSR hydration comments are not visible text or user data.
const renderChecks = state => renderWithMarkers(state).replace(/<!--[^]*?-->/g, "");

test("the actual Solid view keeps a failed Android target visible beside pending iOS", () => {
  const html = renderChecks(example("failed"));
  assert.match(html, /Checks failed/);
  assert.match(html, /Android target android-build-42/);
  assert.match(html, /check-failed/);
  assert.match(html, /check-pending/);
  assert.equal((html.match(/<tr\b[^>]*class="check-/g) ?? []).length, 6);
  assert.doesNotMatch(html, /Checks passed|<button/);
});

test("stale failures do not describe the current revision; every missing check has a row", () => {
  const html = renderChecks(example("incomplete"));
  assert.match(html, /Checks incomplete/);
  assert.match(html, /Previous revision/);
  assert.match(html, /Previously failed\. Does not cover the selected revision\./);
  assert.match(html, /sample-previous-391dbf0/);
  assert.match(html, /No result received/);
  assert.match(html, /Reported as not run/);
  assert.equal((html.match(/<tr\b[^>]*class="check-/g) ?? []).length, 6);
  assert.doesNotMatch(html, /Checks failed|Checks passed/);
});

test("all current passes describe check completion without granting release approval", () => {
  const html = renderChecks(example("passed"));
  assert.match(html, /Checks passed/);
  assert.match(html, /Release approval is evaluated separately/);
  assert.equal((html.match(/<tr\b[^>]*class="check-passed/g) ?? []).length, 6);
  assert.doesNotMatch(html, /<button|Publish|Promote/);
});

test("malformed data removes all summary and target results", () => {
  for (const state of [example("invalid"), { kind: "ready", input: null }, null, undefined, { kind: "unknown" }]) {
    const html = renderChecks(state);
    assert.match(html, /role="alert"/);
    assert.match(html, /Check results could not be displayed/);
    assert.doesNotMatch(html, /Checks passed|Checks failed|<table/);
  }
});

test("loading and unavailable states cannot retain a passing summary", () => {
  for (const state of ["loading", "unavailable"]) {
    const html = renderChecks(example(state));
    assert.match(html, /role="status"/);
    assert.doesNotMatch(html, /Checks passed|<table/);
  }
});

test("untrusted identifiers are escaped as text in headings, attributes and evidence", () => {
  const text = '<img src=x onerror="alert(1)">';
  const html = renderChecks({ kind: "ready", input: {
    revision: text, expectedTargets: [{ id: text, platform: "ios" }], requiredChecks: [text],
    reports: [{ targetId: text, checkId: text, revision: text, state: "passed" }],
  } });
  assert.match(html, /<code[^>]*>&lt;img src=x onerror="alert\(1\)">/);
  assert.match(html, /aria-label="iOS target <img src=x onerror=&quot;alert\(1\)&quot;>"/);
  assert.doesNotMatch(html, /<img src=x onerror="alert\(1\)">/);
});

test("table relationships and textual statuses are available without color", () => {
  const html = renderChecks(example("failed"));
  assert.match(html, /aria-live="polite"/);
  assert.equal((html.match(/<caption/g) ?? []).length, 2);
  assert.equal((html.match(/scope="col"/g) ?? []).length, 6);
  assert.equal((html.match(/scope="row"/g) ?? []).length, 6);
  for (const label of ["Failed", "Passed", "Pending", "Incomplete"]) assert.ok(html.includes(label));
});

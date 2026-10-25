import assert from "node:assert/strict";
import { after, test } from "node:test";
import { mkdtemp, mkdir, rm } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join } from "node:path";
import { build } from "vite";

const root = fileURLToPath(new URL("../", import.meta.url));
const cache = join(root, "node_modules/.cache");
await mkdir(cache, { recursive: true });
const output = await mkdtemp(join(cache, "mixer-build-overview-render-"));
after(() => rm(output, { recursive: true, force: true }));
await build({ root, logLevel: "error", build: {
  ssr: join(root, "tests/render-build-overview.tsx"), outDir: output,
  emptyOutDir: false, minify: false,
} });
const compiled = await import(pathToFileURL(join(output, "render-build-overview.js")));
const render = state => compiled.renderBuildOverview(state).replace(/<!--[^]*?-->/g, "");
const example = compiled.buildExample;

test("the compiled Solid view preserves Android failure beside running iOS without aggregate success", () => {
  const html = render(example("mixed"));
  assert.match(html, /iOS build sample-ios-build-42/);
  assert.match(html, /Android build sample-android-build-73/);
  assert.match(html, /build-running/); assert.match(html, /build-failed/);
  assert.match(html, /Compilation failed\. Review the compiler diagnostics/);
  assert.match(html, /2 of 3/); assert.match(html, /2 of 2 platforms reported/);
  assert.doesNotMatch(html, /compiler_error|All builds succeeded|Builds passed|<button|<a\b/);
});

test("all eight lifecycle outcomes use distinct text and preserve worker uncertainty", () => {
  for (const [state, label] of Object.entries({ queued: "Queued", running: "Running", cancelling: "Cancelling",
    reconciling: "Confirming outcome", succeeded: "Succeeded", failed: "Failed", cancelled: "Cancelled", timed_out: "Timed out" })) {
    const html = render(example(state));
    assert.equal((html.match(new RegExp(`build-${state}\\b`, "g")) ?? []).length, 2, state);
    assert.ok(html.includes(label), state);
    if (state === "cancelling") assert.match(html, /Cancellation requested\. Waiting for the build to stop\./);
    if (state === "reconciling") assert.match(html, /The deadline has passed\. Confirming whether the build has stopped\./);
    if (state === "cancelling" || state === "reconciling") assert.doesNotMatch(html, /This platform build was cancelled|This attempt exceeded its deadline/);
    assert.match(html, /Build status is separate from signing and distribution/);
    assert.doesNotMatch(html, /release approval|Worker completion|Queue position/);
  }
});

test("missing and zero reports retain all selected identities as explicit unreported cards", () => {
  for (const [scenario, missing] of [["missing", 1], ["empty", 2]]) {
    const html = render(example(scenario));
    assert.equal((html.match(/build-not_reported\b/g) ?? []).length, missing);
    assert.match(html, /sample-ios-build-42/); assert.match(html, /sample-android-build-73/);
    assert.match(html, /No update received for this exact platform build and source content/);
    if (scenario === "empty") { assert.match(html, /No build updates yet/); assert.doesNotMatch(html, /Succeeded/); }
  }
});

test("loading, unavailable and malformed states cannot retain platform outcomes", () => {
  for (const [scenario, label] of [["loading", "Loading builds"], ["unavailable", "Build data unavailable"]]) {
    const html = render(example(scenario)); assert.match(html, /role="status"/); assert.ok(html.includes(label));
    assert.doesNotMatch(html, /sample-ios|target-card|Succeeded|2 of 2/);
  }
  for (const state of [example("invalid"), null, undefined, { kind: "unknown" }, { kind: "ready", input: null }]) {
    const html = render(state); assert.match(html, /role="alert"/);
    assert.match(html, /Build updates could not be displayed/); assert.doesNotMatch(html, /target-card|Succeeded|2 of 2/);
  }
});

test("each platform displays its own supplied source labels and exact immutable digests", () => {
  const state = example("succeeded"); const html = render(state);
  assert.match(html, /Source reference/); assert.match(html, /Upload reference/);
  for (const target of state.input.expected) {
    assert.ok(html.includes(target.source.reference));
    for (const key of ["sourceSha256", "toolchainLockSha256", "buildDefinitionSha256"]) assert.ok(html.includes(target[key]));
  }
  assert.equal((html.match(/Source content SHA-256/g) ?? []).length, 2);
  assert.equal((html.match(/<details\b/g) ?? []).length, 2);
  assert.equal((html.match(/<summary>Immutable build inputs/g) ?? []).length, 2);
  assert.equal((html.match(/<details[^>]*><summary>Immutable build inputs<\/summary><dl><div class="build-source-digest"><dt>Source content SHA-256/g) ?? []).length, 2);
  assert.match(html, /aria-live="polite"/);
  delete state.input.expected[0].source; delete state.input.expected[1].source;
  assert.doesNotMatch(render(state), /Source reference|Upload reference|sample\/fieldlog|source\.zip/);
});

test("untrusted source and build labels render as escaped text", () => {
  const state = example("succeeded"); const hostile = '<img src=x onerror="alert(1)">';
  state.input.expected[0].source.reference = hostile;
  state.input.expected[0].buildId = hostile; state.input.reports[0].buildId = hostile;
  const html = render(state);
  assert.match(html, /&lt;img src=x onerror="alert\(1\)">/);
  assert.match(html, /aria-label="iOS build <img src=x onerror=&quot;alert\(1\)&quot;>"/);
  assert.doesNotMatch(html, /<img src=x onerror="alert\(1\)">/);
});

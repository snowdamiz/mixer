import assert from "node:assert/strict";
import { readFile, writeFile, symlink, unlink, readlink, readdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import test from "node:test";

const packet = fileURLToPath(new URL("./", import.meta.url));
const workspace = fileURLToPath(new URL("../../", import.meta.url));
const snapshot = join(packet, "source-snapshot/console");
const installed = join(workspace, "console/node_modules");
const hash = value => createHash("sha256").update(value).digest("hex");
const { summarizeBuildOverview: summarize } = await import(pathToFileURL(join(snapshot, "src/domain/build-overview.ts")));
const { build } = await import(pathToFileURL(join(installed, "vite/dist/node/index.js")));
const { default: solid } = await import(pathToFileURL(join(installed, "vite-plugin-solid/dist/esm/index.mjs")));
await writeFile(join(snapshot, "independent-render.tsx"), `import { renderToString } from "solid-js/web";
import { BuildOverview } from "./src/components/BuildOverview.js";
export const render = (state: any) => renderToString(() => <BuildOverview state={state} />);
`);
await symlink(installed, join(snapshot, "node_modules"), "dir");
assert.equal(await readlink(join(snapshot, "node_modules")), installed);
try {
  const check = spawnSync(process.execPath, [join(installed, "typescript/bin/tsc"), "--noEmit", "--project", join(snapshot, "tsconfig.json")], { encoding: "utf8" });
  await writeFile(join(packet, "typecheck.stdout"), check.stdout);
  await writeFile(join(packet, "typecheck.stderr"), check.stderr);
  assert.equal(check.status, 0, check.stderr || check.stdout);
  await build({ root: snapshot, configFile: false, plugins: [solid({ ssr: true })], logLevel: "warn",
    ssr: { noExternal: true }, build: { ssr: join(snapshot, "independent-render.tsx"),
      outDir: join(packet, "compiled-component"), emptyOutDir: false, minify: false } });
  await build({ root: snapshot, configFile: join(snapshot, "vite.config.ts"),
    build: { outDir: join(packet, "production-dist"), emptyOutDir: false } });
} finally {
  await unlink(join(snapshot, "node_modules"));
}
const renderer = (await readdir(join(packet, "compiled-component"))).find(file => /^independent-render\.(?:js|mjs)$/.test(file));
assert.ok(renderer, "Vite did not emit the expected SSR renderer");
const { render: renderWithMarkers } = await import(pathToFileURL(join(packet, "compiled-component", renderer)));
const render = state => renderWithMarkers(state).replace(/<!--[^]*?-->/g, "");
const scope = { organizationId: "independent-org", projectId: "independent-project", applicationId: "independent-app" };
const target = (platform, digit) => ({ platform, buildId: `independent-${platform}-${digit}`, sourceSha256: digit.repeat(64),
  toolchainLockSha256: String(Number(digit) + 1).repeat(64), buildDefinitionSha256: String(Number(digit) + 2).repeat(64),
  source: { kind: platform === "ios" ? "revision" : "upload", reference: `independent/${platform}/${digit}` } });
const expected = [target("ios", "1"), target("android", "6")];
const pending = ["running", "cancelling", "reconciling"];
const report = (target, state) => {
  const { source: _label, ...identity } = target;
  return { ...scope, ...identity, state, attempt: 3, maxAttempts: 5,
    workerCompletionPending: pending.includes(state),
    ...(["failed", "timed_out"].includes(state) ? { failureCode: "test_failure" } : {}) };
};
const input = () => structuredClone({ scope, expected, reports: [report(expected[1], "failed"), report(expected[0], "succeeded")] });
const ready = value => ({ kind: "ready", input: value });
const parse = html => {
  const result = spawnSync("python3", [join(packet, "inspect_html.py")], { input: html, encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
};

test("distinct per-platform identities survive reversed reports and failure remains visible", () => {
  const result = summarize(input());
  assert.deepEqual(result.builds.map(row => [row.target.platform, row.target.buildId, row.observation.state]),
    [["ios", "independent-ios-1", "succeeded"], ["android", "independent-android-6", "failed"]]);
  assert.equal(Object.hasOwn(result, "state"), false);
  const html = render(ready(input()));
  assert.match(html, /build-succeeded/); assert.match(html, /build-failed/);
  assert.match(html, /Tests failed/); assert.match(html, /3 of 5/);
  assert.doesNotMatch(html, /All builds|Builds passed|All platforms succeeded/);
  const inspection = parse(html);
  assert.ok(!inspection.tags.some(tag => ["a", "button", "input", "select", "form"].includes(tag)));
  assert.equal(inspection.tags.filter(tag => tag === "details").length, 2);
  assert.equal(inspection.attributes.filter(([key]) => key === "open").length, 0);
});

test("common scope and full platform identity substitutions reject the entire view", () => {
  const bad = [];
  for (const key of ["organizationId", "projectId", "applicationId", "buildId", "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256", "platform"]) {
    const value = input(); value.reports[0][key] = key.endsWith("Sha256") ? "a".repeat(64) : "other"; bad.push(value);
  }
  const duplicate = input(); duplicate.reports = [duplicate.reports[0], duplicate.reports[0]]; bad.push(duplicate);
  const duplicateTarget = input(); duplicateTarget.expected[1] = duplicateTarget.expected[0]; bad.push(duplicateTarget);
  const empty = input(); empty.expected = []; bad.push(empty);
  const unknown = input(); unknown.reports[0].downloadUrl = "https://untrusted.invalid/output"; bad.push(unknown);
  const unsupported = input(); unsupported.reports[0].state = "successful"; bad.push(unsupported);
  for (const value of bad) {
    assert.throws(() => summarize(value), TypeError);
    const html = render(ready(value));
    assert.match(html, /role="alert"/);
    assert.doesNotMatch(html, /target-card|build-succeeded|independent-ios-1|independent-android-6/);
  }
});

test("lifecycle text boundaries use UTF-8 bytes and preserve backend-printable labels", () => {
  const accepted = ["x".repeat(128), "é".repeat(64), "😀".repeat(32), " leading trailing ", "tabs\tand\nlines", "escape\u001bdelete\u007f", "\u200b\u202e\ufdd0\u{10ffff}"];
  const rejected = ["x".repeat(129), "é".repeat(65), "😀".repeat(33), "\ud800", "\udfff", "\u0000", "\u001f", "\u0080", "\u009f", "\ufffe", "\uffff"];
  for (const label of accepted) {
    const value = input(); value.expected[0].buildId = label; value.reports[1].buildId = label;
    value.scope.organizationId = label; for (const row of value.reports) row.organizationId = label;
    const result = summarize(value); assert.equal(result.builds[0].target.buildId, label); assert.equal(result.scope.organizationId, label);
  }
  for (const label of rejected) {
    const value = input(); value.expected[0].buildId = label; value.reports[1].buildId = label;
    assert.throws(() => summarize(value), TypeError, JSON.stringify(label));
  }
  for (const [reference, valid] of [["x".repeat(1024), true], ["x".repeat(1025), false], ["é".repeat(512), true], ["é".repeat(513), false]]) {
    const value = input(); value.expected[1].source.reference = reference;
    if (valid) assert.equal(summarize(value).builds[1].target.source.reference, reference);
    else assert.throws(() => summarize(value), TypeError);
  }
});

test("all eight states preserve worker uncertainty, including late non-infrastructure timeout failure", () => {
  const labels = { queued: "Queued", running: "Running", cancelling: "Cancelling", reconciling: "Confirming outcome",
    succeeded: "Succeeded", failed: "Failed", cancelled: "Cancelled", timed_out: "Timed out" };
  for (const [state, label] of Object.entries(labels)) {
    const value = input(); value.reports[0] = report(expected[1], state);
    const result = summarize(value); assert.equal(result.builds[1].observation.workerCompletionPending, pending.includes(state));
    const html = render(ready(value)); assert.ok(html.includes(label)); assert.ok(html.includes(`build-${state}`));
    if (state === "cancelling") assert.match(html, /Waiting for the build to stop/);
    if (state === "reconciling") assert.match(html, /Confirming whether the build has stopped/);
    if (state === "timed_out") assert.match(html, /Tests failed/);
    value.reports[0].workerCompletionPending = !value.reports[0].workerCompletionPending;
    assert.throws(() => summarize(value), TypeError, state);
  }
});

test("missing reports retain expected builds while unavailable/invalid wrappers remove outcomes", () => {
  for (const count of [0, 1]) {
    const value = input(); value.reports.length = count;
    const result = summarize(value); assert.equal(result.builds.length, 2); assert.equal(result.reportedCount, count);
    assert.equal(result.builds.filter(row => row.observation === null).length, 2 - count);
    const html = render(ready(value)); assert.match(html, /independent-ios-1/); assert.match(html, /independent-android-6/);
    assert.equal((html.match(/build-not_reported\b/g) ?? []).length, 2 - count);
  }
  const one = input(); one.expected = [one.expected[1]]; one.reports = [one.reports[0]];
  assert.equal(summarize(one).builds[0].target.platform, "android");
  for (const wrapper of [null, undefined, { kind: "unknown" }, { kind: "ready", input: null }, { kind: "loading" }, { kind: "unavailable" }]) {
    const html = render(wrapper); assert.doesNotMatch(html, /target-card|independent-ios|independent-android|Succeeded|2 of 2/);
    assert.match(html, /role="(?:alert|status)"/);
  }
});

test("snapshots have no caller aliases and hostile label markup stays text", () => {
  const value = input(); const snapshot = summarize(value);
  value.scope.organizationId = "changed"; value.expected[0].source.reference = "changed";
  value.expected[0].sourceSha256 = "a".repeat(64); value.reports[1].state = "running";
  assert.equal(snapshot.scope.organizationId, scope.organizationId);
  assert.equal(snapshot.builds[0].target.source.reference, expected[0].source.reference);
  assert.equal(snapshot.builds[0].target.sourceSha256, expected[0].sourceSha256);
  assert.equal(snapshot.builds[0].observation.state, "succeeded");
  const assertFrozen = object => { assert.equal(Object.isFrozen(object), true); for (const nested of Object.values(object)) if (nested && typeof nested === "object") assertFrozen(nested); };
  assertFrozen(snapshot);
  for (const hostile of ['<img src=x onerror="alert(1)">', '<script>alert(1)</script>', '</code><a href="javascript:alert(1)">x</a>']) {
    const sample = input(); sample.expected[0].buildId = hostile; sample.reports[1].buildId = hostile; sample.expected[0].source.reference = hostile;
    const html = render(ready(sample)); const inspection = parse(html);
    assert.ok(!inspection.tags.some(tag => ["script", "img", "a"].includes(tag)));
    assert.ok(!inspection.attributes.some(([name]) => name.startsWith("on") || name === "href" || name === "src"));
    assert.ok(inspection.text.some(text => text.includes(hostile)));
  }
});

async function descendants(dir) {
  const files = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) files.push(...await descendants(join(dir, entry.name)));
    else if (entry.isFile()) files.push(join(dir, entry.name));
    else throw new Error(`Unexpected output path ${entry.name}`);
  }
  return files;
}
test("production excludes synthetic preview code and retains website brand bytes/tokens", async () => {
  const files = await descendants(join(packet, "production-dist"));
  const scripts = (await Promise.all(files.filter(file => file.endsWith(".js")).map(file => readFile(file, "utf8")))).join("\n");
  for (const marker of ["sample-ios-build-42", "sample-android-build-73", "sample-fieldlog-source.zip", "Synthetic build data", "Local preview", "Example state"]) assert.ok(!scripts.includes(marker), marker);
  assert.ok(!files.some(file => file.includes("BuildOverviewPreview")));
  assert.ok(scripts.includes("Build data unavailable"));
  assert.ok(scripts.includes("No build data source is connected"));
  const tokens = css => Object.fromEntries([...css.matchAll(/^:root\s*\{([^}]+)\}/gm)].flatMap(match => match[1].split(";").map(declaration => {
    const i = declaration.indexOf(":"); return [declaration.slice(0, i).trim(), declaration.slice(i + 1).trim()];
  })).filter(([key]) => key.startsWith("--")));
  const website = await readFile(join(packet, "source-snapshot/website/src/styles.css"), "utf8");
  const consoleBrand = await readFile(join(snapshot, "src/brand.css"), "utf8");
  for (const [key, value] of Object.entries(tokens(website))) assert.equal(tokens(consoleBrand)[key], value, key);
  for (const asset of ["flick-128.webp", "favicon-32.png"]) assert.equal(hash(await readFile(join(snapshot, "public/assets", asset))), hash(await readFile(join(packet, "source-snapshot/website/public/assets", asset))));
});

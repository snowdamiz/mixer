import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { cp, mkdir, readFile, writeFile, symlink, readlink, unlink } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { test } from "node:test";
import { spawnSync } from "node:child_process";

const packet = fileURLToPath(new URL("./", import.meta.url));
const workspace = resolve(packet, "../..");
const consoleRoot = join(workspace, "console");
const snapshot = join(packet, "source-snapshot");
const output = join(packet, "compiled-component");
await mkdir(join(snapshot, "src/components"), { recursive: true });
await mkdir(join(snapshot, "src/domain"), { recursive: true });
const files = ["src/components/ReleaseChecks.tsx", "src/domain/release-check-summary.ts"];
const hashes = {};
for (const file of files) {
  const source = join(consoleRoot, file);
  await cp(source, join(snapshot, file));
  hashes[`console/${file}`] = createHash("sha256").update(await readFile(source)).digest("hex");
}
try { await symlink(join(consoleRoot, "node_modules"), join(snapshot, "node_modules"), "dir"); }
catch (error) { if (error.code !== "EEXIST") throw error; }
assert.equal(await readlink(join(snapshot, "node_modules")), join(consoleRoot, "node_modules"));
await writeFile(join(snapshot, "render.tsx"), `import { renderToString } from "solid-js/web";
import { ReleaseChecks } from "./src/components/ReleaseChecks.js";
export const render = (state: any) => renderToString(() => <ReleaseChecks state={state} />);
`);
const { build } = await import(pathToFileURL(join(consoleRoot, "node_modules/vite/dist/node/index.js")));
const { default: solid } = await import(pathToFileURL(join(consoleRoot, "node_modules/vite-plugin-solid/dist/esm/index.mjs")));
try {
  await build({
    root: snapshot, configFile: false, logLevel: "warn", plugins: [solid({ ssr: true })],
    ssr: { noExternal: true },
    build: { ssr: join(snapshot, "render.tsx"), outDir: output, emptyOutDir: true, minify: false },
  });
} finally {
  await unlink(join(snapshot, "node_modules"));
}
const { render: renderWithMarkers } = await import(pathToFileURL(join(output, "render.mjs")));
const render = state => renderWithMarkers(state).replace(/<!--[^]*?-->/g, "");
await writeFile(join(packet, "component-source-hashes.json"), JSON.stringify(hashes, null, 2) + "\n");

const current = "independent-current";
const target = (id, platform) => ({ id, platform });
const targets = [target("independent-ios", "ios"), target("independent-android", "android")];
const required = ["compatibility", "policy", "tests"];
const reports = () => targets.flatMap(item => required.map(checkId => ({ targetId: item.id, checkId, revision: current, state: "passed" })));
const ready = (results = reports(), revision = current) => ({ kind: "ready", input: { revision, expectedTargets: targets, requiredChecks: required, reports: results } });

test("a current failure dominates every position even with a different pending result", () => {
  for (let failed = 0; failed < 6; failed++) {
    const results = reports();
    results[failed].state = "failed";
    results[(failed + 1) % 6].state = "pending";
    const html = render(ready(results));
    assert.match(html, /summary-failed/);
    assert.match(html, /Checks failed/);
    assert.equal((html.match(/class="check-failed"/g) ?? []).length, 1);
    assert.doesNotMatch(html, /Checks passed/);
  }
});

test("only selected revision reports can pass; missing, stale and explicit not-run evidence stay distinct", () => {
  const results = reports();
  results[0].revision = "independent-old";
  results[0].state = "failed";
  results[1].state = "not_run";
  results.splice(2, 1);
  const html = render(ready(results));
  assert.match(html, /summary-incomplete/);
  assert.match(html, /Selected source revision<\/dt><dd><code[^>]*>independent-current/);
  assert.match(html, /Previously failed\. Does not cover the selected revision\./);
  assert.match(html, /Reported as not run\./);
  assert.match(html, /No result received/);
  assert.equal((html.match(/class="check-/g) ?? []).length, 6);
  assert.doesNotMatch(html, /Checks failed|Checks passed/);
  const changed = render(ready(reports(), "next-revision"));
  assert.match(changed, /summary-incomplete/);
  assert.equal((changed.match(/Previous revision/g) ?? []).length, 6);
});

test("malformed state wrappers and ready payloads fail closed without a summary, revision or target table", () => {
  const invalidInputs = [null, {}, { ...ready().input, reports: null },
    { ...ready().input, reports: [...reports(), reports()[0]] },
    { ...ready().input, requiredChecks: [] },
    { ...ready().input, expectedTargets: [target("unsupported", "web")] },
    { ...ready().input, reports: [{ ...reports()[0], state: "success" }] },
  ];
  const malformedStates = [null, undefined, { kind: "unknown" }, ...invalidInputs.map(input => ({ kind: "ready", input }))];
  for (const state of malformedStates) {
    const html = render(state);
    assert.match(html, /role="alert"/);
    assert.match(html, /Check results could not be displayed/);
    assert.doesNotMatch(html, /summary-(passed|failed|incomplete)|<table|independent-current/);
  }
});

test("untrusted identifiers cannot create executable tags, links, handlers or raw markup", () => {
  for (const text of ['<script>alert(1)</script>', '<img src=x onerror="alert(1)">', '</code><a href="javascript:alert(1)">x</a>']) {
    const html = render({ kind: "ready", input: { revision: text,
      expectedTargets: [target(text, "ios")], requiredChecks: [text],
      reports: [{ targetId: text, checkId: text, revision: text, state: "passed" }] } });
    assert.match(html, /Checks passed/);
    const parsed = spawnSync("python3", [join(packet, "inspect-html.py")], { input: html, encoding: "utf8" });
    assert.equal(parsed.status, 0, parsed.stderr);
    const inspection = JSON.parse(parsed.stdout);
    assert.ok(!inspection.tags.some(tag => ["script", "img", "a"].includes(tag)));
    assert.ok(!inspection.attributes.some(([name]) => name.startsWith("on")));
    assert.ok(!inspection.attributes.some(([name]) => name === "href" || name === "src"));
    assert.ok(html.includes("&lt;"));
  }
});

test("the view exposes native table semantics, text labels and read-only release context", () => {
  const html = render(ready());
  assert.equal((html.match(/<caption/g) ?? []).length, 2);
  assert.equal((html.match(/scope="col"/g) ?? []).length, 6);
  assert.equal((html.match(/scope="row"/g) ?? []).length, 6);
  assert.match(html, /aria-labelledby="release-checks-heading"/);
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /Release approval is evaluated separately/);
  assert.doesNotMatch(html, /<button|<input|<select|href=/);
});

test("loading and unavailable render without any passing, failed or incomplete summary", () => {
  for (const kind of ["loading", "unavailable"]) {
    const html = render({ kind });
    assert.match(html, /role="status"/);
    assert.doesNotMatch(html, /summary-(passed|failed|incomplete)|<table|independent-current/);
  }
});

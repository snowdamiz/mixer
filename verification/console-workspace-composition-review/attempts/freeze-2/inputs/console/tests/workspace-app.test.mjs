import assert from "node:assert/strict";
import { after, test } from "node:test";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join } from "node:path";
import { build } from "vite";

const root = fileURLToPath(new URL("../", import.meta.url));
const cache = join(root, "node_modules/.cache");
await mkdir(cache, { recursive: true });
const output = await mkdtemp(join(cache, "mixer-workspace-app-"));
after(() => rm(output, { recursive: true, force: true }));
await build({ root, logLevel: "error", ssr: { noExternal: ["@solidjs/router"] }, build: {
  ssr: join(root, "tests/workspace-app-render.tsx"), outDir: output, emptyOutDir: false, minify: false,
} });
const { renderWorkspaceApp } = await import(pathToFileURL(join(output, "workspace-app-render.js")));
const render = (url, session) => renderWorkspaceApp(url, session).replace(/<!--[^]*?-->/g, "");

test("production route renders workspace within the website-branded shell and active navigation", () => {
  const html = render("/workspace");
  assert.match(html, /src="\/assets\/flick-128.webp"/);
  assert.match(html, /mixer<span class="brand-period">\.<\/span>/);
  assert.match(html, /href="#main-content"/);
  assert.match(html, /<main id="main-content" tabindex="-1">/i);
  assert.match(html, /href="\/workspace"[^>]*aria-current="page"/);
  assert.match(html, /<h1 id="workspace-directory-heading">Organizations &amp; projects<\/h1>/);
  assert.match(html, /Workspace temporarily unavailable/);
  assert.match(html, /Choose an organization/);
  assert.doesNotMatch(html, /Sign out|Create organization|FieldLog|fixture/);
});

test("server rendering never calls an authenticated adapter or serializes its private values", () => {
  let calls = 0;
  const privateValue = "private-session-sentinel";
  const client = { organizations() { calls++; throw Error(privateValue); }, projects() { calls++; throw Error(privateValue); } };
  const html = render("/workspace", { kind: "ready", client });
  assert.equal(calls, 0);
  assert.doesNotMatch(html, /private-session-sentinel|organizations\(\)|projects\(\)/);
  assert.match(html, /Loading organizations/);
});

test("build, release and missing routes retain their distinct views and share workspace navigation", () => {
  for (const path of ["/builds", "/releases", "/not-a-route"]) {
    const html = render(path);
    assert.match(html, /href="\/workspace"/);
    assert.doesNotMatch(html, /id="workspace-directory-heading"/);
    if (path === "/not-a-route") assert.match(html, /Page not found/);
    else assert.doesNotMatch(html, /Page not found/);
  }
});

test("shell section follows the actual matched route including trailing slash, query and fragment", () => {
  for (const [path, label] of [["/workspace", "Organizations &amp; projects"], ["/builds", "Builds"], ["/releases", "Releases"]]) {
    for (const suffix of ["/", "?view=all", "#content"]) {
      const html = render(path + suffix);
      assert.ok(html.includes(`<strong>${label}</strong>`));
      assert.doesNotMatch(html, /Page not found/);
    }
  }
  assert.match(render("/workspace/unknown"), /<strong>Page not found<\/strong>/);
});

import assert from "node:assert/strict";
import { after, test } from "node:test";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join } from "node:path";
import { build } from "vite";

const root = fileURLToPath(new URL("../", import.meta.url));
const cache = join(root, "node_modules/.cache"); mkdirSync(cache, { recursive: true });
const output = mkdtempSync(join(cache, "mixer-browser-session-binding-"));
after(() => { rmSync(output, { recursive: true, force: true }); assert.equal(existsSync(output), false); });
try {
  execFileSync(process.execPath, [join(root, "node_modules/typescript/bin/tsc"), "src/state/browser-session-binding.ts", "src/state/workspace-binding.ts",
    "--target", "ES2022", "--module", "ESNext", "--moduleResolution", "Bundler", "--strict", "--skipLibCheck",
    "--noUncheckedIndexedAccess", "--exactOptionalPropertyTypes", "--outDir", output], { cwd: root, stdio: "pipe", timeout: 15000 });
  await build({ root, logLevel: "error", ssr: { noExternal: ["@solidjs/router"] }, build: {
    ssr: join(root, "tests/workspace-app-render.tsx"), outDir: join(output, "app"), emptyOutDir: false, minify: false,
  } });
} catch (error) {
  if (error.stdout) process.stderr.write(error.stdout);
  if (error.stderr) process.stderr.write(error.stderr);
  rmSync(output, { recursive: true, force: true }); throw error;
}
writeFileSync(join(output, "package.json"), '{"type":"module"}\n');

test("Solid client runtime checks synthetic lifecycle events, epoch fences and actual cookie/workspace binding join", () => {
  const environment = { ...process.env,
    MIXER_BROWSER_SESSION_BINDING_MODULE: pathToFileURL(join(output, "state/browser-session-binding.js")).href,
    MIXER_BROWSER_SESSION_CONTROLLER_MODULE: pathToFileURL(join(output, "state/browser-session-controller.js")).href,
    MIXER_BROWSER_WORKSPACE_BINDING_MODULE: pathToFileURL(join(output, "state/workspace-binding.js")).href };
  delete environment.NODE_TEST_CONTEXT;
  let result;
  try { result = execFileSync(process.execPath, ["--conditions=browser", "--test", join(root, "tests/browser-session-binding-runner.mjs")], {
    cwd: root, encoding: "utf8", timeout: 30000, env: environment,
  }); } catch (error) {
    if (error.stdout) process.stdout.write(error.stdout);
    if (error.stderr) process.stderr.write(error.stderr);
    throw error;
  }
  assert.match(result, /# tests 10\b/); assert.match(result, /# fail 0\b/); process.stdout.write(result);
});

test("actual App SSR accepts the session seam without requesting or serializing private metadata", async () => {
  const { createBrowserSessionController } = await import(pathToFileURL(join(output, "state/browser-session-controller.js")));
  const { renderWorkspaceApp } = await import(pathToFileURL(join(output, "app/workspace-app-render.js")));
  const csrf = "A".repeat(43), generation = "B".repeat(42) + "A";
  let sessionCalls = 0, workspaceCalls = 0;
  const controller = createBrowserSessionController({ fetch: async path => {
    if (path !== "/auth/session") { workspaceCalls++; throw Error("unexpected SSR workspace call"); }
    sessionCalls++;
    return new Response(JSON.stringify({ state: "authenticated", generation, csrf_token: csrf, expires_at: Math.floor(Date.now() / 1000) + 60 }),
      { headers: { "content-type": "application/json", "cache-control": "no-store" } });
  } });
  try {
    controller.revalidate(); await new Promise(resolve => setImmediate(resolve));
    assert.equal(controller.getSession().kind, "ready");
    const html = renderWorkspaceApp("/workspace", controller.getSession());
    assert.match(html, /Loading organizations/); assert.doesNotMatch(html, new RegExp(`${csrf}|${generation}|csrf_token|expires_at`));
    assert.equal(sessionCalls, 1); assert.equal(workspaceCalls, 0);
  } finally { controller.dispose(); }
});

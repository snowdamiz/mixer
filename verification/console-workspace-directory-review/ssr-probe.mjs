import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join } from "node:path";

const root = fileURLToPath(new URL("../../", import.meta.url));
const { build } = await import(pathToFileURL(join(root, "console/node_modules/vite/dist/node/index.js")));
const phase = process.argv[2];
assert.ok(["initial-review", "correction"].includes(phase));
const evidence = join(root, "verification/console-workspace-directory-review", phase);
const cache = join(root, "console/node_modules/.cache");
await mkdir(cache, { recursive: true });
const output = await mkdtemp(join(cache, "mixer-workspace-directory-review-"));
const fixture = () => ({
  organizations: { kind: "ready", input: { organizations: [
    { id: " ", display_name: null, organization_roles: [] },
  ], next_cursor: null } },
  projects: { kind: "ready", organizationId: " ", input: { projects: [
    { organization_id: " ", id: "  ", display_name: null, roles: ["viewer"] },
  ], next_cursor: null } },
  selectedOrganizationId: " ", selectedProjectId: "  ",
  onSelectOrganization() {}, onSelectProject() {},
});
function buttonNames(html) {
  return [...html.matchAll(/<button\b([^]*?)>([^]*?)<\/button>/g)].map(([, attributes, content]) => {
    const explicit = /aria-label="([^"]*)"/.exec(attributes)?.[1];
    const text = content.replace(/<svg\b[^]*?<\/svg>/g, "").replace(/<!--[^]*?-->/g, "").replace(/<[^>]*>/g, "");
    return { attributes, name: (explicit ?? text).replace(/\s+/gu, " ").trim() };
  });
}
try {
  await build({ root: join(root, "console"), logLevel: "error", build: {
    ssr: join(root, "console/tests/workspace-directory-render.tsx"), outDir: output,
    emptyOutDir: false, minify: false,
  } });
  const { renderWorkspaceDirectory } = await import(pathToFileURL(join(output, "workspace-directory-render.js")));
  const input = fixture();
  const html = renderWorkspaceDirectory(input);
  await writeFile(join(evidence, "whitespace-identities.html"), html);
  const names = buttonNames(html);
  assert.equal(names.length, 2);
  if (phase === "initial-review") assert.deepEqual(names.map(button => button.name), ["", ""]);
  else assert.ok(names.every(button => button.name.length > 0));
  const stale = fixture(); stale.selectedOrganizationId = "other";
  const staleHtml = renderWorkspaceDirectory(stale);
  await writeFile(join(evidence, "stale-selection.html"), staleHtml);
  assert.ok(staleHtml.includes("Choose an organization"));
  assert.ok(!staleHtml.includes("Selected project"));
  const result = {
    phase, whitespace_identity_buttons: names,
    exact_input_ids: { organization: input.organizations.input.organizations[0].id,
      project: input.projects.input.projects[0].id },
    stale_selection_hides_project: true,
    accessible_name_method: "Explicit aria-label if present, otherwise whitespace-normalized button text after removing aria-hidden SVG; exact SSR fixture has no external naming references.",
    runtime_scope: "Vite-compiled Solid SSR in Node only; no browser or native runtime",
  };
  await writeFile(join(evidence, "ssr-probe.json"), JSON.stringify(result, null, 2) + "\n");
  console.log(JSON.stringify(result, null, 2));
} finally {
  await rm(output, { recursive: true, force: true });
}

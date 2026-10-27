import assert from "node:assert/strict";
import { after, test } from "node:test";
import { mkdtemp, mkdir, rm } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { join } from "node:path";
import { build } from "vite";

const root = fileURLToPath(new URL("../", import.meta.url));
const cache = join(root, "node_modules/.cache");
await mkdir(cache, { recursive: true });
const output = await mkdtemp(join(cache, "mixer-workspace-directory-render-"));
after(() => rm(output, { recursive: true, force: true }));
await build({ root, logLevel: "error", build: {
  ssr: join(root, "tests/workspace-directory-render.tsx"), outDir: output, emptyOutDir: false, minify: false,
} });
const compiled = await import(pathToFileURL(join(output, "workspace-directory-render.js")));
const render = state => compiled.renderWorkspaceDirectory(state).replace(/<!--[^]*?-->/g, "");
const state = () => ({ organizations: { kind: "ready", input: { organizations: [
  { id: "org:北/..", display_name: "Studio & Co", organization_roles: [] },
  { id: "org:second", display_name: null, organization_roles: ["administrator", "owner"] },
], next_cursor: null } }, projects: { kind: "ready", organizationId: "org:北/..", input: { projects: [
  { organization_id: "org:北/..", id: "project/one", display_name: "FieldLog", roles: ["developer", "release_manager"] },
  { organization_id: "org:北/..", id: "project:two", display_name: null, roles: ["viewer"] },
], next_cursor: null } }, selectedOrganizationId: "org:北/..", selectedProjectId: "project/one",
  onSelectOrganization() {}, onSelectProject() {} });

test("compiled Solid view uses semantic sections, current selection and separate organization/project roles", () => {
  const html = render(state());
  assert.match(html, /<h1 id="workspace-directory-heading">Organizations &amp; projects<\/h1>/);
  assert.match(html, /<h2 id="workspace-organizations-heading">Organizations<\/h2>/);
  assert.match(html, /<h2 id="workspace-projects-heading">Projects<\/h2>/);
  assert.match(html, /aria-label="Organizations"/); assert.match(html, /aria-label="Projects"/);
  assert.match(html, /Studio &amp; Co/); assert.match(html, /org:second/); assert.match(html, /project:two/);
  assert.equal((html.match(/aria-pressed="true"/g) ?? []).length, 2);
  assert.match(html, /Project access/); assert.match(html, /Your organization roles/); assert.match(html, /Your project roles/);
  assert.match(html, /Release manager/); assert.match(html, /Administrator/);
  assert.match(html, /aria-live="polite" aria-atomic="true"/); assert.match(html, /Selected project/);
  assert.doesNotMatch(html, /<a\b|Create|Import|Delete|Configure|API|Phoenix|next_cursor|organization_roles/);
});

test("null names fall back to exact IDs and untrusted labels render only as escaped text", () => {
  const input = state(); const hostile = '<img src=x onerror="alert(1)">';
  input.organizations.input.organizations[0].display_name = hostile;
  input.projects.input.projects[0].display_name = hostile;
  const html = render(input);
  assert.match(html, /&lt;img src=x onerror="alert\(1\)">/);
  assert.doesNotMatch(html, /<img src=x/); assert.match(html, /<bdi(?:\s[^>]*)?>org:second<\/bdi>/); assert.match(html, /<bdi(?:\s[^>]*)?>project:two<\/bdi>/);
});

test("unnamed ASCII and Unicode whitespace IDs have readable distinct button, header and selection identities", () => {
  for (const [organizationId, projectId, organizationMarker, projectMarker] of [
    [" ", "  ", '"\\u0020"', '"\\u0020\\u0020"'],
    ["\u00a0", "\u2003\u3000", '"\\u00a0"', '"\\u2003\\u3000"'],
  ]) {
    const input = state();
    input.organizations.input.organizations = [{ id: organizationId, display_name: null, organization_roles: [] }];
    input.projects = { kind: "ready", organizationId, input: { projects: [
      { organization_id: organizationId, id: projectId, display_name: null, roles: ["viewer"] },
    ], next_cursor: null } };
    input.selectedOrganizationId = organizationId; input.selectedProjectId = projectId;
    const html = render(input);
    const buttons = [...html.matchAll(/<button\b[^>]*>([^]*?)<\/button>/g)].map(match =>
      match[1].replace(/<svg\b[^]*?<\/svg>/g, "").replace(/<[^>]*>/g, "").replace(/\s+/gu, " ").trim());
    assert.equal(buttons.length, 2);
    assert.ok(buttons[0].startsWith("Organization ID ")); assert.ok(buttons[0].includes(organizationMarker));
    assert.ok(buttons[1].startsWith("Project ID ")); assert.ok(buttons[1].includes(projectMarker));
    assert.notEqual(buttons[0], buttons[1]);
    assert.equal(html.split(organizationMarker).length - 1, 2, "organization button and selected-organization header");
    assert.equal(html.split(projectMarker).length - 1, 2, "project button and selected-project status");
    assert.equal((html.match(/aria-pressed="true"/g) ?? []).length, 2);
    assert.equal(input.selectedOrganizationId, organizationId); assert.equal(input.selectedProjectId, projectId);
  }
});

test("nonnull names remain exact even when blank-looking; whitespace IDs have a separate readable marker", () => {
  const input = state();
  input.organizations.input.organizations = [{ id: " ", display_name: "  Studio  ", organization_roles: [] }];
  input.selectedOrganizationId = " "; input.selectedProjectId = "  ";
  input.projects = { kind: "ready", organizationId: " ", input: { projects: [
    { organization_id: " ", id: "  ", display_name: "\u00a0", roles: ["viewer"] },
  ], next_cursor: null } };
  const html = render(input);
  assert.match(html, /<bdi(?:\s[^>]*)?>  Studio  <\/bdi>/); assert.match(html, /<bdi(?:\s[^>]*)?>\u00a0<\/bdi>/);
  assert.ok(html.includes('"\\u0020"')); assert.ok(html.includes('"\\u0020\\u0020"'));
  assert.doesNotMatch(html, /Organization ID|Project ID/);
});

test("organization-only and completely empty workspaces have distinct honest empty states", () => {
  const input = state(); input.projects.input.projects = [];
  const html = render(input);
  assert.match(html, /No accessible projects/); assert.match(html, /There are no projects available to your account/);
  assert.doesNotMatch(html, /Selected project|FieldLog|Create|Import/);
  input.organizations.input.organizations = [];
  const empty = render(input);
  assert.match(empty, /No organizations yet/); assert.match(empty, /Choose an organization/);
  assert.doesNotMatch(empty, /FieldLog|Studio &amp; Co|Selected project|No accessible projects/);
});

test("loading, unavailable, unauthenticated and failures never retain rows or project selection", () => {
  const cases = [
    [{ kind: "loading" }, "Loading organizations", "status"],
    [{ kind: "unavailable" }, "Workspace temporarily unavailable", "status"],
    [{ kind: "unauthenticated" }, "Sign in to view your workspace", "status"],
    [{ kind: "error", reason: "permission_denied" }, "You cannot view these organizations", "alert"],
    [{ kind: "error", reason: "not_found" }, "Organization no longer available", "alert"],
    [{ kind: "error", reason: "request_failed" }, "Could not load organizations", "alert"],
    [{ kind: "ready", input: null }, "Could not load organizations", "alert"],
  ];
  for (const [organizations, label, role] of cases) {
    const input = state(); input.organizations = organizations; input.onRetryOrganizations = () => {};
    const html = render(input);
    assert.ok(html.includes(label)); assert.ok(html.includes(`role="${role}"`));
    assert.doesNotMatch(html, /Studio &amp; Co|FieldLog|Selected project|aria-pressed="true"/);
    if (["unavailable", "error"].includes(organizations.kind) || organizations.input === null) assert.match(html, /Try again/);
  }
});

test("project loading/error/auth/unavailable states preserve organization choice but hide stale projects", () => {
  for (const kind of ["loading", "error", "unauthenticated", "unavailable"]) {
    const input = state(); input.projects = { kind, organizationId: "org:北/..", ...(kind === "error" ? { reason: "request_failed" } : {}) };
    const html = render(input);
    assert.match(html, /Studio &amp; Co/); assert.doesNotMatch(html, /FieldLog|project\/one|Selected project/);
    assert.equal((html.match(/aria-pressed="true"/g) ?? []).length, 1);
  }
});

test("mismatched organization payload and stale selected IDs cannot expose another project's data", () => {
  let input = state(); input.projects.organizationId = "other";
  let html = render(input); assert.match(html, /Could not load projects/); assert.doesNotMatch(html, /FieldLog|Selected project/);
  input = state(); input.projects.input.projects[1].organization_id = "other";
  html = render(input); assert.match(html, /Could not load projects/); assert.doesNotMatch(html, /FieldLog|Selected project/);
  input = state(); input.selectedOrganizationId = "missing";
  html = render(input); assert.match(html, /Choose an organization/); assert.doesNotMatch(html, /FieldLog|Selected project/);
  input = state(); input.selectedProjectId = "missing";
  html = render(input); assert.match(html, /FieldLog/); assert.doesNotMatch(html, /Selected project/);
});

test("next-page controls reflect only validated server cursors and available handlers", () => {
  const input = state(); input.organizations.input.next_cursor = "opaque_org_-"; input.projects.input.next_cursor = "opaque_project_-";
  let html = render(input);
  assert.match(html, /disabled[^>]*>Next organizations/); assert.match(html, /disabled[^>]*>Next projects/);
  input.onNextOrganizations = () => {}; input.onNextProjects = () => {};
  html = render(input);
  assert.match(html, /<button type="button" class="workspace-page-button">Next organizations/);
  assert.match(html, /<button type="button" class="workspace-page-button">Next projects/);
  assert.doesNotMatch(html, /opaque_org|opaque_project|2 of|Total|Page [0-9]/);
  input.organizations.input.next_cursor = null; input.projects.input.next_cursor = null;
  assert.doesNotMatch(render(input), /Next organizations|Next projects/);
  input.projects.input.next_cursor = "invalid=";
  html = render(input); assert.match(html, /Could not load projects/); assert.doesNotMatch(html, /Next projects|FieldLog/);
});

test("first-page controls remain reachable after later-page failure and disabled during active requests", () => {
  const input = state();
  input.onFirstOrganizations = () => {}; input.onFirstProjects = () => {};
  assert.doesNotMatch(render(input), /First organizations|First projects/);
  input.canReturnToFirstOrganizations = true; input.canReturnToFirstProjects = true;
  let html = render(input);
  assert.match(html, /<button type="button" class="workspace-page-button">First organizations<\/button>/);
  assert.match(html, /<button type="button" class="workspace-page-button">First projects<\/button>/);
  input.projects = { kind: "loading", organizationId: "org:北/.." }; html = render(input);
  assert.match(html, /disabled[^>]*>First projects<\/button>/);
  for (const kind of ["error", "unavailable"]) {
    input.projects = { kind, organizationId: "org:北/..", ...(kind === "error" ? { reason: "not_found" } : {}) };
    html = render(input);
    assert.match(html, /<button type="button" class="workspace-page-button">First projects<\/button>/);
    assert.doesNotMatch(html, /FieldLog|Selected project/);
    input.organizations = kind === "error" ? { kind, reason: "request_failed" } : { kind };
    html = render(input);
    assert.match(html, /<button type="button" class="workspace-page-button">First organizations<\/button>/);
    assert.doesNotMatch(html, /First projects|FieldLog|Selected project/);
    input.organizations = state().organizations;
  }
  input.organizations = { kind: "loading" }; html = render(input);
  assert.match(html, /disabled[^>]*>First organizations<\/button>/);
  input.organizations = state().organizations; input.projects.organizationId = "stale";
  assert.doesNotMatch(render(input), /First projects/);
  input.projects = state().projects; delete input.onFirstOrganizations; delete input.onFirstProjects;
  html = render(input);
  assert.match(html, /disabled[^>]*>First organizations<\/button>/); assert.match(html, /disabled[^>]*>First projects<\/button>/);
  input.organizations = { kind: "unauthenticated" };
  assert.doesNotMatch(render(input), /First organizations|First projects/);
});

test("all malformed role/name data fails closed instead of fabricating names or access labels", () => {
  for (const patch of [{ display_name: "" }, { display_name: "bad\nname" }, { organization_roles: ["admin"] }, { organization_roles: ["owner", "developer"] }]) {
    const input = state(); Object.assign(input.organizations.input.organizations[0], patch);
    const html = render(input); assert.match(html, /Could not load organizations/); assert.doesNotMatch(html, /Studio &amp; Co|FieldLog|Selected project/);
  }
  const input = state(); input.projects.input.projects[0].roles = [];
  assert.match(render(input), /Could not load projects/); assert.doesNotMatch(render(input), /FieldLog|Selected project/);
});

// Host-only Solid reactive runtime. No browser, DOM, capture or UI automation.
import assert from "node:assert/strict";
import test from "node:test";
import { createComputed, createRoot, createSignal } from "solid-js";
import { createServer } from "node:http";
import { setTimeout as delay } from "node:timers/promises";

const { createWorkspaceBinding } = await import(process.env.MIXER_WORKSPACE_BINDING_MODULE);
const { createWorkspaceClient } = await import(process.env.MIXER_WORKSPACE_CLIENT_MODULE);
const organizationId = " /../+%2F北?&#=";
const orgs = { organizations: [{ id: organizationId, display_name: "Studio", organization_roles: ["owner"] }], next_cursor: null };
const projects = { projects: [{ organization_id: organizationId, id: "project/one", display_name: "FieldLog", roles: ["viewer"] }], next_cursor: null };
function owner() {
  let binding, setSession, dispose;
  createRoot(stop => {
    dispose = stop;
    const [session, update] = createSignal(undefined, { equals: false });
    setSession = update;
    binding = createWorkspaceBinding(session);
  });
  return { binding, setSession, dispose };
}
async function until(check) {
  const deadline = Date.now() + 2000;
  while (!check()) { assert.ok(Date.now() < deadline, "State transition deadline exceeded"); await delay(5); }
}
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };

test("actual Node client and HTTP responses update the shared Solid owner and exact selection", async () => {
  const seen = [];
  const server = createServer((request, response) => {
    seen.push({ url: request.url, authorization: request.headers.authorization });
    const url = new URL(request.url, "http://localhost");
    response.writeHead(200, { "content-type": "application/json" });
    const result = url.pathname === "/v3/orgs" ? orgs : projects;
    response.end(JSON.stringify({ ...result, next_cursor: url.searchParams.has("cursor") ? null : "NEXT" }));
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const app = owner();
  try {
    const client = createWorkspaceClient({ apiOrigin: `http://127.0.0.1:${server.address().port}`,
      accessToken: () => "synthetic.binding.token", allowInsecureLoopback: true });
    app.setSession({ kind: "ready", client });
    await until(() => app.binding.state().organizations.kind === "ready");
    app.binding.controller.selectOrganization(organizationId);
    await until(() => app.binding.state().projects.kind === "ready");
    app.binding.controller.selectProject({ organizationId, projectId: "project/one" });
    assert.equal(app.binding.state().selectedOrganizationId, organizationId);
    assert.equal(app.binding.state().selectedProjectId, "project/one");
    assert.equal(seen.length, 2);
    assert.equal(seen[1].url, `/v3/projects?organization_id=${encodeURIComponent(organizationId)}`);
    assert.ok(seen.every(row => row.authorization === "Bearer synthetic.binding.token"));
    app.binding.controller.nextProjects({ organizationId, cursor: "NEXT" });
    await until(() => app.binding.state().projects.kind === "ready");
    assert.equal(app.binding.state().canReturnToFirstProjects, true);
    app.binding.controller.firstProjects(organizationId);
    await until(() => app.binding.state().projects.kind === "ready");
    assert.equal(seen.at(-2).url, `/v3/projects?organization_id=${encodeURIComponent(organizationId)}&cursor=NEXT`);
    assert.equal(seen.at(-1).url, `/v3/projects?organization_id=${encodeURIComponent(organizationId)}`);
    assert.equal(app.binding.state().canReturnToFirstProjects, undefined);
    app.binding.controller.selectProject({ organizationId, projectId: "project/one" });
    // Child route ownership can end without disposing the app's shared selection.
    createRoot(stop => { assert.equal(app.binding.state().selectedProjectId, "project/one"); stop(); });
    assert.equal(app.binding.state().selectedProjectId, "project/one");
    app.binding.controller.nextOrganizations("NEXT");
    await until(() => app.binding.state().organizations.kind === "ready");
    assert.equal(app.binding.state().canReturnToFirstOrganizations, true);
    app.binding.controller.firstOrganizations();
    await until(() => app.binding.state().organizations.kind === "ready");
    assert.equal(seen.at(-2).url, "/v3/orgs?cursor=NEXT"); assert.equal(seen.at(-1).url, "/v3/orgs");
    assert.equal(app.binding.state().selectedProjectId, undefined);
    assert.equal(app.binding.state().canReturnToFirstOrganizations, undefined);
    assert.ok(seen.every(row => row.authorization === "Bearer synthetic.binding.token"));
    app.setSession({ kind: "unauthenticated" });
    assert.deepEqual(app.binding.state(), { organizations: { kind: "unauthenticated" }, projects: { kind: "unselected" } });
    assert.doesNotMatch(JSON.stringify(app.binding.state()), /Studio|FieldLog|synthetic.binding.token/);
  } finally {
    app.dispose();
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
});

test("reactive session replacement aborts old work and suppresses its late failure", async () => {
  const app = owner(); const old = deferred(); let oldSignal;
  try {
    app.setSession({ kind: "ready", client: { organizations(_page, signal) { oldSignal = signal; return old.promise; }, projects() { throw Error("unused"); } } });
    await until(() => oldSignal !== undefined);
    app.setSession({ kind: "ready", client: { organizations() { return Promise.resolve(orgs); }, projects() { return Promise.resolve(projects); } } });
    assert.equal(oldSignal.aborted, true);
    await until(() => app.binding.state().organizations.kind === "ready");
    old.reject(Error("private old session details"));
    await delay(0);
    assert.equal(app.binding.state().organizations.kind, "ready");
    assert.doesNotMatch(JSON.stringify(app.binding.state()), /private old/);
    app.setSession(undefined);
    assert.equal(app.binding.state().organizations.kind, "unavailable");
    assert.equal(app.binding.state().selectedOrganizationId, undefined);
  } finally { app.dispose(); }
});

test("disposing the application owner aborts pending projects and erases retained state", async () => {
  const app = owner(); const pending = deferred(); let signal;
  try {
    app.setSession({ kind: "ready", client: { organizations() { return Promise.resolve(orgs); },
      projects(_organization, _page, value) { signal = value; return pending.promise; } } });
    await until(() => app.binding.state().organizations.kind === "ready");
    app.binding.controller.selectOrganization(organizationId);
    await until(() => signal !== undefined);
    app.dispose();
    assert.equal(signal.aborted, true);
    assert.deepEqual(app.binding.state(), { organizations: { kind: "unavailable" }, projects: { kind: "unselected" } });
    pending.resolve(projects); await delay(0);
    assert.equal(app.binding.state().projects.kind, "unselected");
    app.binding.controller.selectOrganization(organizationId);
    assert.equal(app.binding.state().selectedOrganizationId, undefined);
  } finally { app.dispose(); }
});

test("pure consumers registered before binding cannot read old rows or act with an old session", async () => {
  let binding, setSession, dispose, prior;
  const observations = [];
  let projectCalls = 0, organizationCalls = 0;
  const client = { organizations() { organizationCalls++; return Promise.resolve({ ...orgs, next_cursor: "NEXT" }); },
    projects() { projectCalls++; return Promise.resolve(projects); } };
  const replacement = { kind: "ready", client };
  createRoot(stop => {
    dispose = stop;
    const [session, update] = createSignal(undefined);
    setSession = update;
    createComputed(() => {
      const current = session();
      if (binding && current !== prior) {
        prior = current;
        observations.push({ session: current?.kind, state: binding.state() });
        // This runs before the binding's effect admits the replacement epoch.
        if (current === replacement) {
          binding.controller.firstOrganizations(); binding.controller.firstProjects(organizationId);
          binding.controller.selectOrganization(organizationId);
        }
      }
    });
    binding = createWorkspaceBinding(session);
  });
  try {
    setSession({ kind: "ready", client });
    await until(() => binding.state().organizations.kind === "ready");
    binding.controller.nextOrganizations("NEXT");
    await until(() => binding.state().organizations.kind === "ready");
    assert.equal(binding.state().canReturnToFirstOrganizations, true);
    const beforeReplacement = organizationCalls;
    setSession(replacement);
    assert.equal(organizationCalls, beforeReplacement + 1, "only the replacement session may request its first page");
    assert.equal(projectCalls, 0);
    await until(() => binding.state().organizations.kind === "ready");
    setSession({ kind: "unauthenticated" });
    assert.equal(binding.state().organizations.kind, "unauthenticated");
    assert.ok(observations.length >= 3);
    for (const row of observations) {
      assert.notEqual(row.state.organizations.kind, "ready");
      assert.equal(row.state.selectedOrganizationId, undefined);
      assert.doesNotMatch(JSON.stringify(row.state), /Studio|FieldLog/);
    }
  } finally { dispose(); }
});

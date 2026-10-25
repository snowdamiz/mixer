import assert from "node:assert/strict";
import { after, test } from "node:test";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const output = mkdtempSync(join(tmpdir(), "mixer-workspace-controller-"));
after(() => { rmSync(output, { recursive: true, force: true }); assert.equal(existsSync(output), false); });
try {
  execFileSync(process.execPath, [join(root, "node_modules/typescript/bin/tsc"),
    "src/state/workspace-controller.ts", "--outDir", output, "--target", "ES2022", "--module", "ESNext",
    "--moduleResolution", "Bundler", "--strict", "--skipLibCheck", "--noUncheckedIndexedAccess",
    "--exactOptionalPropertyTypes"], { cwd: root, stdio: "pipe" });
} catch (error) { rmSync(output, { recursive: true, force: true }); throw error; }
writeFileSync(join(output, "package.json"), '{"type":"module"}\n');
const { createWorkspaceController } = await import(pathToFileURL(join(output, "state/workspace-controller.js")).href);
const { WorkspaceClientError } = await import(pathToFileURL(join(output, "api/workspace-client.js")).href);
const { resolveWorkspaceDirectory } = await import(pathToFileURL(join(output, "domain/workspace-directory.js")).href);

const organizations = (ids = ["a", "b"], cursor = null) => ({
  organizations: ids.map(id => ({ id, display_name: null, organization_roles: ["owner"] })), next_cursor: cursor,
});
const projects = (organizationId = "a", ids = ["p", "q"], cursor = null) => ({
  projects: ids.map(id => ({ organization_id: organizationId, id, display_name: null, roles: ["viewer"] })), next_cursor: cursor,
});
const flush = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function controlled() {
  const calls = [];
  const capture = (kind, organizationId, page, signal) => {
    const pending = deferred();
    calls.push({ kind, organizationId, page, signal, ...pending });
    return pending.promise;
  };
  const client = {
    organizations: (page, signal) => capture("organizations", undefined, page, signal),
    projects: (organizationId, page, signal) => capture("projects", organizationId, page, signal),
  };
  return { client, calls };
}
async function ready(controller, api, page = organizations()) {
  controller.setSession({ kind: "ready", client: api.client });
  api.calls.at(-1).resolve(page);
  await flush();
}
async function selected(controller, api, organizationId = "a", page = projects(organizationId)) {
  controller.selectOrganization(organizationId);
  api.calls.at(-1).resolve(page);
  await flush();
}
function assertEmpty(state, kind) {
  assert.deepEqual(state, { organizations: { kind }, projects: { kind: "unselected" } });
}

test("initial state is immutable unavailable and invalid actions make no requests", () => {
  const controller = createWorkspaceController();
  assertEmpty(controller.getState(), "unavailable");
  assert.ok(Object.isFrozen(controller));
  assert.ok(Object.isFrozen(controller.getState()));
  assert.ok(Object.isFrozen(controller.getState().organizations));
  assert.ok(Object.isFrozen(controller.getState().projects));
  const state = controller.getState();
  controller.selectOrganization("a"); controller.selectProject({ organizationId: "a", projectId: "p" });
  controller.nextOrganizations("old"); controller.nextProjects({ organizationId: "a", cursor: "old" });
  controller.retryOrganizations(); controller.retryProjects("a");
  assert.equal(controller.getState(), state);
  controller.dispose();
});

test("ready session starts only first organization page and never auto-selects", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  controller.setSession({ kind: "ready", client: api.client });
  assertEmpty(controller.getState(), "loading");
  assert.equal(api.calls.length, 1); assert.equal(api.calls[0].kind, "organizations");
  assert.deepEqual(api.calls[0].page, {}); assert.ok(Object.isFrozen(api.calls[0].page));
  assert.ok(api.calls[0].signal instanceof AbortSignal);
  api.calls[0].resolve(organizations()); await flush();
  assert.equal(controller.getState().organizations.kind, "ready");
  assert.equal(controller.getState().selectedOrganizationId, undefined);
  assert.deepEqual(controller.getState().projects, { kind: "unselected" });
  assert.equal(api.calls.length, 1); controller.dispose();
});

test("empty valid pages remain ready with no automatic network or selection", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  await ready(controller, api, organizations([]));
  controller.selectOrganization("a"); controller.nextOrganizations("anything");
  assert.equal(api.calls.length, 1); assert.deepEqual(controller.getState().organizations.input, organizations([]));
  await ready(controller, api); await selected(controller, api, "a", projects("a", []));
  controller.selectProject({ organizationId: "a", projectId: "p" });
  assert.equal(controller.getState().projects.kind, "ready");
  assert.equal(controller.getState().selectedProjectId, undefined); controller.dispose();
});

test("selection accepts only exact visible IDs and repeated selection makes no request", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  await ready(controller, api, organizations(["a", " a "]));
  for (const id of ["missing", "A", "a ", "*", ""]) controller.selectOrganization(id);
  assert.equal(api.calls.length, 1);
  controller.selectOrganization("a"); controller.selectOrganization("a");
  assert.equal(api.calls.length, 2); assert.equal(api.calls[1].organizationId, "a");
  assert.equal(controller.getState().selectedOrganizationId, "a");
  assert.deepEqual(controller.getState().projects, { kind: "loading", organizationId: "a" });
  api.calls[1].resolve(projects()); await flush();
  for (const selection of [{ organizationId: "b", projectId: "p" }, { organizationId: "a", projectId: "P" },
    { organizationId: "a", projectId: "missing" }]) controller.selectProject(selection);
  assert.equal(controller.getState().selectedProjectId, undefined);
  controller.selectProject({ organizationId: "a", projectId: "p" });
  const state = controller.getState(); controller.selectProject({ organizationId: "a", projectId: "p" });
  assert.equal(controller.getState(), state); assert.equal(api.calls.length, 2); controller.dispose();
});

test("valid arbitrary identifiers survive selection and project scope unchanged", async () => {
  for (const id of [".", "..", " /../+%2F北?&#=", " ", "é".repeat(64), "😀".repeat(32)]) {
    const controller = createWorkspaceController(); const api = controlled();
    await ready(controller, api, organizations([id]));
    await selected(controller, api, id, projects(id, [id]));
    assert.equal(api.calls[1].organizationId, id);
    controller.selectProject({ organizationId: id, projectId: id });
    assert.equal(controller.getState().selectedOrganizationId, id);
    assert.equal(controller.getState().selectedProjectId, id);
    assert.equal(resolveWorkspaceDirectory(controller.getState()).selectedProject.id, id);
    controller.dispose();
  }
});

test("changing organization synchronously clears project rows and selection and aborts old work", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  await ready(controller, api); await selected(controller, api, "a", projects("a", ["same"], "NEXT"));
  controller.selectProject({ organizationId: "a", projectId: "same" });
  controller.nextProjects({ organizationId: "a", cursor: "NEXT" }); const pending = api.calls.at(-1);
  controller.selectOrganization("b");
  assert.equal(pending.signal.aborted, true);
  assert.deepEqual(controller.getState().projects, { kind: "loading", organizationId: "b" });
  assert.equal(controller.getState().selectedProjectId, undefined);
  pending.resolve(projects("a", ["same"])); await flush();
  assert.equal(controller.getState().projects.kind, "loading");
  api.calls.at(-1).resolve(projects("b", ["same"])); await flush();
  assert.equal(controller.getState().selectedProjectId, undefined);
  assert.equal(resolveWorkspaceDirectory(controller.getState()).selectedProject, null); controller.dispose();
});

test("organization pagination accepts only the offered cursor and replaces all dependent data", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  await ready(controller, api, organizations(["a", "b"], "ORG_next-1")); await selected(controller, api);
  controller.selectProject({ organizationId: "a", projectId: "p" });
  controller.nextOrganizations("old"); assert.equal(api.calls.length, 2);
  controller.nextOrganizations("ORG_next-1");
  assertEmpty(controller.getState(), "loading"); assert.deepEqual(api.calls.at(-1).page, { cursor: "ORG_next-1" });
  controller.nextOrganizations("ORG_next-1"); controller.selectOrganization("a"); controller.retryOrganizations();
  assert.equal(api.calls.length, 3);
  api.calls.at(-1).resolve(organizations(["c"], "SECOND")); await flush();
  assert.deepEqual(controller.getState().organizations.input.organizations.map(row => row.id), ["c"]);
  controller.nextOrganizations("ORG_next-1"); controller.selectOrganization("a");
  assert.equal(api.calls.length, 3); assert.equal(controller.getState().selectedOrganizationId, undefined); controller.dispose();
});

test("project pagination checks current organization/cursor and clears prior selection immediately", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  await ready(controller, api); await selected(controller, api, "a", projects("a", ["p"], "PROJECT_next"));
  controller.selectProject({ organizationId: "a", projectId: "p" });
  controller.nextProjects({ organizationId: "b", cursor: "PROJECT_next" });
  controller.nextProjects({ organizationId: "a", cursor: "old" }); assert.equal(api.calls.length, 2);
  const callback = { organizationId: "a", cursor: "PROJECT_next" };
  controller.nextProjects(callback); callback.organizationId = "b"; callback.cursor = "mutated";
  assert.deepEqual(api.calls[2].page, { cursor: "PROJECT_next" }); assert.equal(api.calls[2].organizationId, "a");
  assert.deepEqual(controller.getState().projects, { kind: "loading", organizationId: "a" });
  assert.equal(controller.getState().selectedProjectId, undefined);
  controller.nextProjects({ organizationId: "a", cursor: "PROJECT_next" }); controller.retryProjects("a");
  assert.equal(api.calls.length, 3);
  api.calls[2].resolve(projects("a", ["q"])); await flush();
  controller.selectProject({ organizationId: "a", projectId: "p" });
  assert.equal(controller.getState().selectedProjectId, undefined);
  assert.deepEqual(controller.getState().projects.input.projects.map(row => row.id), ["q"]); controller.dispose();
});

test("pagination invalidates an in-flight project success and its old callbacks", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  await ready(controller, api, organizations(["a"], "NEXT"));
  controller.selectOrganization("a"); const old = api.calls.at(-1);
  controller.nextOrganizations("NEXT"); assert.equal(old.signal.aborted, true);
  old.resolve(projects()); await flush(); assertEmpty(controller.getState(), "loading");
  api.calls.at(-1).resolve(organizations(["b"])); await flush();
  controller.retryProjects("a"); controller.nextProjects({ organizationId: "a", cursor: "NEXT" });
  controller.selectProject({ organizationId: "a", projectId: "p" }); assert.equal(api.calls.length, 3);
  assert.equal(controller.getState().selectedProjectId, undefined); controller.dispose();
});

test("replacing a session with the same client invalidates a noncooperative organization response", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  controller.setSession({ kind: "ready", client: api.client }); const old = api.calls[0];
  controller.setSession({ kind: "ready", client: api.client });
  assert.equal(old.signal.aborted, true); assert.equal(api.calls.length, 2);
  old.resolve(organizations(["old"])); await flush(); assertEmpty(controller.getState(), "loading");
  api.calls[1].resolve(organizations(["new"])); await flush();
  assert.deepEqual(controller.getState().organizations.input.organizations.map(row => row.id), ["new"]); controller.dispose();
});

test("session replacement clears ready pages and selection before notifications", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  await ready(controller, api); await selected(controller, api);
  controller.selectProject({ organizationId: "a", projectId: "p" });
  const observed = []; const stop = controller.subscribe(state => observed.push(state));
  controller.setSession({ kind: "ready", client: api.client });
  assertEmpty(observed.at(-1), "loading"); assertEmpty(controller.getState(), "loading");
  api.calls.at(-1).resolve(organizations()); await flush();
  assert.equal(controller.getState().selectedOrganizationId, undefined); stop(); controller.dispose();
});

test("logout/unavailability abort old projects and late success or failure cannot restore state", async () => {
  for (const kind of ["unauthenticated", "unavailable"]) {
    for (const completion of ["success", "failure"]) {
      const controller = createWorkspaceController(); const api = controlled(); await ready(controller, api);
      controller.selectOrganization("a"); const old = api.calls.at(-1);
      controller.setSession({ kind }); assert.equal(old.signal.aborted, true); assertEmpty(controller.getState(), kind);
      if (completion === "success") old.resolve(projects()); else old.reject(new WorkspaceClientError("unauthenticated"));
      await flush(); assertEmpty(controller.getState(), kind);
      controller.retryOrganizations(); controller.retryProjects("a"); assert.equal(api.calls.length, 2); controller.dispose();
    }
  }
});

test("stale authentication failure cannot clear a replacement session or new organization scope", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  controller.setSession({ kind: "ready", client: api.client }); const oldSession = api.calls[0];
  await ready(controller, api); controller.selectOrganization("a"); const oldScope = api.calls.at(-1);
  controller.selectOrganization("b"); oldSession.reject(new WorkspaceClientError("unauthenticated"));
  oldScope.reject(new WorkspaceClientError("unauthenticated")); await flush();
  assert.equal(controller.getState().selectedOrganizationId, "b"); assert.equal(controller.getState().projects.kind, "loading");
  api.calls.at(-1).resolve(projects("b")); await flush(); assert.equal(controller.getState().projects.kind, "ready"); controller.dispose();
});

test("current authentication failure clears the entire session and prevents retries", async () => {
  for (const list of ["organizations", "projects"]) {
    const controller = createWorkspaceController(); const api = controlled();
    if (list === "organizations") controller.setSession({ kind: "ready", client: api.client });
    else { await ready(controller, api); controller.selectOrganization("a"); }
    const active = api.calls.at(-1); active.reject(new WorkspaceClientError("unauthenticated")); await flush();
    assertEmpty(controller.getState(), "unauthenticated"); assert.equal(active.signal.aborted, true);
    const count = api.calls.length; controller.retryOrganizations(); controller.retryProjects("a");
    assert.equal(api.calls.length, count); controller.dispose();
  }
});

test("fixed errors map per list without copying exception data", async () => {
  const reasons = ["permission_denied", "not_found", "unavailable", "invalid_response", "invalid_request", "aborted", "unknown"];
  for (const list of ["organizations", "projects"]) {
    for (const code of reasons) {
      const controller = createWorkspaceController(); const api = controlled();
      if (list === "organizations") controller.setSession({ kind: "ready", client: api.client });
      else { await ready(controller, api); controller.selectOrganization("a"); }
      const error = code === "unknown" ? Object.assign(new Error("secret token, body and URL"), { code: "unauthenticated" }) : new WorkspaceClientError(code);
      error.message = "secret token, body and URL"; api.calls.at(-1).reject(error); await flush();
      const value = controller.getState()[list];
      const scope = list === "projects" ? { organizationId: "a" } : {};
      assert.deepEqual(value, code === "unavailable" ? { kind: "unavailable", ...scope } :
        { kind: "error", reason: ["permission_denied", "not_found"].includes(code) ? code : "request_failed", ...scope });
      assert.equal(JSON.stringify(controller.getState()).includes("secret"), false);
      if (list === "projects") assert.equal(controller.getState().selectedOrganizationId, "a");
      controller.dispose();
    }
  }
});

test("organization retry retains canonical failed page and repeated loading retries are inert", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  controller.setSession({ kind: "ready", client: api.client }); api.calls[0].reject(new WorkspaceClientError("unavailable")); await flush();
  controller.retryOrganizations(); controller.retryOrganizations(); assert.equal(api.calls.length, 2); assert.deepEqual(api.calls[1].page, {});
  api.calls[1].resolve(organizations(["a"], "CANONICAL_1")); await flush();
  controller.nextOrganizations("CANONICAL_1"); api.calls[2].reject(new WorkspaceClientError("not_found")); await flush();
  controller.nextOrganizations("CANONICAL_1"); assert.equal(api.calls.length, 3);
  controller.retryOrganizations(); controller.retryOrganizations(); assert.equal(api.calls.length, 4);
  assert.deepEqual(api.calls[3].page, { cursor: "CANONICAL_1" }); assert.ok(Object.isFrozen(api.calls[3].page));
  api.calls[3].resolve(organizations(["b"])); await flush();
  controller.retryOrganizations(); assert.equal(api.calls.length, 4); controller.dispose();
});

test("project retry retains failed page, validates current scope and resets on organization change", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  await ready(controller, api); await selected(controller, api, "a", projects("a", ["p"], "CANONICAL_2"));
  controller.nextProjects({ organizationId: "a", cursor: "CANONICAL_2" });
  api.calls.at(-1).reject(new WorkspaceClientError("unavailable")); await flush();
  controller.retryProjects("b"); assert.equal(api.calls.length, 3);
  controller.retryProjects("a"); controller.retryProjects("a"); assert.equal(api.calls.length, 4);
  assert.equal(api.calls[3].organizationId, "a"); assert.deepEqual(api.calls[3].page, { cursor: "CANONICAL_2" });
  api.calls[3].reject(new WorkspaceClientError("permission_denied")); await flush();
  controller.selectOrganization("b"); controller.retryProjects("a"); assert.equal(api.calls.length, 5);
  assert.deepEqual(api.calls[4].page, {}); api.calls[4].reject(new WorkspaceClientError("not_found")); await flush();
  controller.retryProjects("b"); assert.deepEqual(api.calls[5].page, {}); controller.dispose();
});

test("controller reparses, copies and deeply freezes client pages against later mutation", async () => {
  const controller = createWorkspaceController(); const api = controlled(); const original = organizations();
  await ready(controller, api, original); const first = controller.getState();
  original.organizations[0].id = "changed"; original.organizations[0].organization_roles.push("viewer"); original.organizations.length = 0;
  assert.equal(first.organizations.input.organizations[0].id, "a");
  assert.ok(Object.isFrozen(first.organizations.input)); assert.ok(Object.isFrozen(first.organizations.input.organizations));
  assert.ok(Object.isFrozen(first.organizations.input.organizations[0])); assert.ok(Object.isFrozen(first.organizations.input.organizations[0].organization_roles));
  const originalProjects = projects(); await selected(controller, api, "a", originalProjects);
  const second = controller.getState(); originalProjects.projects[0].organization_id = "b"; originalProjects.projects[0].roles.push("owner");
  assert.equal(second.projects.input.projects[0].organization_id, "a");
  assert.deepEqual(second.projects.input.projects[0].roles, ["viewer"]);
  assert.ok(Object.isFrozen(second.projects.input.projects[0].roles));
  assert.throws(() => { second.selectedOrganizationId = "b"; }, TypeError);
  assert.throws(() => { second.projects.input.projects[0].id = "changed"; }, TypeError);
  assert.equal(first.projects.kind, "unselected"); controller.dispose();
});

test("malformed or foreign-scope client pages fail closed with no prior rows or selection", async () => {
  const badOrganizations = [null, { ...organizations(), extra: true }, organizations(["duplicate", "duplicate"]), organizations([], "CURSOR")];
  for (const page of badOrganizations) {
    const controller = createWorkspaceController(); const api = controlled(); await ready(controller, api, page);
    assert.deepEqual(controller.getState(), { organizations: { kind: "error", reason: "request_failed" }, projects: { kind: "unselected" } });
    controller.dispose();
  }
  const controller = createWorkspaceController(); const api = controlled(); await ready(controller, api);
  await selected(controller, api, "a", projects("a", ["p"], "NEXT")); controller.selectProject({ organizationId: "a", projectId: "p" });
  controller.nextProjects({ organizationId: "a", cursor: "NEXT" }); api.calls.at(-1).resolve(projects("b")); await flush();
  assert.deepEqual(controller.getState().projects, { kind: "error", organizationId: "a", reason: "request_failed" });
  assert.equal(controller.getState().selectedProjectId, undefined); controller.dispose();
});

test("sync-throwing clients and hostile errors produce safe states without unhandled rejections", async () => {
  const unhandled = []; const listener = reason => unhandled.push(reason); process.on("unhandledRejection", listener);
  try {
    for (const mode of ["throw", "reject", "proxy"]) {
      const controller = createWorkspaceController();
      const unsafe = mode === "proxy" ? new Proxy({}, { getPrototypeOf() { throw new Error("secret"); } }) : new Error("secret");
      controller.setSession({ kind: "ready", client: {
        organizations() { if (mode === "reject") return Promise.reject(unsafe); throw unsafe; },
        projects() { throw new Error("unused"); },
      } });
      await flush(); assert.deepEqual(controller.getState().organizations, { kind: "error", reason: "request_failed" }); controller.dispose();
    }
    const controller = createWorkspaceController(); const api = controlled(); await ready(controller, api);
    api.client.projects = () => { throw new WorkspaceClientError("not_found"); };
    controller.selectOrganization("a"); await flush();
    assert.deepEqual(controller.getState().projects, { kind: "error", organizationId: "a", reason: "not_found" });
    controller.dispose(); await flush(); assert.deepEqual(unhandled, []);
  } finally { process.off("unhandledRejection", listener); }
});

test("reentrant response validation cannot commit a page after logout", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  controller.setSession({ kind: "ready", client: api.client }); const page = organizations();
  Object.defineProperty(page.organizations[0], "display_name", { enumerable: true, get() {
    controller.setSession({ kind: "unauthenticated" }); return null;
  } });
  api.calls[0].resolve(page); await flush(); assertEmpty(controller.getState(), "unauthenticated"); controller.dispose();
});

test("subscriptions deliver immediately, unsubscribe independently and isolate observer failures", async () => {
  const controller = createWorkspaceController(); const api = controlled(); const received = [];
  const unhandled = []; const onUnhandled = value => unhandled.push(value); process.on("unhandledRejection", onUnhandled);
  try {
    const stopBroken = controller.subscribe(() => { throw new Error("observer"); });
    const stopRejected = controller.subscribe(async () => { throw new Error("async observer"); });
    const listener = state => received.push(state); const stopOne = controller.subscribe(listener); const stopTwo = controller.subscribe(listener);
    assert.equal(received.length, 2); assert.equal(received[0], controller.getState());
    stopOne(); stopOne(); await ready(controller, api); assert.equal(received.length, 4);
    stopTwo(); stopBroken(); stopRejected(); const count = received.length;
    controller.setSession({ kind: "unauthenticated" }); await flush(); assert.equal(received.length, count); assert.deepEqual(unhandled, []);
  } finally { controller.dispose(); process.off("unhandledRejection", onUnhandled); }
});

test("nested subscriber actions supersede older notifications and never start invalidated requests", () => {
  const controller = createWorkspaceController(); const api = controlled(); const seen = [];
  controller.subscribe(state => {
    if (state.organizations.kind === "loading") controller.setSession({ kind: "unauthenticated" });
  });
  controller.subscribe(state => seen.push(state.organizations.kind));
  controller.setSession({ kind: "ready", client: api.client });
  assert.deepEqual(seen, ["unavailable", "unauthenticated"]); assert.equal(api.calls.length, 0);
  assertEmpty(controller.getState(), "unauthenticated"); controller.dispose();
});

test("subscriptions added or removed during notification observe only current live revisions", () => {
  const controller = createWorkspaceController(); const seen = []; let stopLater; let added = false;
  controller.subscribe(state => {
    if (state.organizations.kind !== "unauthenticated") return;
    stopLater();
    if (!added) { added = true; controller.subscribe(value => seen.push(`added:${value.organizations.kind}`)); }
  });
  stopLater = controller.subscribe(state => seen.push(`later:${state.organizations.kind}`));
  controller.setSession({ kind: "unauthenticated" });
  assert.deepEqual(seen, ["later:unavailable", "added:unauthenticated"]); controller.dispose();
});

test("abort-handler reentrancy sees coherent cleared state and supersedes the outer session", async () => {
  const controller = createWorkspaceController(); const api = controlled();
  controller.setSession({ kind: "ready", client: api.client }); const old = api.calls[0];
  old.signal.addEventListener("abort", () => {
    assertEmpty(controller.getState(), "loading"); controller.setSession({ kind: "unauthenticated" });
  }, { once: true });
  controller.setSession({ kind: "ready", client: api.client });
  assert.equal(api.calls.length, 1); assertEmpty(controller.getState(), "unauthenticated");
  old.resolve(organizations()); await flush(); assertEmpty(controller.getState(), "unauthenticated"); controller.dispose();
});

test("disposal aborts and clears, suppresses late completions, and makes every action inert", async () => {
  for (const completion of ["success", "failure"]) {
    const controller = createWorkspaceController(); const api = controlled(); const seen = [];
    await ready(controller, api); controller.subscribe(state => seen.push(state)); controller.selectOrganization("a");
    const old = api.calls.at(-1); const notifications = seen.length; controller.dispose();
    assert.equal(old.signal.aborted, true); assertEmpty(controller.getState(), "unavailable");
    const state = controller.getState(); controller.dispose();
    controller.setSession({ kind: "ready", client: api.client }); controller.setSession({ kind: "unauthenticated" });
    controller.selectOrganization("a"); controller.selectProject({ organizationId: "a", projectId: "p" });
    controller.nextOrganizations("NEXT"); controller.nextProjects({ organizationId: "a", cursor: "NEXT" });
    controller.retryOrganizations(); controller.retryProjects("a"); controller.subscribe(() => { throw new Error("called after disposal"); })();
    if (completion === "success") old.resolve(projects()); else old.reject(new WorkspaceClientError("unauthenticated"));
    await flush(); assert.equal(controller.getState(), state); assert.equal(seen.length, notifications); assert.equal(api.calls.length, 2);
  }
});

test("disposal inside notification prevents later observers and starts no request", () => {
  const controller = createWorkspaceController(); const api = controlled(); const seen = [];
  controller.subscribe(state => { if (state.organizations.kind === "loading") controller.dispose(); });
  controller.subscribe(state => seen.push(state.organizations.kind));
  controller.setSession({ kind: "ready", client: api.client });
  assert.deepEqual(seen, ["unavailable"]); assert.equal(api.calls.length, 0); assertEmpty(controller.getState(), "unavailable");
});

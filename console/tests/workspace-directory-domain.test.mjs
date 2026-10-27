import assert from "node:assert/strict";
import test from "node:test";
import { isWorkspaceIdentifier, parseWorkspaceOrganizations, parseWorkspaceProjects, resolveWorkspaceDirectory,
  workspaceDisplayName, workspaceIdentifierMarker } from "../src/domain/workspace-directory.ts";

const roles = ["administrator", "billing_manager", "developer", "owner", "release_manager", "viewer"];
const org = (id = "org:北/..", organization_roles = []) => ({ id, display_name: "Studio & Co", organization_roles });
const project = (id = "project:fieldlog", organization_id = "org:北/..") => ({ organization_id, id, display_name: "FieldLog", roles: ["developer"] });
const organizations = (rows = [org()], next_cursor = null) => ({ organizations: rows, next_cursor });
const projects = (rows = [project()], next_cursor = null) => ({ projects: rows, next_cursor });
const input = () => ({ organizations: { kind: "ready", input: organizations() },
  projects: { kind: "ready", organizationId: "org:北/..", input: projects() },
  selectedOrganizationId: "org:北/..", selectedProjectId: "project:fieldlog" });

test("workspace boundary keeps exact Unicode IDs, names and all six sorted roles without adding organization grants", () => {
  const page = parseWorkspaceOrganizations(organizations([org(), org("admin", roles)]));
  assert.deepEqual(page.organizations[0], org());
  assert.deepEqual(page.organizations[1].organization_roles, roles);
  assert.equal(page.organizations[0].organization_roles.length, 0);
  assert.deepEqual(parseWorkspaceProjects(projects([{ ...project(), roles }]), "org:北/..").projects[0].roles, roles);
  for (const id of [".", "..", "a/b", "a:b", "\"<&>", " ", "é".repeat(64), "😀".repeat(32)]) {
    const row = parseWorkspaceOrganizations(organizations([{ ...org(id), display_name: null }])).organizations[0];
    assert.equal(row.id, id); assert.equal(workspaceDisplayName(row), id);
    const p = parseWorkspaceProjects(projects([project(id, id)]), id).projects[0];
    assert.equal(p.id, id); assert.equal(p.organization_id, id);
  }
});

test("display names preserve supplied spacing and wildcard; only null falls back to the identifier", () => {
  for (const name of ["*", "  Studio  ", "é".repeat(128), "😀".repeat(64)]) {
    const row = parseWorkspaceOrganizations(organizations([{ ...org(), display_name: name }])).organizations[0];
    assert.equal(row.display_name, name); assert.equal(workspaceDisplayName(row), name);
  }
  assert.equal(workspaceDisplayName({ id: "org", display_name: null }), "org");
});

test("whitespace identity markers distinguish exact identifiers without changing snapshots, selections or stored names", () => {
  for (const [id, marker] of [[" ", '"\\u0020"'], ["  ", '"\\u0020\\u0020"'],
    ["\u00a0", '"\\u00a0"'], ["\u1680", '"\\u1680"'], ["\u2003\u3000", '"\\u2003\\u3000"'],
    ["\u2028\u2029", '"\\u2028\\u2029"'], ["\ufeff", '"\\ufeff"']]) {
    assert.equal(isWorkspaceIdentifier(id), true);
    assert.equal(workspaceIdentifierMarker(id), marker);
    const state = { organizations: { kind: "ready", input: organizations([{ ...org(id), display_name: null }]) },
      projects: { kind: "ready", organizationId: id, input: projects([{ ...project(id, id), display_name: null }]) },
      selectedOrganizationId: id, selectedProjectId: id };
    const view = resolveWorkspaceDirectory(state);
    assert.equal(view.selectedOrganization.id, id); assert.equal(view.selectedProject.id, id);
    assert.equal(view.selectedProject.organization_id, id);
    assert.equal(workspaceDisplayName(view.selectedOrganization), id);
    assert.equal(workspaceDisplayName(view.selectedProject), id);
  }
  for (const id of ["org", " Studio ", ".", "..", "é", "a/b:c"]) assert.equal(workspaceIdentifierMarker(id), null);
  for (const display_name of ["  ", "\u00a0", "  Studio  ", "*"]) {
    assert.equal(workspaceDisplayName({ id: " ", display_name }), display_name);
  }
});

test("both page boundaries reject unknown/missing fields, duplicates and overfull pages", () => {
  for (const value of [null, {}, { ...organizations(), extra: true }, { organizations: [] },
    organizations([null]), organizations(new Array(1)), organizations([org(), org()]), organizations(Array.from({ length: 101 }, (_, i) => org(`org-${i}`))),
    organizations([{ ...org(), roles: ["owner"] }]), organizations([{ id: "org", organization_roles: [] }])]) {
    assert.throws(() => parseWorkspaceOrganizations(value), TypeError);
  }
  for (const value of [null, {}, { ...projects(), extra: true }, { projects: [] }, projects([null]), projects(new Array(1)),
    projects([project(), project()]), projects(Array.from({ length: 101 }, (_, i) => project(`project-${i}`))),
    projects([{ ...project(), organization_roles: ["owner"] }]), projects([{ id: "p", organization_id: "org:北/..", roles: ["viewer"] }])]) {
    assert.throws(() => parseWorkspaceProjects(value, "org:北/.."), TypeError);
  }
});

test("full identifier and display text limits reject controls, invalid Unicode and overflow", () => {
  for (const id of ["", "*", "x".repeat(129), "é".repeat(65), "😀".repeat(33), "a\u0000", "a\n", "a\t", "a\u007f", "a\u0080", "a\u009f", "\ud800", "\udc00", "\ufffe", "\uffff", 3, null]) {
    assert.throws(() => parseWorkspaceOrganizations(organizations([org(id)])), TypeError, String(id));
    assert.throws(() => parseWorkspaceProjects(projects([project(id)]), "org:北/.."), TypeError, String(id));
    assert.throws(() => parseWorkspaceProjects(projects([]), id), TypeError, String(id));
  }
  for (const display_name of ["", "x".repeat(257), "é".repeat(129), "😀".repeat(65), "a\n", "a\u007f", "a\u009f", "\ud800", "\ufffe", 4, {}, undefined]) {
    assert.throws(() => parseWorkspaceOrganizations(organizations([{ ...org(), display_name }])), TypeError);
    assert.throws(() => parseWorkspaceProjects(projects([{ ...project(), display_name }]), "org:北/.."), TypeError);
  }
});

test("organization roles may be empty but project roles must be canonical, sorted, unique and nonempty", () => {
  for (const bad of [["admin"], ["owner", "owner"], ["owner", "developer"], [null], "owner", undefined, Array(7).fill("owner")]) {
    assert.throws(() => parseWorkspaceOrganizations(organizations([{ ...org("org"), organization_roles: bad }])), TypeError);
    assert.throws(() => parseWorkspaceProjects(projects([{ ...project(), roles: bad }]), "org:北/.."), TypeError);
  }
  assert.throws(() => parseWorkspaceProjects(projects([{ ...project(), roles: [] }]), "org:北/.."), TypeError);
  assert.equal(parseWorkspaceOrganizations(organizations([org()])).organizations[0].organization_roles.length, 0);
});

test("pagination is a bounded opaque cursor and is never decoded, rewritten or treated as a total", () => {
  for (const next_cursor of [null, "opaque_-09AZ", "a".repeat(1400)]) {
    assert.equal(parseWorkspaceOrganizations(organizations([org()], next_cursor)).next_cursor, next_cursor);
    assert.equal(parseWorkspaceProjects(projects([project()], next_cursor), "org:北/..").next_cursor, next_cursor);
  }
  for (const next_cursor of ["", "a".repeat(1401), "padded=", "+", "/", "%2F", "a b", "é", 1, {}, undefined]) {
    assert.throws(() => parseWorkspaceOrganizations({ ...organizations([org()]), next_cursor }), TypeError);
    assert.throws(() => parseWorkspaceProjects({ ...projects([project()]), next_cursor }, "org:北/.."), TypeError);
  }
  assert.equal(parseWorkspaceOrganizations(organizations([])).next_cursor, null);
  assert.equal(parseWorkspaceProjects(projects([]), "org:北/..").next_cursor, null);
  assert.throws(() => parseWorkspaceOrganizations(organizations([], "opaque")), TypeError);
  assert.throws(() => parseWorkspaceProjects(projects([], "opaque"), "org:北/.."), TypeError);
});

test("every project row must match the exact selected organization", () => {
  for (const organization_id of ["other", "org:北/../", null, undefined]) {
    assert.throws(() => parseWorkspaceProjects(projects([{ ...project("p"), organization_id }]), "org:北/.."), TypeError);
  }
  assert.throws(() => parseWorkspaceProjects(projects([project(), project("p", "other")]), "org:北/.."), TypeError);
});

test("snapshots are deeply copied and frozen without mutating caller-owned input", () => {
  const source = organizations([org("org", ["owner"])]); const page = parseWorkspaceOrganizations(source);
  source.organizations[0].display_name = "Changed"; source.organizations[0].organization_roles[0] = "viewer";
  source.organizations.push(org("other"));
  assert.equal(page.organizations[0].display_name, "Studio & Co");
  assert.deepEqual(page.organizations[0].organization_roles, ["owner"]);
  assert.equal(page.organizations.length, 1);
  const sourceProjects = projects(); const projectPage = parseWorkspaceProjects(sourceProjects, "org:北/..");
  sourceProjects.projects[0].roles.push("viewer"); sourceProjects.projects[0].id = "changed";
  assert.equal(projectPage.projects[0].id, "project:fieldlog"); assert.deepEqual(projectPage.projects[0].roles, ["developer"]);
  for (const value of [page, page.organizations, page.organizations[0], page.organizations[0].organization_roles,
    projectPage, projectPage.projects, projectPage.projects[0], projectPage.projects[0].roles]) assert.equal(Object.isFrozen(value), true);
});

test("selection resolves only current validated rows and never manufactures roles or project access", () => {
  let state = input(); let view = resolveWorkspaceDirectory(state);
  assert.equal(view.selectedOrganization.id, "org:北/.."); assert.equal(view.selectedProject.id, "project:fieldlog");
  assert.deepEqual(view.selectedOrganization.organization_roles, []);
  state.projects.input = projects([]); view = resolveWorkspaceDirectory(state);
  assert.equal(view.projects.kind, "ready"); assert.equal(view.selectedProject, null);
  state = input(); delete state.selectedOrganizationId; view = resolveWorkspaceDirectory(state);
  assert.equal(view.projects.kind, "unselected"); assert.equal(view.selectedProject, null);
  state = input(); state.selectedOrganizationId = "other"; view = resolveWorkspaceDirectory(state);
  assert.equal(view.selectedOrganization, null); assert.equal(view.projects.kind, "unselected");
  state = input(); state.selectedProjectId = "missing"; assert.equal(resolveWorkspaceDirectory(state).selectedProject, null);
});

test("switching organization hides stale project payloads and selections, including failure states", () => {
  for (const projectState of [
    { kind: "ready", input: projects() }, { kind: "loading" }, { kind: "error", reason: "permission_denied" },
    { kind: "unauthenticated" }, { kind: "unavailable" },
  ]) {
    const state = input(); state.organizations.input = organizations([org(), org("other", ["viewer"])]);
    state.selectedOrganizationId = "other"; state.projects = { ...projectState, organizationId: "org:北/.." };
    const view = resolveWorkspaceDirectory(state);
    assert.equal(view.selectedOrganization.id, "other"); assert.equal(view.projects.kind, "invalid");
    assert.equal(view.selectedProject, null);
  }
  const state = input(); state.projects.input.projects[0].organization_id = "other";
  assert.equal(resolveWorkspaceDirectory(state).projects.kind, "invalid");
});

test("loading, authentication, unavailable and errors replace stale selections without retaining rows", () => {
  for (const kind of ["loading", "unauthenticated", "unavailable", "error"]) {
    const state = input(); state.organizations = kind === "error" ? { kind, reason: "request_failed" } : { kind };
    const view = resolveWorkspaceDirectory(state);
    assert.equal(view.organizations.kind, kind); assert.equal(view.projects.kind, "unselected");
    assert.equal(view.selectedOrganization, null); assert.equal(view.selectedProject, null);
    state.organizations = input().organizations;
    state.projects = { ...state.organizations, kind, organizationId: "org:北/..", ...(kind === "error" ? { reason: "request_failed" } : {}) };
    delete state.projects.input;
    const projectView = resolveWorkspaceDirectory(state);
    assert.equal(projectView.projects.kind, kind); assert.equal(projectView.selectedProject, null);
  }
});

test("malformed ready data and unsupported controlled states fail closed", () => {
  for (const organizations of [null, undefined, { kind: "unknown" }, { kind: "error", reason: "internal_dump" },
    { kind: "ready", input: null }, { kind: "loading", input: input().organizations.input }]) {
    const state = input(); state.organizations = organizations;
    const view = resolveWorkspaceDirectory(state);
    assert.equal(view.organizations.kind, "invalid"); assert.equal(view.projects.kind, "unselected");
    assert.equal(view.selectedProject, null);
  }
  for (const projects of [null, undefined, { kind: "unselected" }, { kind: "ready", organizationId: "org:北/..", input: {} },
    { kind: "error", organizationId: "org:北/..", reason: "internal_dump" }]) {
    const state = input(); state.projects = projects;
    assert.equal(resolveWorkspaceDirectory(state).projects.kind, "invalid");
  }
  assert.equal(resolveWorkspaceDirectory(null).organizations.kind, "invalid");
});

test("first-page availability accepts only explicit flags and current valid organization scope", () => {
  for (const flag of [undefined, false, "true", 1, {}, null]) {
    const state = input(); state.canReturnToFirstOrganizations = flag; state.canReturnToFirstProjects = flag;
    const view = resolveWorkspaceDirectory(state);
    assert.equal(view.canReturnToFirstOrganizations, false); assert.equal(view.canReturnToFirstProjects, false);
  }
  for (const kind of ["ready", "loading", "error", "unavailable"]) {
    const state = input(); state.canReturnToFirstOrganizations = true; state.canReturnToFirstProjects = true;
    if (kind !== "ready") state.projects = { kind, organizationId: "org:北/..", ...(kind === "error" ? { reason: "not_found" } : {}) };
    let view = resolveWorkspaceDirectory(state);
    assert.equal(view.canReturnToFirstOrganizations, true); assert.equal(view.canReturnToFirstProjects, true);
    state.projects.organizationId = "other"; view = resolveWorkspaceDirectory(state);
    assert.equal(view.canReturnToFirstProjects, false);
    state.organizations = kind === "ready" ? { kind, input: null } :
      { kind, ...(kind === "error" ? { reason: "request_failed" } : {}) };
    view = resolveWorkspaceDirectory(state);
    assert.equal(view.canReturnToFirstOrganizations, kind !== "ready"); assert.equal(view.canReturnToFirstProjects, false);
  }
  const state = input(); state.canReturnToFirstOrganizations = true; state.canReturnToFirstProjects = true;
  state.projects = { kind: "unauthenticated", organizationId: "org:北/.." };
  assert.equal(resolveWorkspaceDirectory(state).canReturnToFirstProjects, false);
  state.organizations = { kind: "unauthenticated" };
  assert.equal(resolveWorkspaceDirectory(state).canReturnToFirstOrganizations, false);
});

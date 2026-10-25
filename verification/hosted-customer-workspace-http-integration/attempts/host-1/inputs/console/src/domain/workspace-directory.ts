export type WorkspaceRole = "owner" | "administrator" | "developer" | "release_manager" | "billing_manager" | "viewer";

export interface WorkspaceOrganization {
  readonly id: string;
  readonly display_name: string | null;
  /** Organization grants only. Project membership never becomes an organization role. */
  readonly organization_roles: readonly WorkspaceRole[];
}

export interface WorkspaceProject {
  readonly organization_id: string;
  readonly id: string;
  readonly display_name: string | null;
  readonly roles: readonly WorkspaceRole[];
}

export interface WorkspaceOrganizationPage {
  readonly organizations: readonly WorkspaceOrganization[];
  readonly next_cursor: string | null;
}

export interface WorkspaceProjectPage {
  readonly projects: readonly WorkspaceProject[];
  readonly next_cursor: string | null;
}

export type WorkspaceFailure = "permission_denied" | "not_found" | "request_failed";
type LoadState =
  | { readonly kind: "loading" }
  | { readonly kind: "unauthenticated" }
  | { readonly kind: "unavailable" }
  | { readonly kind: "error"; readonly reason: WorkspaceFailure };
export type WorkspaceOrganizationsState = LoadState | { readonly kind: "ready"; readonly input: unknown };
export type WorkspaceProjectsState = { readonly kind: "unselected" } |
  ((LoadState | { readonly kind: "ready"; readonly input: unknown }) & { readonly organizationId: string });

export interface WorkspaceDirectoryState {
  readonly organizations: WorkspaceOrganizationsState;
  readonly projects: WorkspaceProjectsState;
  readonly selectedOrganizationId?: string;
  readonly selectedProjectId?: string;
}

type OrganizationView = LoadState | { readonly kind: "invalid" } |
  { readonly kind: "ready"; readonly page: WorkspaceOrganizationPage };
type ProjectView = LoadState | { readonly kind: "invalid" } | { readonly kind: "unselected" } |
  { readonly kind: "ready"; readonly page: WorkspaceProjectPage };
export interface WorkspaceDirectoryView {
  readonly organizations: OrganizationView;
  readonly projects: ProjectView;
  readonly selectedOrganization: WorkspaceOrganization | null;
  readonly selectedProject: WorkspaceProject | null;
}

const roles: readonly string[] = ["administrator", "billing_manager", "developer", "owner", "release_manager", "viewer"];
const failures: readonly string[] = ["permission_denied", "not_found", "request_failed"];

function requireValid(value: boolean, reason: string): asserts value {
  if (!value) throw new TypeError(reason);
}

function object(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    keys.every(key => Object.hasOwn(value, key)) && Object.keys(value).length === keys.length;
}

/** Match Scope.identifier? and the display-name contract without trimming or normalizing. */
function printable(value: unknown, maximum: number): value is string {
  if (typeof value !== "string" || value.length === 0 || value.length > maximum) return false;
  let bytes = 0;
  for (const character of value) {
    const code = character.codePointAt(0)!;
    if (!((code >= 0x20 && code <= 0x7e) || (code >= 0xa0 && code <= 0xd7ff) ||
      (code >= 0xe000 && code <= 0xfffd) || (code >= 0x10000 && code <= 0x10ffff))) return false;
    bytes += code <= 0x7f ? 1 : code <= 0x7ff ? 2 : code <= 0xffff ? 3 : 4;
    if (bytes > maximum) return false;
  }
  return true;
}

export function isWorkspaceIdentifier(value: unknown): value is string {
  return printable(value, 128) && value !== "*";
}

function displayName(value: unknown): value is string | null {
  return value === null || printable(value, 256);
}

function cursor(value: unknown): value is string | null {
  return value === null || (typeof value === "string" && value.length <= 1400 && /^[A-Za-z0-9_-]+$/u.test(value));
}

function copyRoles(value: unknown, allowEmpty: boolean): readonly WorkspaceRole[] {
  requireValid(Array.isArray(value) && value.length <= roles.length && (allowEmpty || value.length > 0), "Invalid workspace roles");
  let previous: string | undefined;
  for (const role of value) {
    requireValid(typeof role === "string" && roles.includes(role) && (previous === undefined || previous < role), "Invalid workspace role order");
    previous = role;
  }
  return Object.freeze([...value]) as readonly WorkspaceRole[];
}

/** Strict, bounded customer API boundary. Rows convey visibility, never release authority. */
export function parseWorkspaceOrganizations(input: unknown): WorkspaceOrganizationPage {
  requireValid(object(input, ["organizations", "next_cursor"]) && Array.isArray(input.organizations) &&
    input.organizations.length <= 100 && cursor(input.next_cursor) &&
    (input.organizations.length > 0 || input.next_cursor === null), "Invalid organization page");
  const ids = new Set<string>();
  const organizations = Array.from(input.organizations, value => {
    requireValid(object(value, ["id", "display_name", "organization_roles"]) && isWorkspaceIdentifier(value.id) &&
      displayName(value.display_name) && !ids.has(value.id), "Invalid organization row");
    ids.add(value.id);
    return Object.freeze({ id: value.id, display_name: value.display_name,
      organization_roles: copyRoles(value.organization_roles, true) });
  });
  return Object.freeze({ organizations: Object.freeze(organizations), next_cursor: input.next_cursor });
}

/** A project page is valid only for the organization selected by the caller. */
export function parseWorkspaceProjects(input: unknown, organizationId: string): WorkspaceProjectPage {
  requireValid(isWorkspaceIdentifier(organizationId), "Invalid selected organization");
  requireValid(object(input, ["projects", "next_cursor"]) && Array.isArray(input.projects) &&
    input.projects.length <= 100 && cursor(input.next_cursor) &&
    (input.projects.length > 0 || input.next_cursor === null), "Invalid project page");
  const ids = new Set<string>();
  const projects = Array.from(input.projects, value => {
    requireValid(object(value, ["organization_id", "id", "display_name", "roles"]) &&
      value.organization_id === organizationId && isWorkspaceIdentifier(value.id) && displayName(value.display_name) &&
      !ids.has(value.id), "Invalid project row");
    ids.add(value.id);
    return Object.freeze({ organization_id: organizationId, id: value.id, display_name: value.display_name,
      roles: copyRoles(value.roles, false) });
  });
  return Object.freeze({ projects: Object.freeze(projects), next_cursor: input.next_cursor });
}

export function workspaceDisplayName(row: { readonly id: string; readonly display_name: string | null }): string {
  return row.display_name ?? row.id;
}

/** A visible identity annotation only; never use it as a request or selection ID. */
export function workspaceIdentifierMarker(identifier: string): string | null {
  if (!/^\s+$/u.test(identifier)) return null;
  return `"${Array.from(identifier, character => `\\u${character.codePointAt(0)!.toString(16).padStart(4, "0")}`).join("")}"`;
}

function loadState(value: Record<string, unknown>, scoped: boolean): LoadState | null {
  const keys = scoped ? ["kind", "organizationId"] : ["kind"];
  if (["loading", "unauthenticated", "unavailable"].includes(value.kind as string) && object(value, keys)) {
    return Object.freeze({ kind: value.kind }) as LoadState;
  }
  if (value.kind === "error" && object(value, [...keys, "reason"]) && failures.includes(value.reason as string)) {
    return Object.freeze({ kind: "error", reason: value.reason as WorkspaceFailure });
  }
  return null;
}

/** Resolve controlled selection against the current validated pages; stale scopes stay hidden. */
export function resolveWorkspaceDirectory(input: WorkspaceDirectoryState): WorkspaceDirectoryView {
  let organizations: OrganizationView = { kind: "invalid" };
  let projects: ProjectView = { kind: "unselected" };
  let selectedOrganization: WorkspaceOrganization | null = null;
  let selectedProject: WorkspaceProject | null = null;
  try {
    const state = input.organizations;
    if (object(state, ["kind", "input"]) && state.kind === "ready") {
      organizations = { kind: "ready", page: parseWorkspaceOrganizations(state.input) };
      selectedOrganization = organizations.page.organizations.find(row => row.id === input.selectedOrganizationId) ?? null;
    } else if (state && typeof state === "object") {
      organizations = loadState(state as unknown as Record<string, unknown>, false) ?? { kind: "invalid" };
    }
    if (selectedOrganization) {
      projects = { kind: "invalid" };
      const state = input.projects;
      if (state && typeof state === "object" && "organizationId" in state && state.organizationId === selectedOrganization.id) {
        if (object(state, ["kind", "organizationId", "input"]) && state.kind === "ready") {
          projects = { kind: "ready", page: parseWorkspaceProjects(state.input, selectedOrganization.id) };
          selectedProject = projects.page.projects.find(row => row.id === input.selectedProjectId) ?? null;
        } else {
          projects = loadState(state as unknown as Record<string, unknown>, true) ?? { kind: "invalid" };
        }
      }
    }
  } catch {
    if (selectedOrganization === null) organizations = { kind: "invalid" };
    else projects = { kind: "invalid" };
  }
  return Object.freeze({ organizations: Object.freeze(organizations), projects: Object.freeze(projects),
    selectedOrganization, selectedProject });
}

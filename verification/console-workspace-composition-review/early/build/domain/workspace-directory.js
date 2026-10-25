const roles = ["administrator", "billing_manager", "developer", "owner", "release_manager", "viewer"];
const failures = ["permission_denied", "not_found", "request_failed"];
function requireValid(value, reason) {
    if (!value)
        throw new TypeError(reason);
}
function object(value, keys) {
    return value !== null && typeof value === "object" && !Array.isArray(value) &&
        keys.every(key => Object.hasOwn(value, key)) && Object.keys(value).length === keys.length;
}
/** Match Scope.identifier? and the display-name contract without trimming or normalizing. */
function printable(value, maximum) {
    if (typeof value !== "string" || value.length === 0 || value.length > maximum)
        return false;
    let bytes = 0;
    for (const character of value) {
        const code = character.codePointAt(0);
        if (!((code >= 0x20 && code <= 0x7e) || (code >= 0xa0 && code <= 0xd7ff) ||
            (code >= 0xe000 && code <= 0xfffd) || (code >= 0x10000 && code <= 0x10ffff)))
            return false;
        bytes += code <= 0x7f ? 1 : code <= 0x7ff ? 2 : code <= 0xffff ? 3 : 4;
        if (bytes > maximum)
            return false;
    }
    return true;
}
export function isWorkspaceIdentifier(value) {
    return printable(value, 128) && value !== "*";
}
function displayName(value) {
    return value === null || printable(value, 256);
}
function cursor(value) {
    return value === null || (typeof value === "string" && value.length <= 1400 && /^[A-Za-z0-9_-]+$/u.test(value));
}
function copyRoles(value, allowEmpty) {
    requireValid(Array.isArray(value) && value.length <= roles.length && (allowEmpty || value.length > 0), "Invalid workspace roles");
    let previous;
    for (const role of value) {
        requireValid(typeof role === "string" && roles.includes(role) && (previous === undefined || previous < role), "Invalid workspace role order");
        previous = role;
    }
    return Object.freeze([...value]);
}
/** Strict, bounded customer API boundary. Rows convey visibility, never release authority. */
export function parseWorkspaceOrganizations(input) {
    requireValid(object(input, ["organizations", "next_cursor"]) && Array.isArray(input.organizations) &&
        input.organizations.length <= 100 && cursor(input.next_cursor) &&
        (input.organizations.length > 0 || input.next_cursor === null), "Invalid organization page");
    const ids = new Set();
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
export function parseWorkspaceProjects(input, organizationId) {
    requireValid(isWorkspaceIdentifier(organizationId), "Invalid selected organization");
    requireValid(object(input, ["projects", "next_cursor"]) && Array.isArray(input.projects) &&
        input.projects.length <= 100 && cursor(input.next_cursor) &&
        (input.projects.length > 0 || input.next_cursor === null), "Invalid project page");
    const ids = new Set();
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
export function workspaceDisplayName(row) {
    return row.display_name ?? row.id;
}
/** A visible identity annotation only; never use it as a request or selection ID. */
export function workspaceIdentifierMarker(identifier) {
    if (!/^\s+$/u.test(identifier))
        return null;
    return `"${Array.from(identifier, character => `\\u${character.codePointAt(0).toString(16).padStart(4, "0")}`).join("")}"`;
}
function loadState(value, scoped) {
    const keys = scoped ? ["kind", "organizationId"] : ["kind"];
    if (["loading", "unauthenticated", "unavailable"].includes(value.kind) && object(value, keys)) {
        return Object.freeze({ kind: value.kind });
    }
    if (value.kind === "error" && object(value, [...keys, "reason"]) && failures.includes(value.reason)) {
        return Object.freeze({ kind: "error", reason: value.reason });
    }
    return null;
}
/** Resolve controlled selection against the current validated pages; stale scopes stay hidden. */
export function resolveWorkspaceDirectory(input) {
    let organizations = { kind: "invalid" };
    let projects = { kind: "unselected" };
    let selectedOrganization = null;
    let selectedProject = null;
    try {
        const state = input.organizations;
        if (object(state, ["kind", "input"]) && state.kind === "ready") {
            organizations = { kind: "ready", page: parseWorkspaceOrganizations(state.input) };
            selectedOrganization = organizations.page.organizations.find(row => row.id === input.selectedOrganizationId) ?? null;
        }
        else if (state && typeof state === "object") {
            organizations = loadState(state, false) ?? { kind: "invalid" };
        }
        if (selectedOrganization) {
            projects = { kind: "invalid" };
            const state = input.projects;
            if (state && typeof state === "object" && "organizationId" in state && state.organizationId === selectedOrganization.id) {
                if (object(state, ["kind", "organizationId", "input"]) && state.kind === "ready") {
                    projects = { kind: "ready", page: parseWorkspaceProjects(state.input, selectedOrganization.id) };
                    selectedProject = projects.page.projects.find(row => row.id === input.selectedProjectId) ?? null;
                }
                else {
                    projects = loadState(state, true) ?? { kind: "invalid" };
                }
            }
        }
    }
    catch {
        if (selectedOrganization === null)
            organizations = { kind: "invalid" };
        else
            projects = { kind: "invalid" };
    }
    return Object.freeze({ organizations: Object.freeze(organizations), projects: Object.freeze(projects),
        selectedOrganization, selectedProject });
}

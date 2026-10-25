import { WorkspaceClientError } from "../api/workspace-client.js";
import { parseWorkspaceOrganizations, parseWorkspaceProjects } from "../domain/workspace-directory.js";
const firstPage = Object.freeze({});
const unselected = Object.freeze({ kind: "unselected" });
function snapshot(state) {
    return Object.freeze({ ...state, organizations: Object.freeze({ ...state.organizations }),
        projects: Object.freeze({ ...state.projects }) });
}
/** Only the transport's closed error class can change authentication or error category. */
function failure(error) {
    try {
        if (error instanceof WorkspaceClientError) {
            const code = error.code;
            switch (code) {
                case "unauthenticated":
                case "permission_denied":
                case "not_found":
                case "unavailable": return code;
            }
        }
    }
    catch { /* Untrusted errors, including throwing proxies, receive the fixed fallback. */ }
    return "request_failed";
}
/** An in-memory controller. The client alone owns authentication and transport. */
export function createWorkspaceController() {
    let state = snapshot({ organizations: { kind: "unavailable" }, projects: unselected });
    let disposed = false;
    let client;
    let sessionGeneration = 0;
    let requestGeneration = 0;
    let revision = 0;
    let notifying = false;
    const subscriptions = new Set();
    let organizationRequest;
    let projectRequest;
    let organizationAttempt;
    let projectAttempt;
    // A nested mutation supersedes the current notification round. New subscribers get
    // the current revision once; removed subscribers cannot be called from a stale copy.
    function notify() {
        if (notifying || disposed)
            return;
        notifying = true;
        try {
            while (!disposed) {
                const currentRevision = revision;
                const currentState = state;
                const pending = [...subscriptions].filter(item => item.revision !== currentRevision);
                if (pending.length === 0)
                    break;
                for (const item of pending) {
                    if (disposed || revision !== currentRevision)
                        break;
                    if (!subscriptions.has(item) || item.revision === currentRevision)
                        continue;
                    item.revision = currentRevision;
                    try {
                        void Promise.resolve(item.listener(currentState)).catch(() => undefined);
                    }
                    catch { /* One observer cannot block another or a request. */ }
                }
            }
        }
        finally {
            notifying = false;
        }
    }
    function update(next, cancelled = []) {
        state = snapshot(next);
        revision++;
        // Abort handlers may reenter, so state and request slots are coherent first.
        for (const request of cancelled)
            request?.controller.abort();
        notify();
    }
    function request(page) {
        return { generation: ++requestGeneration, sessionGeneration, client: client, page,
            controller: new AbortController() };
    }
    function current(value, active) {
        return !disposed && client === value.client && value.sessionGeneration === sessionGeneration &&
            active?.generation === value.generation && !value.controller.signal.aborted;
    }
    function organizationPage() {
        return state.organizations.kind === "ready" ? state.organizations.input : undefined;
    }
    function selectedOrganization(id) {
        return typeof id === "string" && state.selectedOrganizationId === id &&
            organizationPage()?.organizations.some(row => row.id === id) === true;
    }
    async function loadOrganizations(value) {
        if (!current(value, organizationRequest))
            return;
        try {
            const input = await value.client.organizations(value.page, value.controller.signal);
            if (!current(value, organizationRequest))
                return;
            const page = parseWorkspaceOrganizations(input);
            if (!current(value, organizationRequest))
                return;
            organizationRequest = undefined;
            update({ organizations: { kind: "ready", input: page }, projects: unselected });
        }
        catch (error) {
            if (!current(value, organizationRequest))
                return;
            const reason = failure(error);
            if (!current(value, organizationRequest))
                return;
            if (reason === "unauthenticated") {
                setSession({ kind: "unauthenticated" });
                return;
            }
            organizationRequest = undefined;
            update({ organizations: reason === "unavailable" ? { kind: "unavailable" } : { kind: "error", reason },
                projects: unselected });
        }
    }
    async function loadProjects(value) {
        if (!current(value, projectRequest) || !selectedOrganization(value.organizationId))
            return;
        try {
            const input = await value.client.projects(value.organizationId, value.page, value.controller.signal);
            if (!current(value, projectRequest) || !selectedOrganization(value.organizationId))
                return;
            const page = parseWorkspaceProjects(input, value.organizationId);
            if (!current(value, projectRequest) || !selectedOrganization(value.organizationId))
                return;
            projectRequest = undefined;
            update({ organizations: state.organizations, selectedOrganizationId: value.organizationId,
                projects: { kind: "ready", organizationId: value.organizationId, input: page } });
        }
        catch (error) {
            if (!current(value, projectRequest) || !selectedOrganization(value.organizationId))
                return;
            const reason = failure(error);
            if (!current(value, projectRequest) || !selectedOrganization(value.organizationId))
                return;
            if (reason === "unauthenticated") {
                setSession({ kind: "unauthenticated" });
                return;
            }
            projectRequest = undefined;
            update({ organizations: state.organizations, selectedOrganizationId: value.organizationId,
                projects: reason === "unavailable" ? { kind: "unavailable", organizationId: value.organizationId } :
                    { kind: "error", organizationId: value.organizationId, reason } });
        }
    }
    function beginOrganizations(page) {
        const cancelled = [organizationRequest, projectRequest];
        projectRequest = undefined;
        projectAttempt = undefined;
        organizationAttempt = page;
        const value = request(page);
        organizationRequest = value;
        update({ organizations: { kind: "loading" }, projects: unselected }, cancelled);
        // The async boundary catches both synchronous throws and rejected client promises.
        void loadOrganizations(value);
    }
    function beginProjects(organizationId, page) {
        const cancelled = projectRequest;
        projectAttempt = Object.freeze({ organizationId, page });
        const value = { ...request(page), organizationId };
        projectRequest = value;
        update({ organizations: state.organizations, selectedOrganizationId: organizationId,
            projects: { kind: "loading", organizationId } }, [cancelled]);
        void loadProjects(value);
    }
    function setSession(session) {
        if (disposed)
            return;
        const cancelled = [organizationRequest, projectRequest];
        organizationRequest = undefined;
        projectRequest = undefined;
        organizationAttempt = undefined;
        projectAttempt = undefined;
        sessionGeneration++;
        client = session.kind === "ready" ? session.client : undefined;
        if (client) {
            organizationAttempt = firstPage;
            const value = request(firstPage);
            organizationRequest = value;
            update({ organizations: { kind: "loading" }, projects: unselected }, cancelled);
            void loadOrganizations(value);
        }
        else {
            update({ organizations: { kind: session.kind === "unauthenticated" ? "unauthenticated" : "unavailable" },
                projects: unselected }, cancelled);
        }
    }
    return Object.freeze({
        getState: () => state,
        subscribe(listener) {
            if (disposed)
                return () => undefined;
            const item = { listener, revision: -1 };
            subscriptions.add(item);
            notify();
            return () => { subscriptions.delete(item); };
        },
        setSession,
        selectOrganization(id) {
            if (disposed || !client || typeof id !== "string" || state.selectedOrganizationId === id ||
                !organizationPage()?.organizations.some(row => row.id === id))
                return;
            beginProjects(id, firstPage);
        },
        selectProject(selection) {
            if (disposed || !client || !selection || !selectedOrganization(selection.organizationId) ||
                state.projects.kind !== "ready" || state.projects.organizationId !== selection.organizationId)
                return;
            const page = state.projects.input;
            if (!page.projects.some(row => row.id === selection.projectId) || state.selectedProjectId === selection.projectId)
                return;
            update({ ...state, selectedProjectId: selection.projectId });
        },
        nextOrganizations(cursor) {
            if (disposed || !client || typeof cursor !== "string" || organizationPage()?.next_cursor !== cursor)
                return;
            beginOrganizations(Object.freeze({ cursor }));
        },
        nextProjects(page) {
            if (disposed || !client || !page || !selectedOrganization(page.organizationId) ||
                state.projects.kind !== "ready" || state.projects.organizationId !== page.organizationId ||
                typeof page.cursor !== "string" || state.projects.input.next_cursor !== page.cursor)
                return;
            beginProjects(page.organizationId, Object.freeze({ cursor: page.cursor }));
        },
        retryOrganizations() {
            if (disposed || !client || !organizationAttempt ||
                (state.organizations.kind !== "error" && state.organizations.kind !== "unavailable"))
                return;
            beginOrganizations(organizationAttempt);
        },
        retryProjects(organizationId) {
            if (disposed || !client || !projectAttempt || !selectedOrganization(organizationId) ||
                projectAttempt.organizationId !== organizationId || state.projects.kind === "unselected" ||
                state.projects.organizationId !== organizationId ||
                (state.projects.kind !== "error" && state.projects.kind !== "unavailable"))
                return;
            beginProjects(organizationId, projectAttempt.page);
        },
        dispose() {
            if (disposed)
                return;
            disposed = true;
            sessionGeneration++;
            client = undefined;
            const cancelled = [organizationRequest, projectRequest];
            organizationRequest = undefined;
            projectRequest = undefined;
            organizationAttempt = undefined;
            projectAttempt = undefined;
            subscriptions.clear();
            update({ organizations: { kind: "unavailable" }, projects: unselected }, cancelled);
        },
    });
}

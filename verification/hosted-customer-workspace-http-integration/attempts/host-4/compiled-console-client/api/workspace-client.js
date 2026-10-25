import { isWorkspaceIdentifier, parseWorkspaceOrganizations, parseWorkspaceProjects } from "../domain/workspace-directory.js";
const failureCodes = ["unauthenticated", "permission_denied", "not_found", "unavailable", "invalid_response", "invalid_request", "aborted"];
/** Fixed public errors never include bearer tokens, response bodies, URLs or provider details. */
export class WorkspaceClientError extends Error {
    code;
    constructor(code) {
        if (!failureCodes.includes(code))
            code = "unavailable";
        super(`Workspace request ${code}`);
        this.name = "WorkspaceClientError";
        this.code = code;
    }
}
const maximumResponseBytes = 262_144;
const failure = (code) => { throw new WorkspaceClientError(code); };
function origin(options) {
    try {
        const value = new URL(options.apiOrigin);
        const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(value.hostname);
        if (value.username || value.password || value.pathname !== "/" || value.search || value.hash ||
            !(value.protocol === "https:" || (options.allowInsecureLoopback === true && loopback && value.protocol === "http:"))) {
            return failure("invalid_request");
        }
        return value.origin;
    }
    catch {
        return failure("invalid_request");
    }
}
function query(page, organizationId) {
    if (!page || typeof page !== "object" || Array.isArray(page) ||
        Object.keys(page).some(key => key !== "limit" && key !== "cursor"))
        return failure("invalid_request");
    const fields = [];
    if (organizationId !== undefined) {
        if (!isWorkspaceIdentifier(organizationId))
            return failure("invalid_request");
        fields.push(["organization_id", organizationId]);
    }
    if (Object.hasOwn(page, "limit")) {
        if (!Number.isInteger(page.limit) || page.limit < 1 || page.limit > 100)
            return failure("invalid_request");
        fields.push(["limit", String(page.limit)]);
    }
    if (Object.hasOwn(page, "cursor")) {
        if (typeof page.cursor !== "string" || page.cursor.length > 1400 || !/^[A-Za-z0-9_-]+$/u.test(page.cursor)) {
            return failure("invalid_request");
        }
        fields.push(["cursor", page.cursor]);
    }
    return fields.length ? `?${fields.map(([key, value]) => `${key}=${encodeURIComponent(value)}`).join("&")}` : "";
}
function token(value) {
    return typeof value === "string" && value.length <= 4089 && /^[A-Za-z0-9._~+/-]+=*$/u.test(value);
}
function cancelBody(response) {
    // Cancellation is best effort and must not extend the request deadline.
    void response.body?.cancel().catch(() => undefined);
}
async function json(response, signal) {
    if (response.redirected || !/^application\/json(?:\s*;\s*charset=utf-8)?$/iu.test(response.headers.get("content-type") ?? "")) {
        cancelBody(response);
        return failure("invalid_response");
    }
    const length = response.headers.get("content-length");
    if (length !== null && (!/^\d+$/u.test(length) || Number(length) > maximumResponseBytes)) {
        cancelBody(response);
        return failure("invalid_response");
    }
    if (!response.body)
        return failure("invalid_response");
    const reader = response.body.getReader();
    const cancel = () => { void reader.cancel().catch(() => undefined); };
    signal.addEventListener("abort", cancel, { once: true });
    const chunks = [];
    let size = 0;
    let reads = 0;
    try {
        if (signal.aborted)
            return failure("aborted");
        while (true) {
            if (++reads > 4096)
                return failure("invalid_response");
            const item = await reader.read();
            if (signal.aborted)
                return failure("aborted");
            if (item.done)
                break;
            size += item.value.byteLength;
            if (size > maximumResponseBytes)
                return failure("invalid_response");
            chunks.push(item.value);
        }
        const bytes = new Uint8Array(size);
        let offset = 0;
        for (const chunk of chunks) {
            bytes.set(chunk, offset);
            offset += chunk.byteLength;
        }
        return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    }
    catch (error) {
        if (error instanceof WorkspaceClientError)
            throw error;
        return failure("invalid_response");
    }
    finally {
        signal.removeEventListener("abort", cancel);
        cancel();
        reader.releaseLock();
    }
}
/** Read-only customer workspace transport. Login and selection state belong to its caller. */
export function createWorkspaceClient(options) {
    const base = origin(options);
    if (typeof options.accessToken !== "function")
        return failure("invalid_request");
    const fetchRequest = options.fetch ?? globalThis.fetch;
    const timeoutMs = options.timeoutMs ?? 15_000;
    if (typeof fetchRequest !== "function" || !Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 30_000) {
        return failure("invalid_request");
    }
    const accessToken = options.accessToken;
    async function request(path, decode, signal) {
        if (signal?.aborted)
            return failure("aborted");
        const controller = new AbortController();
        let timedOut = false;
        const cancel = () => controller.abort();
        signal?.addEventListener("abort", cancel, { once: true });
        const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
        let abortListener;
        const stopped = new Promise((_, reject) => {
            abortListener = () => reject(new WorkspaceClientError(timedOut ? "unavailable" : "aborted"));
            controller.signal.addEventListener("abort", abortListener, { once: true });
        });
        const perform = async () => {
            const bearer = await accessToken();
            if (controller.signal.aborted)
                return failure(timedOut ? "unavailable" : "aborted");
            if (!token(bearer))
                return failure("unauthenticated");
            const response = await fetchRequest(base + path, {
                method: "GET", headers: { accept: "application/json", authorization: `Bearer ${bearer}` },
                credentials: "omit", redirect: "error", cache: "no-store", referrerPolicy: "no-referrer", signal: controller.signal,
            });
            if (controller.signal.aborted) {
                cancelBody(response);
                return failure(timedOut ? "unavailable" : "aborted");
            }
            if (response.status !== 200) {
                cancelBody(response);
                if (response.status === 401)
                    return failure("unauthenticated");
                if (response.status === 403)
                    return failure("permission_denied");
                if (response.status === 404)
                    return failure("not_found");
                if ([429, 500, 502, 503, 504].includes(response.status))
                    return failure("unavailable");
                return failure("invalid_response");
            }
            const value = await json(response, controller.signal);
            try {
                return decode(value);
            }
            catch {
                return failure("invalid_response");
            }
        };
        try {
            return await Promise.race([perform(), stopped]);
        }
        catch (error) {
            // A session provider may itself throw an Error with mutable private text.
            if (error instanceof WorkspaceClientError)
                throw new WorkspaceClientError(error.code);
            return failure(controller.signal.aborted ? (timedOut ? "unavailable" : "aborted") : "unavailable");
        }
        finally {
            clearTimeout(timer);
            signal?.removeEventListener("abort", cancel);
            if (abortListener)
                controller.signal.removeEventListener("abort", abortListener);
        }
    }
    return Object.freeze({
        async organizations(page = {}, signal) {
            return request("/v3/orgs" + query(page), parseWorkspaceOrganizations, signal);
        },
        async projects(organizationId, page = {}, signal) {
            // undefined cannot silently select an unscoped project endpoint at runtime.
            if (!isWorkspaceIdentifier(organizationId))
                return failure("invalid_request");
            return request("/v3/projects" + query(page, organizationId), value => parseWorkspaceProjects(value, organizationId), signal);
        },
    });
}

import { decode, decimal, encoder, errorResponse, exact, hex, invalid, parseJSON, sha, text } from "./wire.js";
export function principal(env) {
    try {
        if (!env.MIXER_PRINCIPAL || !env.MIXER_POOL_TOKEN_SHA256)
            return null;
        const p = parseJSON(encoder.encode(env.MIXER_PRINCIPAL), 4096);
        exact(p, ["environment_id", "pool_id", "controller_id", "platforms"]);
        for (const k of ["environment_id", "pool_id", "controller_id"])
            if (!/^[\x20-\x7e]+$/.test(text(p[k])))
                invalid();
        if (!Array.isArray(p.platforms) || !p.platforms.length || p.platforms.length > 2 || new Set(p.platforms).size !== p.platforms.length || !p.platforms.every(x => x === "ios" || x === "android"))
            invalid();
        return { ...p, token_sha256: hex(env.MIXER_POOL_TOKEN_SHA256) };
    }
    catch {
        return null;
    }
}
function unhex(v) { return Uint8Array.from(v.match(/../g), x => parseInt(x, 16)); }
export async function authenticate(request, p) {
    const header = request.headers.get("Authorization");
    if (!header || !/^Bearer [A-Za-z0-9_-]{43}$/.test(header))
        return false;
    const token = header.slice(7);
    let decoded;
    try {
        decoded = atob(token.replace(/-/g, "+").replace(/_/g, "/") + "=");
    }
    catch {
        return false;
    }
    if (decoded.length !== 32 || btoa(decoded).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_") !== token)
        return false;
    const actual = unhex(await sha(token));
    // Delegate fixed-size digest equality to standard Web Crypto HMAC verify,
    // rather than implementing a JIT-sensitive character comparison loop.
    const key = await crypto.subtle.importKey("raw", crypto.getRandomValues(new Uint8Array(32)), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
    const tag = await crypto.subtle.sign("HMAC", key, unhex(p.token_sha256));
    return crypto.subtle.verify("HMAC", key, tag, actual);
}
export async function body(request) {
    if (request.headers.get("Content-Type") !== "application/json" ||
        ![null, "identity"].includes(request.headers.get("Content-Encoding")))
        invalid();
    const length = request.headers.get("Content-Length");
    if (length !== null && BigInt(decimal(length, 1n, 16384n)) > 16384n)
        invalid();
    const source = request.body;
    if (!source)
        invalid();
    const reader = source.getReader();
    const chunks = [];
    let size = 0;
    let timer;
    const deadline = new Promise((_, reject) => { timer = setTimeout(() => { void reader.cancel().catch(() => { }); reject(new Error("body_timeout")); }, 4000); });
    try {
        while (true) {
            const { value, done } = await Promise.race([reader.read(), deadline]);
            if (done)
                break;
            size += value.length;
            if (size > 16384)
                invalid();
            chunks.push(value);
        }
    }
    catch {
        void reader.cancel().catch(() => { });
        invalid();
    }
    finally {
        if (timer !== undefined)
            clearTimeout(timer);
        reader.releaseLock();
    }
    if (length !== null && BigInt(size) !== BigInt(length))
        invalid();
    const out = new Uint8Array(size);
    let offset = 0;
    for (const c of chunks) {
        out.set(c, offset);
        offset += c.length;
    }
    return out;
}
export async function ingress(request, env) {
    const url = new URL(request.url);
    if (request.method !== "POST" || url.pathname !== "/internal/mixer-build-worker/v1" || url.search)
        return errorResponse(404);
    const p = principal(env);
    if (!p || !await authenticate(request, p))
        return errorResponse(401);
    try {
        const bytes = await body(request), r = await decode(bytes);
        if (r.environment_id !== p.environment_id || r.pool_id !== p.pool_id || r.controller_id !== p.controller_id || !p.platforms.includes(r.ref.platform))
            return errorResponse(403);
        return { r, bytes };
    }
    catch {
        return errorResponse(400);
    }
}
export async function operationKey(r) {
    return sha(JSON.stringify(["mixer-worker-controller-do-v1", r.environment_id, r.pool_id, r.controller_id, r.operation_id]));
}

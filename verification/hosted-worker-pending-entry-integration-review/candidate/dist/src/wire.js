// Mixer-owned v1 codec. No authorization or provider execution is inferred here.
export const MAX = 9223372036854775807n;
export const encoder = new TextEncoder();
export class InvalidInput extends Error {
    constructor() { super("invalid_input"); this.name = "InvalidInput"; }
}
export function invalid() { throw new InvalidInput(); }
export function exact(v, keys) {
    if (!v || typeof v !== "object" || Array.isArray(v) || Object.keys(v).length !== keys.length || !keys.every(k => Object.hasOwn(v, k)))
        invalid();
}
export function decimal(v, min = 1n, max = MAX) {
    if (typeof v !== "string" || v.length > 19 || !/^(0|[1-9][0-9]*)$/.test(v))
        invalid();
    const n = BigInt(v);
    if (n < min || n > max)
        invalid();
    return v;
}
export function text(v, max = 128) {
    if (typeof v !== "string" || !v.length || encoder.encode(v).length > max)
        invalid();
    // Elixir printable UTF-8 repertoire, without normalization or surrogate repair.
    for (const ch of v) {
        const c = ch.codePointAt(0);
        if (!((c >= 32 && c <= 127) || (c >= 160 && c <= 0xd7ff) || (c >= 0xe000 && c <= 0xfffd) ||
            (c >= 0x10000 && c <= 0x10ffff) || (c >= 7 && c <= 13) || c === 27))
            invalid();
    }
    return v;
}
export function hex(v, length = 64) {
    if (typeof v !== "string" || v.length !== length || !/^[0-9a-f]+$/.test(v))
        invalid();
    return v;
}
const scopeKeys = ["organization_id", "project_id", "application_id", "build_id", "platform"];
// This parser counts depth/tokens/raw string bytes before allocating decoded
// strings/objects. JSON.parse is used only for a bounded single string token.
export function parseJSON(raw, limit = 16384) {
    if (!raw.byteLength || raw.byteLength > limit)
        invalid();
    let source;
    try {
        source = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(raw);
    }
    catch {
        invalid();
    }
    let i = 0, tokens = 0;
    const ws = () => { while (i < source.length && " \n\r\t".includes(source[i]))
        i++; };
    const token = () => { if (++tokens > 512)
        invalid(); };
    const str = () => {
        const start = i++;
        let escaped = false;
        while (i < source.length) {
            const c = source[i++];
            if (!escaped && c === '"') {
                const slice = source.slice(start, i);
                if (encoder.encode(slice.slice(1, -1)).length > 8192)
                    invalid();
                let value;
                try {
                    value = JSON.parse(slice);
                }
                catch {
                    invalid();
                }
                return value;
            }
            if (!escaped && c === "\\")
                escaped = true;
            else
                escaped = false;
        }
        return invalid();
    };
    const value = (depth) => {
        ws();
        token();
        if (depth > 8)
            invalid();
        const c = source[i];
        if ((c === "{" || c === "[") && depth >= 8)
            invalid();
        if (c === '"')
            return str();
        if (c === "{") {
            i++;
            const result = Object.create(null);
            ws();
            if (source[i] === "}") {
                i++;
                return result;
            }
            while (true) {
                ws();
                token();
                if (source[i] !== '"')
                    invalid();
                const key = str();
                if (Object.hasOwn(result, key))
                    invalid();
                ws();
                if (source[i++] !== ":")
                    invalid();
                result[key] = value(depth + 1);
                ws();
                const sep = source[i++];
                if (sep === "}")
                    return result;
                if (sep !== ",")
                    invalid();
            }
        }
        if (c === "[") {
            i++;
            const result = [];
            ws();
            if (source[i] === "]") {
                i++;
                return result;
            }
            while (true) {
                result.push(value(depth + 1));
                ws();
                const sep = source[i++];
                if (sep === "]")
                    return result;
                if (sep !== ",")
                    invalid();
            }
        }
        const start = i;
        while (i < source.length && !" \t\n\r,]}".includes(source[i]))
            i++;
        const literal = source.slice(start, i);
        if (literal === "true")
            return true;
        if (literal === "false")
            return false;
        if (literal === "null")
            return null;
        // Protocol numbers are only small integer version/attempt tokens.
        if (!/^(0|[1-9][0-9]*)$/.test(literal))
            invalid();
        const n = Number(literal);
        if (!Number.isSafeInteger(n))
            invalid();
        return n;
    };
    const result = value(0);
    ws();
    if (i !== source.length)
        invalid();
    return result;
}
function scope(v) {
    for (const key of scopeKeys)
        if (key !== "platform")
            text(v[key]);
    if (v.platform !== "ios" && v.platform !== "android")
        invalid();
}
export async function sha(s) {
    const bytes = typeof s === "string" ? encoder.encode(s) : s;
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest), x => x.toString(16).padStart(2, "0")).join("");
}
// Exact default Jason string bytes are part of the frozen hash contract.
// JSON.stringify differs for printable \v/\e: Jason's Unicode escapes use
// uppercase hex. Walk characters so literal text such as "\\u000b" is untouched.
function hashString(value) {
    let out = '"';
    const short = { 8: "\\b", 9: "\\t", 10: "\\n", 12: "\\f", 13: "\\r" };
    for (const ch of value) {
        const cp = ch.codePointAt(0);
        if (ch === '"')
            out += '\\"';
        else if (ch === '\\')
            out += '\\\\';
        else if (cp < 32)
            out += short[cp] ?? "\\u" + cp.toString(16).toUpperCase().padStart(4, "0");
        else
            out += ch;
    }
    return out + '"';
}
function hashArray(value) {
    return "[" + value.map(v => Array.isArray(v) ? hashArray(v) : typeof v === "string" ? hashString(v) :
        typeof v === "number" && Number.isSafeInteger(v) ? String(v) : invalid()).join(",") + "]";
}
export function immutableBytes(r) {
    const f = r.ref, s = r.spec;
    return hashArray(["mixer-worker-binding-v1", r.operation_id, r.guard.record_id,
        [f.organization_id, f.project_id, f.application_id, f.build_id, f.platform, f.attempt, f.fence],
        [s.organization_id, s.project_id, s.application_id, s.build_id, s.platform, s.source.kind, s.source.sha256, s.source.reference, s.toolchain_lock_sha256, s.build_definition_sha256], r.deadline_ms]);
}
export function operationBytes(r) {
    const f = r.ref;
    const prefix = hashArray(["mixer-build-operation-v1", r.guard.record_id, f.organization_id, f.project_id, f.application_id, f.build_id, f.platform, f.attempt]);
    return prefix.slice(0, -1) + "," + decimal(f.fence) + "]";
}
export async function decode(raw) {
    const v = parseJSON(raw);
    exact(v, ["version", "environment_id", "pool_id", "controller_id", "request_id", "command", "operation_id", "immutable_sha256", "ref", "spec", "deadline_ms", "guard"]);
    if (v.version !== 1 || !["query", "ensure_started", "stop"].includes(v.command))
        invalid();
    for (const k of ["environment_id", "pool_id", "controller_id"]) {
        const t = text(v[k]);
        if (!/^[\x20-\x7e]+$/.test(t))
            invalid();
    }
    hex(v.request_id, 32);
    hex(v.operation_id);
    hex(v.immutable_sha256);
    decimal(v.deadline_ms);
    exact(v.ref, [...scopeKeys, "attempt", "fence"]);
    scope(v.ref);
    if (!Number.isInteger(v.ref.attempt) || v.ref.attempt < 1 || v.ref.attempt > 5)
        invalid();
    decimal(v.ref.fence);
    exact(v.spec, [...scopeKeys, "source", "toolchain_lock_sha256", "build_definition_sha256"]);
    scope(v.spec);
    const f = v.ref, s = v.spec;
    if (!scopeKeys.every(k => f[k] === s[k]))
        invalid();
    hex(v.spec.toolchain_lock_sha256);
    hex(v.spec.build_definition_sha256);
    exact(v.spec.source, ["kind", "sha256", "reference"]);
    if (v.spec.source.kind !== "revision" && v.spec.source.kind !== "upload")
        invalid();
    hex(v.spec.source.sha256);
    text(v.spec.source.reference, 1024);
    exact(v.guard, ["record_id", "revision", "owner_id", "epoch", "expires_at_us"]);
    if (typeof v.guard.record_id !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v.guard.record_id))
        invalid();
    decimal(v.guard.revision, 0n, 32n);
    decimal(v.guard.epoch);
    decimal(v.guard.expires_at_us);
    text(v.guard.owner_id);
    const r = v;
    if (await sha(operationBytes(r)) !== r.operation_id || await sha(immutableBytes(r)) !== r.immutable_sha256)
        invalid();
    return r;
}
export function reply(r, observation) {
    const { spec: discard, deadline_ms: discard2, ...echo } = r;
    const bytes = encoder.encode(JSON.stringify({ ...echo, observation }));
    if (bytes.length > 32768)
        throw new Error("response_limit");
    return new Response(bytes, { status: 200, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
}
export const errorResponse = (status) => new Response('{"error":"rejected"}', { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
const kinds = ["unsigned_native_binary", "guest_artifact", "resource_inventory", "debug_symbols", "compatibility_report", "sbom", "provenance"];
const failures = { infrastructure: ["worker_unavailable", "worker_lost", "dependency_transport", "artifact_transport", "worker_timeout"], compiler: ["compiler_error"], test: ["test_failure"], policy: ["policy_rejection", "invalid_input"], unknown: ["unknown_failure"] };
export function result(v) {
    if (!v || typeof v !== "object")
        invalid();
    const r = v;
    if (r.outcome === "succeeded") {
        exact(r, ["outcome", "artifacts"]);
        if (!Array.isArray(r.artifacts) || r.artifacts.length !== 7)
            invalid();
        const seen = new Set(), sizes = new Map();
        for (const a of r.artifacts) {
            exact(a, ["kind", "sha256", "size_bytes"]);
            if (!kinds.includes(a.kind) || seen.has(a.kind))
                invalid();
            seen.add(a.kind);
            const h = hex(a.sha256), n = decimal(a.size_bytes);
            if (sizes.has(h) && sizes.get(h) !== n)
                invalid();
            sizes.set(h, n);
        }
    }
    else {
        exact(r, ["outcome", "class", "code", "diagnostic_sha256"]);
        if (r.outcome !== "failed" || typeof r.class !== "string" || typeof r.code !== "string" || !Object.hasOwn(failures, r.class) || !failures[r.class].includes(r.code))
            invalid();
        hex(r.diagnostic_sha256);
    }
    return r;
}

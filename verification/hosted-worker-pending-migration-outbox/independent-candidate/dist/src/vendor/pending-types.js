export const MAX = 9223372036854775807n;
export const encoder = new TextEncoder();
export function invalid() { throw new Error('pending_invalid'); }
export function exact(v, keys) { if (!v || typeof v !== 'object' || Array.isArray(v) || Object.keys(v).length !== keys.length || keys.some(k => !Object.hasOwn(v, k)))
    invalid(); return v; }
export function hex(v, bits = 256) { if (typeof v !== 'string' || v.length !== bits / 4 || !/^[0-9a-f]+$/.test(v))
    invalid(); return v; }
export function decimal(v) { if (typeof v !== 'string' || !/^(0|[1-9][0-9]{0,18})$/.test(v) || BigInt(v) > MAX)
    invalid(); return v; }
export function integer(v, min, max) { if (typeof v !== 'number' || !Number.isInteger(v) || v < min || v > max)
    invalid(); return v; }
export function principal(v) { if (typeof v !== 'string' || v.length < 1 || v.length > 128 || !/^[\x20-\x7e]+$/.test(v))
    invalid(); return v; }
export function config(env) { const c = exact(JSON.parse(env.MIXER_PENDING_CONFIG ?? 'null'), ['generation', 'operationsNamespace', 'registryNamespace']); return { generation: hex(c.generation), operationsNamespace: principal(c.operationsNamespace), registryNamespace: principal(c.registryNamespace) }; }
export function registryName(c, index) { return JSON.stringify(['mixer-worker-pending-registry-v1', c.generation, c.operationsNamespace, c.registryNamespace, integer(index, 0, 15)]); }
export function auditName(c) { return JSON.stringify(['mixer-worker-pending-audit-v1', c.generation, c.operationsNamespace, c.registryNamespace]); }
export const randomId = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), n => n.toString(16).padStart(2, '0')).join('');
export const sha = async (s) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(s))), n => n.toString(16).padStart(2, '0')).join('');
export function identityBytes(i) { return JSON.stringify(['mixer-worker-pending-identity-v1', i.namespaceGeneration, i.environmentId, i.poolId, i.controllerId, i.platform, i.operationKey, i.operationId, i.immutableSha256]); }
export function identityFromBytes(s) { const v = JSON.parse(s); return { namespaceGeneration: v[1], environmentId: v[2], poolId: v[3], controllerId: v[4], platform: v[5], operationKey: v[6], operationId: v[7], immutableSha256: v[8] }; }
export async function identity(v, c) {
    const p = exact(v, ['namespaceGeneration', 'environmentId', 'poolId', 'controllerId', 'platform', 'operationKey', 'operationId', 'immutableSha256']);
    const i = { namespaceGeneration: hex(p.namespaceGeneration), environmentId: principal(p.environmentId), poolId: principal(p.poolId), controllerId: principal(p.controllerId), platform: p.platform, operationKey: hex(p.operationKey), operationId: hex(p.operationId), immutableSha256: hex(p.immutableSha256) };
    if (i.namespaceGeneration !== c.generation || !['ios', 'android'].includes(i.platform))
        invalid();
    const bytes = identityBytes(i);
    if (encoder.encode(bytes).length > 2048)
        invalid();
    if (await sha(JSON.stringify(['mixer-worker-controller-do-v1', i.environmentId, i.poolId, i.controllerId, i.operationId])) !== i.operationKey)
        invalid();
    return { value: i, bytes, digest: await sha(bytes), shard: parseInt(i.operationKey[0], 16) };
}
export function receipt(v, c) { const r = exact(v, ['identityDigest', 'namespaceGeneration', 'recordId', 'shard', 'allocationIndex']); if (r.namespaceGeneration !== c.generation)
    invalid(); return { identityDigest: hex(r.identityDigest), namespaceGeneration: hex(r.namespaceGeneration), recordId: hex(r.recordId, 128), shard: integer(r.shard, 0, 15), allocationIndex: integer(r.allocationIndex, 1, 4096) }; }
export function projection(v) { if (!v || typeof v !== 'object')
    invalid(); const p = v; if (p.kind === 'pending') {
    exact(p, ['kind', 'nextDueUs']);
    return { kind: 'pending', nextDueUs: p.nextDueUs === null ? null : decimal(p.nextDueUs) };
} exact(p, ['kind', 'nextDueUs', 'phase', 'evidenceSha256']); if (p.kind !== 'terminal' || p.nextDueUs !== null || !['completed', 'stopped'].includes(p.phase))
    invalid(); return { kind: 'terminal', nextDueUs: null, phase: p.phase, evidenceSha256: hex(p.evidenceSha256) }; }
export function ticket(v, c) { const t = exact(v, ['runId', 'wakeId', 'receipt', 'trackedVersion', 'attemptSequence']); return { runId: decimal(t.runId), wakeId: hex(t.wakeId, 128), receipt: receipt(t.receipt, c), trackedVersion: decimal(t.trackedVersion), attemptSequence: decimal(t.attemptSequence) }; }
export function disposition(v) { if (!v || typeof v !== 'object')
    invalid(); const d = v; if (d.status === 'pending') {
    exact(d, ['status', 'stateVersion']);
    return { status: 'pending', stateVersion: decimal(d.stateVersion) };
} if (d.status === 'terminal') {
    exact(d, ['status', 'stateVersion', 'projection']);
    const p = projection(d.projection);
    if (p.kind !== 'terminal')
        invalid();
    return { status: 'terminal', stateVersion: decimal(d.stateVersion), projection: p };
} exact(d, ['status']); if (!['empty_orphan', 'quarantined', 'busy', 'unavailable', 'conflict'].includes(d.status))
    invalid(); return { status: d.status }; }
export function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
export function next(v) { const n = BigInt(decimal(v)) + 1n; if (n > MAX)
    throw new Error('pending_exhausted'); return String(n); }
export async function wait(promise, ms) { let timer; try {
    return await Promise.race([promise.then(value => ({ ok: true, value }), () => ({ ok: false })), new Promise(resolve => { timer = setTimeout(() => resolve({ ok: false }), ms); })]);
}
finally {
    if (timer !== undefined)
        clearTimeout(timer);
} }

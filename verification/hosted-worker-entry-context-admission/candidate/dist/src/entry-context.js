import { config, identity, receipt, registryName, exact, wait, same } from './pending-types.js';
import { operationKey } from './principal.js';
export function budget(signal) { const started = performance.now(); return { remaining: () => Math.max(0, 4000 - (performance.now() - started)), check() { if (signal?.aborted || performance.now() - started >= 4000)
        throw new Error('entry_deadline'); } }; }
export async function pendingIdentity(r, c, b) { const key = await operationKey(r); b?.check(); const checked = await identity({ namespaceGeneration: c.generation, environmentId: r.environment_id, poolId: r.pool_id, controllerId: r.controller_id, platform: r.ref.platform, operationKey: key, operationId: r.operation_id, immutableSha256: r.immutable_sha256 }, c); b?.check(); return checked; }
export async function registration(env, c, i, b) {
    const checked = await identity(i, c);
    b?.check();
    const port = env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(c, checked.shard)));
    const result = await wait(port.register(checked.value), Math.min(250, b?.remaining() ?? 250));
    b?.check();
    if (!result.ok)
        throw new Error('entry_registration_unavailable');
    return checkedReceipt(result.value, c, checked.digest, checked.shard);
}
export function checkedReceipt(v, c, digest, shard) { const r = exact(v, ['status', 'receipt']); if (r.status !== 'registered' && r.status !== 'duplicate')
    throw new Error('entry_registration'); const p = receipt(r.receipt, c); if (p.identityDigest !== digest || p.shard !== shard)
    throw new Error('entry_receipt'); return p; }
export function registryPort(env, c, i) {
    const shard = parseInt(i.operationKey[0], 16), port = env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(c, shard)));
    return { register: value => port.register(value), track: value => port.track(value) };
}
export { config, identity, receipt, same };

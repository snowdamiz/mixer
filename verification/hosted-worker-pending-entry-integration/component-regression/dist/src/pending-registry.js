import { DurableObject } from 'cloudflare:workers';
import schema from './registry-schema.sql';
import { config, registryName, identity, identityFromBytes, receipt, projection, decimal, integer, hex, exact, same, next, randomId, ticket, disposition, encoder, wait } from './pending-types.js';
const initial = JSON.stringify({ kind: 'pending', nextDueUs: null });
export class MixerPendingRegistryShard extends DurableObject {
    c = null;
    shard = -1;
    available = false;
    constructor(ctx, env) {
        super(ctx, env);
        try {
            const c = config(env);
            this.c = c;
            for (let i = 0; i < 16; i++)
                if (ctx.id.equals(env.PENDING_REGISTRY.idFromName(registryName(c, i))))
                    this.shard = i;
            if (this.shard < 0)
                throw new Error('pending_namespace');
            ctx.storage.transactionSync(() => {
                const exists = ctx.storage.sql.exec("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_registry_meta'").toArray();
                if (exists.length) {
                    const m = ctx.storage.sql.exec('SELECT version,config,shard FROM pending_registry_meta').toArray();
                    if (m.length !== 1 || m[0].version !== 1 || m[0].config !== JSON.stringify(c) || m[0].shard !== this.shard)
                        throw new Error('pending_schema_config');
                }
                if (!exists.length && ctx.storage.sql.exec("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_registry_record'").toArray().length)
                    throw new Error('pending_schema_missing');
                ctx.storage.sql.exec(schema);
                ctx.storage.sql.exec('INSERT OR IGNORE INTO pending_registry_meta(singleton,version,config,shard,allocated) VALUES(1,1,?,?,0)', JSON.stringify(c), this.shard);
            });
            this.available = true;
        }
        catch {
            this.available = false;
        }
    }
    row(id) { return this.ctx.storage.sql.exec('SELECT * FROM pending_registry_record WHERE record_id=?', id).toArray()[0] ?? null; }
    receipt(r) { return { identityDigest: r.identity_digest, namespaceGeneration: this.c.generation, recordId: r.record_id, shard: this.shard, allocationIndex: r.allocation_index }; }
    matches(r, p) { return same(this.receipt(r), p); }
    bounded(r) { if (encoder.encode(JSON.stringify(r)).length > 4096)
        throw new Error('pending_record_limit'); }
    async register(value) {
        if (!this.available)
            return { status: 'unavailable' };
        try {
            const i = await identity(value, this.c);
            if (i.shard !== this.shard)
                return { status: 'conflict' };
            const id = randomId();
            const result = this.ctx.storage.transactionSync(() => {
                const old = this.ctx.storage.sql.exec('SELECT * FROM pending_registry_record WHERE operation_key=? OR identity_digest=?', i.value.operationKey, i.digest).toArray();
                if (old.length)
                    return old.length === 1 && old[0].identity_bytes === i.bytes && old[0].identity_digest === i.digest ? { status: 'duplicate', receipt: this.receipt(old[0]) } : { status: 'conflict' };
                const n = this.ctx.storage.sql.exec('SELECT allocated FROM pending_registry_meta WHERE singleton=1').toArray()[0].allocated;
                if (n >= 4096)
                    return { status: 'capacity' };
                this.ctx.storage.sql.exec('INSERT INTO pending_registry_record(allocation_index,operation_key,identity_bytes,identity_digest,record_id,state_version,projection_json,pending,failures,skip_visits,needs_attention,attempt_sequence) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', n + 1, i.value.operationKey, i.bytes, i.digest, id, '0', initial, 1, 0, 0, 0, '0');
                this.bounded(this.row(id));
                this.ctx.storage.sql.exec('UPDATE pending_registry_meta SET allocated=? WHERE singleton=1', n + 1);
                return { status: 'registered', receipt: this.receipt(this.row(id)) };
            });
            await this.ctx.storage.sync();
            return result;
        }
        catch (error) {
            return { status: error instanceof Error && error.message === 'pending_invalid' ? 'conflict' : 'unavailable' };
        }
    }
    async track(input) {
        if (!this.available)
            return { status: 'unavailable' };
        try {
            const a = exact(input, ['receipt', 'stateVersion', 'projection']), p = receipt(a.receipt, this.c), version = decimal(a.stateVersion), body = JSON.stringify(projection(a.projection));
            const result = this.ctx.storage.transactionSync(() => {
                const r = this.row(p.recordId);
                if (!r || !this.matches(r, p))
                    return { status: 'conflict' };
                if (BigInt(version) < BigInt(r.state_version))
                    return { status: 'stale', stateVersion: r.state_version };
                if (version === r.state_version)
                    return body === r.projection_json ? { status: 'duplicate', stateVersion: version } : { status: 'conflict' };
                if (!r.pending) {
                    if (projection(a.projection).kind !== 'terminal' || body !== r.projection_json)
                        return { status: 'conflict' };
                    this.ctx.storage.sql.exec('UPDATE pending_registry_record SET state_version=? WHERE record_id=?', version, p.recordId);
                    this.bounded(this.row(p.recordId));
                    return { status: 'accepted', stateVersion: version };
                }
                this.ctx.storage.sql.exec('UPDATE pending_registry_record SET state_version=?,projection_json=?,pending=?,ticket_json=NULL,disposition_json=NULL WHERE record_id=?', version, body, projection(a.projection).kind === 'terminal' ? 0 : 1, p.recordId);
                this.bounded(this.row(p.recordId));
                return { status: 'accepted', stateVersion: version };
            });
            await this.ctx.storage.sync();
            return result;
        }
        catch (error) {
            return { status: error instanceof Error && error.message === 'pending_invalid' ? 'conflict' : 'unavailable' };
        }
    }
    async scan_due(cursor, limit) {
        if (!this.available)
            throw new Error('pending_unavailable');
        exact(cursor, ['afterAllocationIndex']);
        const after = integer(cursor.afterAllocationIndex, 0, 4096), count = integer(limit, 1, 32);
        const records = [];
        let wrapped = false;
        // Two bounded indexed iterators, never an all-record materialization or offset.
        for (const tail of [true, false]) {
            const rows = tail ? this.ctx.storage.sql.exec('SELECT * FROM pending_registry_record WHERE pending=1 AND allocation_index>? ORDER BY allocation_index LIMIT ?', after, count) : this.ctx.storage.sql.exec('SELECT * FROM pending_registry_record WHERE pending=1 AND allocation_index<=? ORDER BY allocation_index LIMIT ?', after, count - records.length);
            for (const r of rows) {
                const item = { identity: identityFromBytes(r.identity_bytes), receipt: this.receipt(r), stateVersion: r.state_version, needsAttention: r.needs_attention === 1, skipVisits: r.skip_visits };
                const didWrap = wrapped || !tail;
                if (encoder.encode(JSON.stringify({ records: [...records, item], wrapped: didWrap })).length > 65536)
                    return { records, wrapped };
                records.push(item);
                wrapped = didWrap;
                if (records.length === count)
                    return { records, wrapped };
            }
        }
        return { records, wrapped };
    }
    async reserve_wake(recordId, expectedTrackVersion, runId) {
        if (!this.available)
            return { status: 'unavailable' };
        try {
            hex(recordId, 128);
            decimal(expectedTrackVersion);
            decimal(runId);
            const result = this.ctx.storage.transactionSync(() => {
                const r = this.row(recordId);
                if (!r)
                    return { status: 'stale' };
                if (!r.pending)
                    return { status: 'terminal' };
                if (r.state_version !== expectedTrackVersion)
                    return { status: 'stale' };
                if (r.last_run_id !== null && BigInt(runId) <= BigInt(r.last_run_id))
                    return { status: 'duplicate' };
                if (r.skip_visits > 0) {
                    this.ctx.storage.sql.exec("UPDATE pending_registry_record SET skip_visits=skip_visits-1,last_run_id=?,last_visit='backoff' WHERE record_id=?", runId, recordId);
                    return { status: 'backoff' };
                }
                const sequence = next(r.attempt_sequence), t = { runId, wakeId: randomId(), receipt: this.receipt(r), trackedVersion: r.state_version, attemptSequence: sequence };
                this.ctx.storage.sql.exec("UPDATE pending_registry_record SET attempt_sequence=?,last_run_id=?,last_visit='reserved',ticket_json=?,disposition_json=NULL WHERE record_id=?", sequence, runId, JSON.stringify(t), recordId);
                this.bounded(this.row(recordId));
                return { status: 'reserved', ticket: t };
            });
            await this.ctx.storage.sync();
            return result;
        }
        catch (error) {
            if (error instanceof Error && error.message === 'pending_exhausted') {
                try {
                    this.ctx.storage.sql.exec('UPDATE pending_registry_record SET needs_attention=1 WHERE record_id=? AND state_version=? AND pending=1', recordId, expectedTrackVersion);
                    await this.ctx.storage.sync();
                }
                catch { }
            }
            return { status: 'unavailable' };
        }
    }
    async finish_wake(value, result) {
        if (!this.available)
            return 'unavailable';
        try {
            const t = ticket(value, this.c), d = disposition(result);
            const status = this.ctx.storage.transactionSync(() => {
                const r = this.row(t.receipt.recordId);
                if (!r || !r.pending || !this.matches(r, t.receipt) || r.state_version !== t.trackedVersion || r.ticket_json !== JSON.stringify(t) || r.disposition_json !== null)
                    return 'stale';
                // Recovery dispositions update delivery only. Exact terminal tracking is the
                // sole authority to make a registry record quiescent.
                const success = (d.status === 'pending' || d.status === 'terminal') && BigInt(d.stateVersion) >= BigInt(t.trackedVersion);
                const failures = success ? 0 : Math.min(32, r.failures + 1), skip = success ? 0 : Math.min(7, 2 ** Math.min(failures, 3) - 1);
                this.ctx.storage.sql.exec('UPDATE pending_registry_record SET failures=?,skip_visits=?,needs_attention=?,disposition_json=? WHERE record_id=?', failures, skip, failures >= 8 ? 1 : 0, JSON.stringify(d), t.receipt.recordId);
                this.bounded(this.row(t.receipt.recordId));
                return 'accepted';
            });
            await this.ctx.storage.sync();
            return status;
        }
        catch {
            return 'unavailable';
        }
    }
}
// Caller-side routing is fixed and independently validates full identity bytes.
export class RegistryPort {
    env;
    constructor(env) {
        this.env = env;
    }
    async register(i) { try {
        const c = config(this.env), v = await identity(i, c), s = this.env.PENDING_REGISTRY.get(this.env.PENDING_REGISTRY.idFromName(registryName(c, v.shard)));
        const r = await wait(s.register(v.value), 250);
        if (!r.ok)
            return { status: 'unavailable' };
        const result = r.value;
        if (result.status === 'registered' || result.status === 'duplicate') {
            exact(result, ['status', 'receipt']);
            const p = receipt(result.receipt, c);
            if (p.identityDigest !== v.digest || p.shard !== v.shard)
                throw new Error('pending_receipt');
            return { status: result.status, receipt: p };
        }
        exact(result, ['status']);
        if (!['unavailable', 'capacity', 'conflict'].includes(result.status))
            throw new Error('pending_registration');
        return result;
    }
    catch {
        return { status: 'unavailable' };
    } }
    async track(a) { try {
        const c = config(this.env);
        exact(a, ['receipt', 'stateVersion', 'projection']);
        const p = receipt(a.receipt, c);
        decimal(a.stateVersion);
        projection(a.projection);
        const s = this.env.PENDING_REGISTRY.get(this.env.PENDING_REGISTRY.idFromName(registryName(c, p.shard)));
        const r = await wait(s.track(a), 250);
        if (!r.ok)
            return { status: 'unavailable' };
        const result = r.value;
        if (result.status === 'accepted' || result.status === 'duplicate' || result.status === 'stale') {
            exact(result, ['status', 'stateVersion']);
            decimal(result.stateVersion);
            if (result.status !== 'stale' && result.stateVersion !== a.stateVersion)
                throw new Error('pending_ack');
            return result;
        }
        exact(result, ['status']);
        if (!['unavailable', 'conflict'].includes(result.status))
            throw new Error('pending_ack');
        return result;
    }
    catch {
        return { status: 'unavailable' };
    } }
}

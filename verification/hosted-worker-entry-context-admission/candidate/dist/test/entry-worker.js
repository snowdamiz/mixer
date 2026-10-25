// EXCLUDED FINITE WORKER. Synthetic effects and controls never enter src closure.
import { DurableObject } from 'cloudflare:workers';
import entry from '../src/index.js';
import { MixerWorkerOperation } from '../src/operation.js';
import { OperationState } from '../src/operation-state.js';
import { MixerPendingRegistryShard } from '../src/pending-registry.js';
import { MixerPendingAuditCoordinator } from '../src/pending-audit.js';
import { Engine } from '../src/engine.js';
import { config, registryName, identity } from '../src/pending-types.js';
import { operationKey } from '../src/principal.js';
import { immutableBytes } from '../src/wire.js';
const json = (v) => new Response(JSON.stringify(v ?? { ok: true }), { headers: { 'content-type': 'application/json' } });
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
let events = [];
export class EntryRegistry extends MixerPendingRegistryShard {
    async register(i) {
        const mode = this.env.REGISTRY_MODE;
        if (mode === 'capacity' || mode === 'conflict' || mode === 'unavailable')
            return { status: mode };
        const r = await super.register(i);
        if (mode === 'timeout' || mode === 'late')
            await delay(mode === 'timeout' ? 320 : 160);
        if ((r.status === 'registered' || r.status === 'duplicate') && ['digest', 'generation', 'shard', 'record', 'extra'].includes(mode)) {
            const p = { ...r.receipt };
            if (mode === 'digest')
                p.identityDigest = 'b'.repeat(64);
            if (mode === 'generation')
                p.namespaceGeneration = 'b'.repeat(64);
            if (mode === 'shard')
                p.shard = (p.shard + 1) % 16;
            if (mode === 'record')
                p.recordId = 'short';
            return mode === 'extra' ? { ...r, extra: true } : { ...r, receipt: p };
        }
        return r;
    }
}
export { MixerWorkerOperation, MixerPendingAuditCoordinator };
export class EntryOperation extends DurableObject {
    state;
    constructor(ctx, env) { super(ctx, env); this.state = new OperationState(ctx, env, (_ledger, context) => this.createEngine(context)); }
    get ledger() { return this.state.ledger; }
    get engine() { return this.state.engine; }
    async fetch(request) { this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS entry_received(value TEXT NOT NULL)'); const text = await request.clone().text(); this.ctx.storage.sql.exec('INSERT INTO entry_received(value) VALUES(?)', JSON.stringify({ text, headers: Object.fromEntries(request.headers) })); return this.state.fetch(request); }
    async enrollExisting(i) { return this.state.enrollExisting(i); }
    async enrollAcrossRowChangeFixture(i) {
        // One finite local regression: change non-identity row history in the first
        // hash await after enrollment snapshots it. Production has no hook for this.
        const read = this.ledger.read.bind(this.ledger), trace = [];
        let armed = true;
        this.ledger.read = () => { const row = read(); if (armed) {
            armed = false;
            trace.push('snapshot-read');
            queueMicrotask(() => { this.ctx.storage.sql.exec('UPDATE operation SET failures=failures+1'); trace.push('row-history-changed'); });
        } return row; };
        try {
            return { status: await this.state.enrollExisting(i), trace };
        }
        finally {
            this.ledger.read = read;
        }
    }
    async alarm() { return this.state.alarm(); }
    held = null;
    resourceKind(platform) { return platform === 'ios' ? 'external-macos' : 'cloudflare-linux'; }
    setting() { return this.ctx.storage.sql.exec('SELECT value FROM entry_setting WHERE singleton=1').toArray()[0]?.value ?? 'normal'; }
    createEngine(context) {
        this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS entry_counts(kind TEXT PRIMARY KEY,n INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS entry_setting(singleton INTEGER PRIMARY KEY,value TEXT NOT NULL)');
        this.count('engine');
        const clock = { sample: () => this.setting() === 'clock-unavailable' ? null : { lowerUs: 1900000000000000n, upperUs: 1900000000000001n, qualificationId: 'entry-fixture-only' } };
        const observation = (e) => ({ identity: e.identity, state: 'inert', instanceId: 'entry-instance', bootId: 'entry-boot', definitive: false, descendantsGone: false, launchesSettled: false, diagnosticSha256: 'd'.repeat(64) });
        const provider = { available: true, kind: p => this.resourceKind(p),
            launchInert: async (e, signal) => { this.count('launch'); if (this.setting() === 'hold')
                await new Promise((resolve, reject) => { this.held = resolve; signal.addEventListener('abort', () => reject(new Error('fixture_abort')), { once: true }); }); return observation(e); },
            inspect: async (e) => { this.count('inspect'); return observation(e); },
            stop: async (e) => { this.count('stop'); return { ...observation(e), state: 'absent', instanceId: null, bootId: null, definitive: this.setting() !== 'stop-pending', descendantsGone: this.setting() !== 'stop-pending', launchesSettled: this.setting() !== 'stop-pending' }; } };
        return new Engine(this.ledger, clock, provider, { async verify() { return false; } }, undefined, context);
    }
    count(kind) { this.ctx.storage.sql.exec('INSERT INTO entry_counts(kind,n) VALUES(?,1) ON CONFLICT(kind) DO UPDATE SET n=n+1', kind); }
    async recoverKnown(i, p, t) { this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS recovery_calls(value TEXT NOT NULL)'); this.ctx.storage.sql.exec('INSERT INTO recovery_calls(value) VALUES(?)', JSON.stringify([i, p, t])); return this.state.recoverKnown(i, p, t); }
    async inspectFixture() { const tables = this.ctx.storage.sql.exec("SELECT name FROM sqlite_master WHERE type='table'").toArray().map(x => x.name); return { received: tables.includes('entry_received') ? this.ctx.storage.sql.exec('SELECT value FROM entry_received').toArray().map(x => JSON.parse(x.value)) : [], row: this.ledger.read(), fenced: this.ledger.fenced(), counts: tables.includes('entry_counts') ? this.ctx.storage.sql.exec('SELECT * FROM entry_counts ORDER BY kind').toArray() : [], recoveries: tables.includes('recovery_calls') ? this.ctx.storage.sql.exec('SELECT value FROM recovery_calls').toArray().map(x => JSON.parse(x.value)) : [], alarm: await this.ctx.storage.getAlarm() }; }
    async settingFixture(value) { this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS entry_setting(singleton INTEGER PRIMARY KEY,value TEXT NOT NULL)'); this.ctx.storage.sql.exec('INSERT INTO entry_setting(singleton,value) VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value', value); if (value === 'release')
        this.held?.(); }
    async mutateFixture(kind) {
        if (kind === 'malformed-receipt')
            this.ctx.storage.sql.exec("UPDATE operation SET registration_json='{}'");
        else if (kind === 'missing-identity')
            this.ctx.storage.sql.exec('UPDATE operation SET pending_identity_json=NULL');
        else if (kind === 'extra-identity') {
            const r = this.ledger.read();
            this.ctx.storage.sql.exec('UPDATE operation SET pending_identity_json=?', JSON.stringify({ ...JSON.parse(r.pending_identity_json), extra: true }));
        }
        else if (kind === 'history')
            this.ctx.storage.sql.exec("UPDATE operation SET registry_ack_version='9223372036854775807'");
        else if (kind === 'max')
            this.ctx.storage.sql.exec("UPDATE operation SET state_version='9223372036854775807',registry_ack_version='9223372036854775807',track_outbox_json=NULL");
        else if (kind === 'migration') {
            this.ctx.storage.sql.exec('UPDATE operation SET pending_identity_json=NULL,registration_json=NULL,track_outbox_json=NULL,registry_ack_version=\'0\',effect_barrier_version=NULL,claim_barrier_version=NULL,quarantined=1');
        }
        else if (kind === 'delete-row')
            this.ctx.storage.sql.exec('DELETE FROM operation');
        else if (kind === 'binding-sha-mismatch') {
            const row = this.ledger.read(), request = JSON.parse(row.request_json);
            request.spec.source.reference = 'finite-admission-fixture';
            this.ctx.storage.sql.exec('UPDATE operation SET request_json=?,binding=?', JSON.stringify(request), immutableBytes(request));
        }
        else
            throw new Error('fixture_mutation');
        await this.ledger.sync();
    }
    async alarmFixture() { await this.ctx.storage.deleteAlarm(); await this.state.alarm(); }
    async dropAlarmFixture() { await this.ctx.storage.deleteAlarm(); }
    async claimFixture(value) { return this.engine ? this.engine.claim(value) : { granted: false }; }
    async reportFixture(value) { return this.engine ? this.engine.report(value) : 'rejected'; }
}
export class ForeignOperation extends EntryOperation {
}
export default {
    async fetch(request, env) {
        const path = new URL(request.url).pathname;
        if (!path.startsWith('/__entry/'))
            return entry.fetch(request, env);
        const arg = await request.json();
        if (arg.action === 'events')
            return json(events);
        if (arg.action === 'command') {
            const c = env.OUTER_MODE === 'missing' ? undefined : env.OUTER_MODE === 'bad-generation' ? JSON.stringify({ ...config(env), generation: 'A'.repeat(64) }) : env.OUTER_MODE === 'changed-generation' ? JSON.stringify({ ...config(env), generation: 'b'.repeat(64) }) : env.OUTER_MODE === 'changed-namespace' ? JSON.stringify({ ...config(env), operationsNamespace: 'other' }) : env.MIXER_PENDING_CONFIG;
            const wrapped = { ...env, MIXER_PENDING_CONFIG: c, OPERATIONS: { idFromName: (key) => { events.push(['operation-id', key]); return env.OPERATIONS.idFromName(env.OUTER_MODE === 'wrong-id' ? 'wrong' : key); }, get: (id) => { events.push(['operation-get', id.toString()]); return env.OPERATIONS.get(id); } }, PENDING_REGISTRY: { idFromName: (key) => { events.push(['registry-id', key]); return env.PENDING_REGISTRY.idFromName(key); }, get: (id) => { const p = env.PENDING_REGISTRY.get(id); return { register: async (i) => { events.push(['register-start', i]); const r = await p.register(i); events.push(['register-ack', r]); return r; } }; } } };
            const bytes = new TextEncoder().encode(arg.bodyText ?? JSON.stringify(arg.r));
            const d = Number(env.BODY_DELAY);
            let sent = false;
            const body = d ? new ReadableStream({ async pull(controller) { if (sent)
                    return; sent = true; await delay(d); controller.enqueue(bytes); controller.close(); } }) : bytes;
            const aborter = new AbortController();
            if (env.OUTER_MODE === 'abort-before')
                aborter.abort();
            if (env.OUTER_MODE === 'abort-during')
                setTimeout(() => aborter.abort(), 30);
            const started = performance.now();
            const response = await entry.fetch(new Request('https://entry.test/internal/mixer-build-worker/v1', { method: 'POST', headers: arg.headers ?? { authorization: request.headers.get('authorization') ?? '', 'content-type': 'application/json' }, body, signal: aborter.signal }), wrapped);
            const entryElapsed = performance.now() - started;
            if (d)
                await delay(350);
            return json({ status: response.status, entryElapsed, headers: Object.fromEntries(response.headers), body: await response.json() });
        }
        const key = arg.i?.operationKey ?? await operationKey(arg.r), id = env.OPERATIONS.idFromName(arg.target === 'wrong' ? 'wrong' : key), op = (arg.target === 'foreign' ? env.FOREIGN_OPERATIONS.get(env.FOREIGN_OPERATIONS.idFromName(key)) : env.OPERATIONS.get(id));
        if (arg.action === 'inspect')
            return json(await op.inspectFixture());
        if (arg.action === 'set')
            return json(await op.settingFixture(arg.value));
        if (arg.action === 'mutate')
            return json(await op.mutateFixture(arg.kind));
        if (arg.action === 'recover')
            return json(await op.recoverKnown(arg.i, arg.p, arg.t));
        if (arg.action === 'enroll')
            return json(await op.enrollExisting(arg.i));
        if (arg.action === 'enroll-row-change')
            return json(await op.enrollAcrossRowChangeFixture(arg.i));
        if (arg.action === 'claim')
            return json(await op.claimFixture(arg.payload));
        if (arg.action === 'report')
            return json(await op.reportFixture(arg.payload));
        if (arg.action === 'drop-alarm')
            return json(await op.dropAlarmFixture());
        if (arg.action === 'alarm')
            return json(await op.alarmFixture());
        if (arg.action === 'direct') {
            const response = await op.fetch(new Request('https://entry.test/internal/mixer-build-worker/v1', { method: 'POST', headers: { authorization: request.headers.get('authorization') ?? '', 'content-type': 'application/json' }, body: JSON.stringify(arg.r) }));
            return json({ status: response.status, body: await response.json() });
        }
        if (arg.action === 'register') {
            const c = config(env), i = await identity(arg.i, c), port = env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(c, i.shard)));
            return json(await port.register(i.value));
        }
        if (arg.action === 'reserve') {
            const port = env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(config(env), arg.p.shard)));
            return json(await port.reserve_wake(arg.p.recordId, '0', '1'));
        }
        if (arg.action === 'finish') {
            const port = env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(config(env), arg.p.shard)));
            return json(await port.finish_wake(arg.t, { status: 'empty_orphan' }));
        }
        return new Response('{}', { status: 404 });
    },
    async scheduled(event, env) { await entry.scheduled(event, env); }
};

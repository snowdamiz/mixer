// EXCLUDED finite verification entry. No production route or qualified provider.
import { DurableObject } from 'cloudflare:workers';
import { Engine } from '../src/engine.js';
import { Ledger } from '../src/ledger.js';
import { decode } from '../src/wire.js';
import { MixerPendingRegistryShard, RegistryPort } from '../src/vendor/pending-registry.js';
import { config, registryName } from '../src/vendor/pending-types.js';
const defaults = () => ({ clock: '1900000000000000', qualified: true, drained: false, fault: null, blocked: false });
const response = (v) => new Response(JSON.stringify(v), { headers: { 'Content-Type': 'application/json' } });
class Store {
    sql;
    constructor(sql) {
        this.sql = sql;
        sql.exec('CREATE TABLE IF NOT EXISTS fixture_settings(singleton INTEGER PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS fixture_calls(sequence INTEGER PRIMARY KEY AUTOINCREMENT,value TEXT NOT NULL)');
    }
    get() { const r = this.sql.exec('SELECT value FROM fixture_settings WHERE singleton=1').toArray()[0]; return r ? JSON.parse(r.value) : defaults(); }
    set(v) { this.sql.exec('INSERT INTO fixture_settings VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value', JSON.stringify(v)); }
}
class SyntheticClock {
    s;
    constructor(s) {
        this.s = s;
    }
    sample() { const s = this.s.get(); return s.qualified ? { lowerUs: BigInt(s.clock) - 1n, upperUs: BigInt(s.clock) + 1n, qualificationId: 'excluded-pending-registry-engine-fixture' } : null; }
}
class FixtureHooks {
    s;
    resolve = null;
    constructor(s) {
        this.s = s;
    }
    async point(name) { const s = this.s.get(); if (s.fault !== name)
        return; s.fault = null; s.blocked = true; this.s.set(s); await new Promise(resolve => { this.resolve = resolve; }); }
}
class FixtureProvider {
    s;
    available = true;
    constructor(s) {
        this.s = s;
    }
    kind() { return 'cloudflare-linux'; }
    async perform(e) {
        this.s.sql.exec('INSERT INTO fixture_calls(value) VALUES(?)', JSON.stringify({ kind: e.kind, id: e.id, identity: e.identity }));
        const stop = e.kind === 'stop', drain = this.s.get().drained;
        return { identity: e.identity, state: stop ? 'absent' : 'inert', instanceId: stop ? null : 'instance-1', bootId: stop ? null : 'boot-1', definitive: stop && drain, descendantsGone: stop && drain, launchesSettled: stop && drain, diagnosticSha256: 'd'.repeat(64) };
    }
    launchInert(e) { return this.perform(e); }
    inspect(e) { return this.perform(e); }
    stop(e) { return this.perform(e); }
}
export class TestRegistry extends MixerPendingRegistryShard {
    releaseAck = null;
    setting() { const r = this.ctx.storage.sql.exec('SELECT value FROM fixture_registry WHERE singleton=1').toArray()[0]; return r ? JSON.parse(r.value) : { mode: 'normal', skip: 0, blocked: false }; }
    set(v) { this.ctx.storage.sql.exec('INSERT INTO fixture_registry VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value', JSON.stringify(v)); }
    constructor(ctx, env) { super(ctx, env); ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS fixture_registry(singleton INTEGER PRIMARY KEY,value TEXT NOT NULL)'); }
    async register(i) { if (this.setting().mode === 'register_unavailable')
        return { status: 'unavailable' }; const r = await super.register(i); if (this.setting().mode === 'register_lost')
        return { status: 'unavailable' }; if (this.setting().mode === 'review_register_hold') {
        this.set({ mode: 'normal', skip: 0, blocked: true });
        await new Promise(resolve => { this.releaseAck = resolve; });
    } return r; }
    async track(a) {
        const s = this.setting();
        if (s.mode === 'unavailable')
            return { status: 'unavailable' };
        if (s.skip > 0) {
            s.skip--;
            this.set(s);
            return super.track(a);
        }
        if (s.mode === 'drop_before_once') {
            this.set({ mode: 'normal', skip: 0, blocked: false });
            return { status: 'unavailable' };
        }
        if (s.mode === 'lost_once') {
            this.set({ mode: 'normal', skip: 0, blocked: false });
            await super.track(a);
            return { status: 'unavailable' };
        }
        if (s.mode === 'hold_after_once' || s.mode === 'hold_before_once') {
            this.set({ mode: 'normal', skip: 0, blocked: true });
            const result = s.mode === 'hold_after_once' ? await super.track(a) : null;
            await new Promise(resolve => { this.releaseAck = resolve; });
            return result ?? super.track(a);
        }
        return super.track(a);
    }
    async fixture(action, arg) {
        if (action === 'mode') {
            this.set({ mode: arg.mode, skip: arg.skip ?? 0, blocked: false });
            return { ok: true };
        }
        if (action === 'release') {
            this.releaseAck?.();
            this.releaseAck = null;
            return { ok: true };
        }
        return { settings: this.setting(), records: this.ctx.storage.sql.exec('SELECT * FROM pending_registry_record ORDER BY allocation_index').toArray() };
    }
}
export class TestOperation extends DurableObject {
    ledger;
    engine;
    store;
    hooks;
    provider;
    identity;
    constructor(ctx, env) {
        super(ctx, env); // Member order is deliberately permuted; canonical identity is the fixed tuple.
        this.identity = Object.fromEntries(Object.entries(JSON.parse(env.FIXTURE_IDENTITY)).reverse());
        this.ledger = new Ledger(ctx.storage);
        this.store = new Store(ctx.storage.sql);
        this.hooks = new FixtureHooks(this.store);
        this.provider = new FixtureProvider(this.store);
        const hooks = this.hooks;
        this.engine = new Engine(this.ledger, new SyntheticClock(this.store), this.provider, { async verify() { await hooks.point('during_report_verify'); return true; } }, this.hooks, { identity: this.identity, registry: new RegistryPort(env) });
        ctx.blockConcurrencyWhile(() => this.engine.recover());
    }
    async fixture(action, arg) {
        const resource = { provider: 'cloudflare-linux', key: this.identity.operationKey, immutableSha256: this.identity.immutableSha256 };
        switch (action) {
            case 'command': {
                const r = await decode(new TextEncoder().encode(JSON.stringify(arg.request)));
                return this.engine.commandRegistered(r, (arg.resource ?? resource), (arg.identity ?? this.identity), arg.receipt);
            }
            case 'plain': {
                const r = await decode(new TextEncoder().encode(JSON.stringify(arg.request)));
                return this.engine.command(r, resource);
            }
            case 'defaultUnavailable': {
                const r = await decode(new TextEncoder().encode(JSON.stringify(arg.request)));
                return new Engine(this.ledger, new SyntheticClock(this.store), this.provider, { async verify() { return true; } }).commandRegistered(r, resource, this.identity, arg.receipt);
            }
            case 'raw': return { row: this.ledger.read(), alarm: await this.ctx.storage.getAlarm(), fence: this.ctx.storage.sql.exec('SELECT * FROM registry_quarantine').toArray(), calls: this.ctx.storage.sql.exec('SELECT value FROM fixture_calls ORDER BY sequence').toArray().map(r => JSON.parse(r.value)), settings: this.store.get(), schema: this.ctx.storage.sql.exec('SELECT version FROM controller_schema').toArray() };
            case 'clock': {
                const s = this.store.get();
                s.clock = arg.now;
                s.qualified = arg.qualified !== false;
                this.store.set(s);
                return { ok: true };
            }
            case 'drain': {
                const s = this.store.get();
                s.drained = arg.value === true;
                this.store.set(s);
                return { ok: true };
            }
            case 'inject': {
                const s = this.store.get();
                s.fault = arg.point;
                s.blocked = false;
                this.store.set(s);
                return { ok: true };
            }
            case 'release':
                this.hooks.resolve?.();
                this.hooks.resolve = null;
                return { ok: true };
            case 'reconcile':
                await this.engine.reconcile();
                return { ok: true };
            case 'flush': return { flushed: await this.engine.flushTrack() };
            case 'claim': {
                const r = this.ledger.read();
                return r ? this.engine.claim({ identity: this.ledger.identity(r), immutableSha256: r.binding_hash, instanceId: 'instance-1', bootId: 'boot-1' }) : { granted: false };
            }
            case 'report': {
                const r = this.ledger.read();
                if (!r)
                    return { status: 'rejected' };
                return { status: await this.engine.report({ identity: this.ledger.identity(r), immutableSha256: r.binding_hash, instanceId: r.instance_id, bootId: r.boot_id, claimId: r.claim_id, operationId: r.operation_id, result: { outcome: 'failed', class: 'compiler', code: 'compiler_error', diagnostic_sha256: 'a'.repeat(64) }, attestationSha256: 'a'.repeat(64) }) };
            }
            case 'recoverKnown': return this.engine.recoverKnown((arg.identity ?? this.identity), arg.receipt, arg.ticket);
            case 'enroll': return { status: await this.engine.enrollExisting((arg.identity ?? this.identity)) };
            case 'quarantine':
                await this.engine.quarantine();
                return { ok: true };
            case 'providerMismatch':
                this.ctx.storage.sql.exec("UPDATE operation SET provider_kind='external-macos'");
                await this.ledger.sync();
                return { ok: true };
            case 'reviewMutation': {
                // EXCLUDED independent review: closed, finite same-version restore cases.
                const statements = {
                    epoch: "UPDATE operation SET epoch='2'", revision: "UPDATE operation SET revision='2'",
                    expiry_us: "UPDATE operation SET expiry_us='2000000000000000'",
                    clock_lower: "UPDATE operation SET clock_lower='1'", clock_upper: "UPDATE operation SET clock_upper='2'",
                    clock_qualification: "UPDATE operation SET clock_qualification='excluded-different-qualification'",
                    clock_floor: "UPDATE operation SET clock_floor='1'", claim_state: "UPDATE operation SET claim_state='revoked'",
                    phase: "UPDATE operation SET phase='running'", effect_id: "UPDATE operation SET effect_id='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'",
                    effect_kind: "UPDATE operation SET effect_kind='stop'", effect_request_json: "UPDATE operation SET effect_request_json=effect_request_json||' '",
                    effect_state: "UPDATE operation SET effect_state='uncertain'", effect_barrier_version: "UPDATE operation SET effect_barrier_version='0'",
                    launch_dispatched: "UPDATE operation SET launch_dispatched=0", quarantined: "UPDATE operation SET quarantined=1",
                    desired: "UPDATE operation SET desired='none'", report_hash: "UPDATE operation SET report_hash='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'",
                    pending_result_json: "UPDATE operation SET pending_result_json='{}'", terminal_json: "UPDATE operation SET terminal_json='{\"status\":\"stopped\"}'",
                    next_due_us: "UPDATE operation SET next_due_us='1'", failures: "UPDATE operation SET failures=1"
                };
                const statement = statements[arg.field];
                if (!statement)
                    throw new Error('excluded_review_field');
                this.ctx.storage.sql.exec(statement);
                await this.ledger.sync();
                return { ok: true };
            }
            case 'reportBindingMutation': {
                // Closed restore/race fixtures only. No arbitrary SQL/field/value interface.
                switch (arg.field) {
                    case 'pending_identity_json':
                        this.ctx.storage.sql.exec('UPDATE operation SET pending_identity_json=?', JSON.stringify({ ...this.identity, platform: 'ios' }));
                        break;
                    case 'registration_json': {
                        const r = this.ledger.read(), receipt = JSON.parse(r.registration_json);
                        receipt.recordId = 'f'.repeat(32);
                        this.ctx.storage.sql.exec('UPDATE operation SET registration_json=?', JSON.stringify(receipt));
                        break;
                    }
                    case 'binding':
                        this.ctx.storage.sql.exec("UPDATE operation SET binding=binding||' '");
                        break;
                    case 'binding_hash':
                        this.ctx.storage.sql.exec('UPDATE operation SET binding_hash=?', 'f'.repeat(64));
                        break;
                    case 'provider_key':
                        this.ctx.storage.sql.exec('UPDATE operation SET provider_key=?', 'f'.repeat(64));
                        break;
                    case 'provider_kind':
                        this.ctx.storage.sql.exec("UPDATE operation SET provider_kind='external-macos'");
                        break;
                    case 'operation_id':
                        this.ctx.storage.sql.exec('UPDATE operation SET operation_id=?', 'f'.repeat(64));
                        break;
                    case 'claim_id':
                        this.ctx.storage.sql.exec('UPDATE operation SET claim_id=?', 'f'.repeat(32));
                        break;
                    case 'instance_id':
                        this.ctx.storage.sql.exec("UPDATE operation SET instance_id='excluded-other-instance'");
                        break;
                    case 'boot_id':
                        this.ctx.storage.sql.exec("UPDATE operation SET boot_id='excluded-other-boot'");
                        break;
                    case 'claim_barrier_version':
                        this.ctx.storage.sql.exec("UPDATE operation SET claim_barrier_version='0'");
                        break;
                    case 'clock_floor':
                        this.ctx.storage.sql.exec("UPDATE operation SET clock_floor='1'");
                        break;
                    case 'owner':
                        this.ctx.storage.sql.exec("UPDATE operation SET owner='excluded-other-owner'");
                        break;
                    case 'request_json': {
                        const r = this.ledger.read(), request = JSON.parse(r.request_json);
                        request.guard.owner_id = 'excluded-other-owner';
                        this.ctx.storage.sql.exec('UPDATE operation SET request_json=?', JSON.stringify(request));
                        break;
                    }
                    default: throw new Error('excluded_field');
                }
                await this.ledger.sync();
                return { ok: true };
            }
            case 'fenceOnly':
                this.ctx.storage.sql.exec("INSERT OR IGNORE INTO registry_quarantine VALUES(1,?,'0','excluded_fence_restore')", JSON.stringify(this.identity));
                await this.ledger.sync();
                return { ok: true };
            case 'deleteRow':
                this.ctx.storage.sql.exec('DELETE FROM operation');
                await this.ledger.sync();
                return { ok: true };
            case 'regress':
                this.ctx.storage.sql.exec("UPDATE operation SET state_version='0',track_outbox_json=NULL");
                await this.ledger.sync();
                return { ok: true };
            case 'legacy': {
                const before = this.ledger.read();
                this.ctx.storage.transactionSync(() => {
                    for (const k of ['pending_identity_json', 'registration_json', 'registry_ack_version', 'effect_barrier_version', 'claim_barrier_version', 'track_outbox_json'])
                        this.ctx.storage.sql.exec('ALTER TABLE operation DROP COLUMN ' + k);
                    if (arg.version === 1)
                        this.ctx.storage.sql.exec('ALTER TABLE operation DROP COLUMN clock_floor');
                    this.ctx.storage.sql.exec('DROP TABLE registry_quarantine');
                    this.ctx.storage.sql.exec('DROP TABLE controller_schema');
                    this.ctx.storage.sql.exec('CREATE TABLE controller_schema(version INTEGER NOT NULL)');
                    this.ctx.storage.sql.exec('INSERT INTO controller_schema VALUES(?)', arg.version);
                });
                new Ledger(this.ctx.storage);
                return { before, after: this.ledger.read() };
            }
            case 'partialMetadata': {
                this.ctx.storage.sql.exec('DROP TABLE controller_schema');
                let unavailable = false;
                try {
                    new Ledger(this.ctx.storage);
                }
                catch {
                    unavailable = true;
                }
                return { unavailable, row: this.ledger.read(), fence: this.ledger.fenced() };
            }
            case 'missingSafetyTable': {
                this.ctx.storage.sql.exec('DROP TABLE registry_quarantine');
                try {
                    new Ledger(this.ctx.storage);
                    return { unavailable: false };
                }
                catch {
                    return { unavailable: true };
                }
            }
        }
        throw new Error('fixture_action');
    }
    async alarm() { await this.engine.alarm(); }
}
export default { async fetch(request, env) {
        if (new URL(request.url).pathname !== '/__test/engine' || request.method !== 'POST')
            return new Response('excluded fixture only', { status: 404 });
        try {
            const a = await request.json(), action = a.action, identity = JSON.parse(env.FIXTURE_IDENTITY);
            const shard = env.PENDING_REGISTRY.get(env.PENDING_REGISTRY.idFromName(registryName(config(env), parseInt(identity.operationKey[0], 16))));
            if (action === 'register')
                return response(await new RegistryPort(env).register(identity));
            if (action === 'registry')
                return response(await shard.fixture(a.command, a));
            if (action === 'reserve')
                return response(await shard.reserve_wake(a.recordId, a.version, a.runId));
            if (action === 'forceTrack')
                return response(await shard.track(a.input));
            const operation = env.OPERATIONS.get(env.OPERATIONS.idFromName(identity.operationKey));
            return response(await operation.fixture(action, a));
        }
        catch (e) {
            return response({ fixtureError: e instanceof Error ? e.message : 'unknown' });
        }
    } };

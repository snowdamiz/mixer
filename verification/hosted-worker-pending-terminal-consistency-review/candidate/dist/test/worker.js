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
        return { status: 'unavailable' }; return r; }
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
            case 'independentValidShapeReport': {
                const r = this.ledger.read();
                return { status: await this.engine.report({ identity: this.ledger.identity(r), immutableSha256: r.binding_hash, instanceId: r.instance_id ?? 'review-instance', bootId: r.boot_id ?? 'review-boot', claimId: r.claim_id ?? 'a'.repeat(32), operationId: r.operation_id, result: { outcome: 'failed', class: 'compiler', code: 'compiler_error', diagnostic_sha256: 'a'.repeat(64) }, attestationSha256: 'a'.repeat(64) }) };
            }
            case 'independentAckAhead': {
                const r = this.ledger.read();
                if (r.track_outbox_json !== null || !r.terminal_json || BigInt(r.state_version) < 2n)
                    throw new Error('review_terminal_ack_required');
                this.ctx.storage.sql.exec('UPDATE operation SET state_version=?', String(BigInt(r.state_version) - 1n));
                await this.ledger.sync();
                return { ok: true };
            }
            case 'independentTerminalBytes': {
                const r = this.ledger.read(), o = JSON.parse(r.track_outbox_json);
                let bytes;
                if (arg.kind === 'validEscapedStatus')
                    bytes = ' {\"diagnostic_sha256\":\"' + 'd'.repeat(64) + '\",\"statu\\u0073\":\"stop\\u0070ed\"}\n';
                else if (arg.kind === 'escapedDuplicate')
                    bytes = '{\"status\":\"stopped\",\"statu\\u0073\":\"stopped\",\"diagnostic_sha256\":\"' + 'd'.repeat(64) + '\"}';
                else if (arg.kind === 'extraTerminalField')
                    bytes = JSON.stringify({ ...JSON.parse(r.terminal_json), recovery: true });
                else if (arg.kind === 'duplicateResult')
                    bytes = '{\"status\":\"completed\",\"result\":{\"outcome\":\"failed\",\"class\":\"compiler\",\"code\":\"compiler_error\",\"code\":\"compiler_error\",\"diagnostic_sha256\":\"' + 'a'.repeat(64) + '\"}}';
                else if (arg.kind === 'tooManyBytes')
                    bytes = ' '.repeat(32768) + r.terminal_json;
                else
                    throw new Error('review_terminal_case');
                o.terminal.exactJson = bytes;
                this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?,track_outbox_json=?', bytes, JSON.stringify(o));
                await this.ledger.sync();
                return { ok: true };
            }
            case 'independentPreserveFence': {
                const before = this.ledger.read();
                let rolledBack = false;
                try {
                    this.ctx.storage.transactionSync(() => { const r = this.ledger.read(); this.ledger.fence('independent-review-identity', r.state_version, 'independent_review_first', true); if (arg.rollback === true) {
                        this.ctx.storage.sql.exec("UPDATE operation SET owner='rollback-owner'");
                        throw new Error('review_rollback');
                    } this.ledger.fence('replacement-identity', '0', 'replacement-reason', true); });
                }
                catch (e) {
                    if (e.message !== 'review_rollback')
                        throw e;
                    rolledBack = true;
                }
                await this.ledger.sync();
                return { before, after: this.ledger.read(), rolledBack };
            }
            case 'rememberTerminal': {
                this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS fixture_terminal_original(singleton INTEGER PRIMARY KEY,value TEXT NOT NULL)');
                this.ctx.storage.sql.exec('INSERT INTO fixture_terminal_original VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET value=excluded.value', JSON.stringify(this.ledger.read()));
                await this.ledger.sync();
                return { ok: true };
            }
            case 'restoreTerminal': {
                const original = JSON.parse(this.ctx.storage.sql.exec('SELECT value FROM fixture_terminal_original WHERE singleton=1').toArray()[0].value);
                // Keys originate exclusively in our own remembered SQLite row, never caller input.
                const keys = Object.keys(original);
                this.ctx.storage.sql.exec('UPDATE operation SET ' + keys.map(k => k + '=?').join(','), ...keys.map(k => original[k]));
                await this.ledger.sync();
                return { ok: true };
            }
            case 'terminalAckSyncMutation': {
                const original = this.ledger.sync.bind(this.ledger), storage = this.ctx.storage;
                this.ledger.sync = async () => { this.ledger.sync = original; await original(); storage.sql.exec("UPDATE operation SET phase=CASE phase WHEN 'stopped' THEN 'completed' ELSE 'stopped' END"); await original(); };
                return { ok: true };
            }
            case 'terminalMutation': {
                const r = this.ledger.read(), o = r.track_outbox_json ? JSON.parse(r.track_outbox_json) : null;
                const opposite = r.phase === 'stopped' ? 'completed' : 'stopped';
                switch (arg.field) {
                    case 'exactWhitespace': {
                        const exact = ' \n' + r.terminal_json + ' \n';
                        this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?', exact);
                        o.terminal.exactJson = exact;
                        break;
                    }
                    case 'outboxPhase':
                        o.terminal.phase = opposite;
                        break;
                    case 'rowPhase':
                        this.ctx.storage.sql.exec('UPDATE operation SET phase=?', opposite);
                        break;
                    case 'rowAndOutboxPhase':
                        this.ctx.storage.sql.exec('UPDATE operation SET phase=?', opposite);
                        o.terminal.phase = opposite;
                        break;
                    case 'terminalStatus': {
                        const t = JSON.parse(r.terminal_json);
                        t.status = opposite;
                        this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?', JSON.stringify(t));
                        break;
                    }
                    case 'missingTerminal':
                        this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=NULL');
                        break;
                    case 'missingProjectionTerminal':
                        o.terminal = null;
                        break;
                    case 'missingBothTerminal':
                        this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=NULL');
                        o.terminal = null;
                        break;
                    case 'pendingPhase':
                        this.ctx.storage.sql.exec("UPDATE operation SET phase='stop_pending'");
                        break;
                    case 'terminalNextDue':
                        this.ctx.storage.sql.exec("UPDATE operation SET next_due_us='1'");
                        break;
                    case 'projectionNextDue':
                        o.nextDueUs = '1';
                        break;
                    case 'malformedTerminal':
                        this.ctx.storage.sql.exec("UPDATE operation SET terminal_json='{' ");
                        break;
                    case 'terminalArray':
                        this.ctx.storage.sql.exec("UPDATE operation SET terminal_json='[]'");
                        break;
                    case 'terminalNull':
                        this.ctx.storage.sql.exec("UPDATE operation SET terminal_json='null'");
                        break;
                    case 'terminalUnknownStatus':
                        this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?', '{"status":"running"}');
                        break;
                    case 'terminalDuplicateStatus':
                        this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?', '{"status":"completed","status":"stopped","diagnostic_sha256":"' + 'd'.repeat(64) + '"}');
                        break;
                    case 'terminalInvalidBody':
                        this.ctx.storage.sql.exec('UPDATE operation SET terminal_json=?', JSON.stringify(r.phase === 'completed' ? { status: 'completed', result: { outcome: 'failed' } } : { status: 'stopped', diagnostic_sha256: 'invalid' }));
                        break;
                    case 'exactJsonMismatch':
                        o.terminal.exactJson += ' ';
                        break;
                    case 'projectionFalse':
                        o.terminal = false;
                        break;
                    case 'projectionMissingField':
                        delete o.terminal;
                        break;
                    case 'malformedOutbox':
                        this.ctx.storage.sql.exec("UPDATE operation SET track_outbox_json='{' ");
                        await this.ledger.sync();
                        return { ok: true };
                    case 'missingOutbox':
                        this.ctx.storage.sql.exec('UPDATE operation SET track_outbox_json=NULL');
                        await this.ledger.sync();
                        return { ok: true };
                    case 'unexpectedTerminal':
                        o.terminal = { phase: 'stopped', exactJson: JSON.stringify({ status: 'stopped', diagnostic_sha256: 'd'.repeat(64) }) };
                        break;
                    case 'terminalPhaseWithoutEvidence':
                        this.ctx.storage.sql.exec("UPDATE operation SET phase='stopped'");
                        break;
                    case 'missingTerminalAndProvider':
                        this.ctx.storage.sql.exec("UPDATE operation SET terminal_json=NULL,provider_kind='external-macos'");
                        break;
                    case 'malformedTerminalAndProvider':
                        this.ctx.storage.sql.exec("UPDATE operation SET terminal_json='{',provider_kind='external-macos'");
                        break;
                    default: throw new Error('terminal_mutation');
                }
                if (o !== null)
                    this.ctx.storage.sql.exec('UPDATE operation SET track_outbox_json=?', JSON.stringify(o));
                await this.ledger.sync();
                return { ok: true };
            }
            case 'reviewMutation': {
                switch (arg.field) {
                    case 'terminal_json':
                        this.ctx.storage.sql.exec("UPDATE operation SET terminal_json=terminal_json||' '");
                        break;
                    case 'phase':
                        this.ctx.storage.sql.exec("UPDATE operation SET phase='completed'");
                        break;
                    case 'versionOnly': {
                        const r = this.ledger.read();
                        this.ctx.storage.sql.exec('UPDATE operation SET state_version=?', String(BigInt(r.state_version) + 1n));
                        break;
                    }
                    case 'outboxPhase': {
                        const r = this.ledger.read(), o = JSON.parse(r.track_outbox_json);
                        o.terminal.phase = 'completed';
                        this.ctx.storage.sql.exec('UPDATE operation SET track_outbox_json=?', JSON.stringify(o));
                        break;
                    }
                    default: throw new Error('review_mutation');
                }
                await this.ledger.sync();
                return { ok: true };
            }
            case 'reviewAckSyncProviderChange': {
                const original = this.ledger.sync.bind(this.ledger), ledger = this.ledger, storage = this.ctx.storage;
                ledger.sync = async () => { ledger.sync = original; await original(); storage.sql.exec("UPDATE operation SET provider_kind='external-macos'"); await original(); };
                return { ok: true };
            }
            case 'reviewAckGuard': {
                const r = this.ledger.read();
                let seen = null, threw = false, cleared = false;
                try {
                    cleared = this.ledger.acknowledge(r.state_version, r.track_outbox_json, current => {
                        seen = current;
                        if (arg.mode === 'throw') {
                            this.ctx.storage.sql.exec("UPDATE operation SET provider_kind='external-macos'");
                            throw new Error('review_atomic_rollback');
                        }
                        if (arg.mode === 'fence') {
                            this.ctx.storage.sql.exec("INSERT OR IGNORE INTO registry_quarantine VALUES(1,?,'0','review_ack_guard')", JSON.stringify(this.identity));
                            return false;
                        }
                        return arg.mode === 'allow';
                    });
                }
                catch (e) {
                    if (e.message !== 'review_atomic_rollback')
                        throw e;
                    threw = true;
                }
                await this.ledger.sync();
                return { seen, threw, cleared };
            }
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
            case 'maxVersion': {
                this.ctx.storage.transactionSync(() => { const r = this.ledger.read(); if (!r)
                    throw new Error('missing_fixture_row'); const outbox = r.track_outbox_json ? JSON.parse(r.track_outbox_json) : null; if (outbox)
                    outbox.stateVersion = '9223372036854775807'; this.ctx.storage.sql.exec("UPDATE operation SET state_version='9223372036854775807',track_outbox_json=?", outbox ? JSON.stringify(outbox) : null); });
                await this.ledger.sync();
                return { ok: true };
            }
            case 'restoreProvider':
                this.ctx.storage.sql.exec("UPDATE operation SET provider_kind='cloudflare-linux'");
                await this.ledger.sync();
                return { ok: true };
            case 'repeatMaxOutbox': {
                const r = this.ledger.read();
                if (!r || r.state_version !== '9223372036854775807' || !r.terminal_json)
                    throw new Error('max_terminal_required');
                this.ctx.storage.sql.exec('UPDATE operation SET track_outbox_json=?', JSON.stringify({ stateVersion: r.state_version, nextDueUs: null, terminal: { phase: JSON.parse(r.terminal_json).status, exactJson: r.terminal_json } }));
                await this.ledger.sync();
                return { ok: true };
            }
            case 'providerMissing':
                this.ctx.storage.sql.exec("UPDATE operation SET provider_kind='unavailable'");
                await this.ledger.sync();
                return { ok: true };
            case 'quarantineOnly':
                this.ctx.storage.sql.exec("UPDATE operation SET quarantined=1");
                await this.ledger.sync();
                return { ok: true };
            case 'outboxMutation':
                this.ctx.storage.sql.exec("UPDATE operation SET track_outbox_json=track_outbox_json||' '");
                await this.ledger.sync();
                return { ok: true };
            case 'providerMismatch':
                this.ctx.storage.sql.exec("UPDATE operation SET provider_kind='external-macos'");
                await this.ledger.sync();
                return { ok: true };
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

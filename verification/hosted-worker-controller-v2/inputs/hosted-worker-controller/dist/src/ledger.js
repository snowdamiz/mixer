import schema from "./schema.sql";
import { immutableBytes, MAX } from "./wire.js";
const columns = ["singleton", "operation_id", "binding", "binding_hash", "request_json", "epoch", "revision", "owner", "expiry_us", "clock_lower", "clock_upper", "clock_qualification", "desired", "phase", "provider_key", "provider_kind", "state_version", "claim_state", "claim_id", "instance_id", "boot_id", "effect_id", "effect_request_json", "effect_kind", "effect_state", "launch_dispatched", "terminal_json", "report_hash", "pending_result_json", "next_due_us", "failures", "quarantined"];
// SQL templates derive only from this compile-time fixed identifier list.
const upsert = `INSERT INTO operation (${columns.join(",")}) VALUES (${columns.map(() => "?").join(",")}) ON CONFLICT(singleton) DO UPDATE SET ${columns.filter(k => k !== "singleton").map(k => `${k}=excluded.${k}`).join(",")}`;
export class Ledger {
    storage;
    constructor(storage) {
        this.storage = storage;
        storage.transactionSync(() => {
            storage.sql.exec(schema);
            const versions = storage.sql.exec("SELECT version FROM controller_schema").toArray();
            if (versions.length !== 1 || versions[0].version !== 1)
                throw new Error("schema_unavailable");
        });
    }
    read() { return this.storage.sql.exec("SELECT * FROM operation WHERE singleton=1").toArray()[0] ?? null; }
    transaction(fn) { return this.storage.transactionSync(() => fn(this.read())); }
    save(r, kind) {
        const n = BigInt(r.state_version) + 1n;
        if (n > MAX)
            throw new Error("ledger_exhausted");
        r.state_version = String(n);
        this.storage.sql.exec(upsert, ...columns.map(k => r[k]));
        this.storage.sql.exec("INSERT INTO audit(sequence,kind,state_version) VALUES(?,?,?) ON CONFLICT(sequence) DO UPDATE SET kind=excluded.kind,state_version=excluded.state_version", Number(n % 32n), kind, r.state_version);
    }
    initial(request, clock, identity) {
        return { singleton: 1, operation_id: request.operation_id, binding: immutableBytes(request), binding_hash: request.immutable_sha256,
            request_json: JSON.stringify(request), epoch: request.guard.epoch, revision: request.guard.revision, owner: request.guard.owner_id, expiry_us: request.guard.expires_at_us,
            clock_lower: String(clock.lowerUs), clock_upper: String(clock.upperUs), clock_qualification: clock.qualificationId,
            desired: "none", phase: "unlaunched", provider_key: identity.key, provider_kind: identity.provider, state_version: "0",
            claim_state: "unissued", claim_id: null, instance_id: null, boot_id: null, effect_id: null, effect_request_json: null, effect_kind: null, effect_state: "none", launch_dispatched: 0,
            terminal_json: null, report_hash: null, pending_result_json: null, next_due_us: null, failures: 0, quarantined: 0 };
    }
    identity(r) { return { provider: r.provider_kind, key: r.provider_key, immutableSha256: r.binding_hash }; }
    async sync() { await this.storage.sync(); }
}

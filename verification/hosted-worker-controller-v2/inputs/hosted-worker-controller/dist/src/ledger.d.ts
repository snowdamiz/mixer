import { Interval } from "./clock.js";
import { ResourceIdentity } from "./provider.js";
import { WireRequest } from "./wire.js";
export interface Row {
    [key: string]: SqlStorageValue;
    singleton: number;
    operation_id: string;
    binding: string;
    binding_hash: string;
    request_json: string;
    epoch: string;
    revision: string;
    owner: string;
    expiry_us: string;
    clock_lower: string;
    clock_upper: string;
    clock_qualification: string;
    desired: "none" | "run" | "stop";
    phase: "unlaunched" | "launch_pending" | "inert" | "claim_consumed" | "running" | "stop_pending" | "completed" | "stopped" | "uncertain" | "quarantined";
    provider_key: string;
    provider_kind: ResourceIdentity["provider"];
    state_version: string;
    claim_state: "unissued" | "consumed" | "revoked";
    claim_id: string | null;
    instance_id: string | null;
    boot_id: string | null;
    effect_id: string | null;
    effect_request_json: string | null;
    effect_kind: "launch" | "inspect" | "stop" | null;
    effect_state: "none" | "prepared" | "dispatched" | "uncertain" | "settled";
    launch_dispatched: number;
    terminal_json: string | null;
    report_hash: string | null;
    pending_result_json: string | null;
    next_due_us: string | null;
    failures: number;
    quarantined: number;
}
export declare class Ledger {
    readonly storage: DurableObjectStorage;
    constructor(storage: DurableObjectStorage);
    read(): Row | null;
    transaction<T>(fn: (r: Row | null) => T): T;
    save(r: Row, kind: string): void;
    initial(request: WireRequest, clock: Interval, identity: ResourceIdentity): Row;
    identity(r: Row): ResourceIdentity;
    sync(): Promise<void>;
}

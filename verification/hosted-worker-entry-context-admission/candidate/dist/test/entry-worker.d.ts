import { DurableObject } from 'cloudflare:workers';
import { MixerWorkerOperation, Env as BaseEnv } from '../src/operation.js';
import { MixerPendingRegistryShard } from '../src/pending-registry.js';
import { MixerPendingAuditCoordinator } from '../src/pending-audit.js';
import { Engine } from '../src/engine.js';
import { RegistryContext } from '../src/registry-context.js';
import { PendingIdentity, RegistrationReceipt, WakeTicket, RegistrationResult } from '../src/public-contract.js';
interface Env extends BaseEnv {
    FOREIGN_OPERATIONS: DurableObjectNamespace;
    REGISTRY_MODE: string;
    OUTER_MODE: string;
    BODY_DELAY: string;
}
export declare class EntryRegistry extends MixerPendingRegistryShard {
    register(i: PendingIdentity): Promise<RegistrationResult>;
}
export { MixerWorkerOperation, MixerPendingAuditCoordinator };
export declare class EntryOperation extends DurableObject<Env> {
    private state;
    constructor(ctx: DurableObjectState, env: Env);
    private get ledger();
    private get engine();
    fetch(request: Request): Promise<Response>;
    enrollExisting(i: PendingIdentity): Promise<"unavailable" | "conflict" | "enrolled" | "missing">;
    enrollAcrossRowChangeFixture(i: PendingIdentity): Promise<{
        status: "unavailable" | "conflict" | "enrolled" | "missing";
        trace: string[];
    }>;
    alarm(): Promise<void>;
    private held;
    protected resourceKind(platform: 'ios' | 'android'): 'cloudflare-linux' | 'external-macos';
    private setting;
    protected createEngine(context: RegistryContext): Engine;
    private count;
    recoverKnown(i: PendingIdentity, p: RegistrationReceipt, t: WakeTicket): Promise<import("../src/public-contract.js").RecoveryDisposition>;
    inspectFixture(): Promise<{
        received: any[];
        row: import("../src/ledger.js").Row | null;
        fenced: boolean;
        counts: Record<string, SqlStorageValue>[];
        recoveries: any[];
        alarm: number | null;
    }>;
    settingFixture(value: string): Promise<void>;
    mutateFixture(kind: string): Promise<void>;
    alarmFixture(): Promise<void>;
    dropAlarmFixture(): Promise<void>;
    claimFixture(value: unknown): Promise<{
        granted: boolean;
        claimId?: string;
    } | {
        granted: boolean;
    }>;
    reportFixture(value: unknown): Promise<"duplicate" | "accepted" | "rejected">;
}
export declare class ForeignOperation extends EntryOperation {
}
declare const _default: {
    fetch(request: Request, env: Env): Promise<Response>;
    scheduled(event: ScheduledController, env: Env): Promise<void>;
};
export default _default;

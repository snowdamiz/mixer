import { DurableObject } from 'cloudflare:workers';
import { MixerPendingRegistryShard } from '../src/pending-registry.js';
import { MixerPendingAuditCoordinator } from '../src/pending-audit.js';
import type { PendingIdentity, RegistrationReceipt, RegistrationResult, TrackInput, TrackAck, ScanCursor, PendingPage, WakeReservation, WakeTicket, RecoveryDisposition } from '../src/public-contract.js';
import { PendingEnv } from '../src/pending-types.js';
interface Setting {
    mode: string;
    milliseconds: number;
}
export declare class TestRegistry extends MixerPendingRegistryShard {
    private held;
    constructor(ctx: DurableObjectState, env: PendingEnv);
    private setting;
    configure(s: Setting): Promise<void>;
    release(): Promise<void>;
    private fault;
    register(i: PendingIdentity): Promise<RegistrationResult>;
    track(a: TrackInput): Promise<TrackAck>;
    scan_due(c: ScanCursor, n: number): Promise<PendingPage>;
    reserve_wake(id: string, v: string, run: string): Promise<WakeReservation>;
    finish_wake(t: WakeTicket, d: RecoveryDisposition): Promise<'accepted' | 'stale' | 'unavailable'>;
    inspect(recordId: string | null): Promise<unknown>;
    counterMax(recordId: string): Promise<void>;
    schemaConflict(): Promise<void>;
}
export declare class TestAudit extends MixerPendingAuditCoordinator {
    inspect(): Promise<unknown>;
    completionFault(mode: string): Promise<void>;
    counterMax(): Promise<void>;
}
export declare class FixtureRecovery extends DurableObject<PendingEnv> {
    private releaseHold;
    constructor(ctx: DurableObjectState, env: PendingEnv);
    configure(mode: string): Promise<void>;
    recoverKnown(i: PendingIdentity, r: RegistrationReceipt, t: WakeTicket): Promise<RecoveryDisposition>;
    release(): Promise<void>;
    inspect(): Promise<unknown>;
}
declare const _default: {
    fetch(req: Request, env: PendingEnv): Promise<Response>;
    scheduled(_event: ScheduledController, env: PendingEnv, _ctx: ExecutionContext): Promise<void>;
};
export default _default;

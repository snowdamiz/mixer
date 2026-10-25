import { DurableObject } from 'cloudflare:workers';
import { MixerPendingRegistryShard } from '../src/pending-registry.js';
import { MixerPendingAuditCoordinator } from '../src/pending-audit.js';
import { PendingEnv } from '../src/pending-types.js';
import type { PendingIdentity, TrackInput, TrackAck, WakeTicket, RecoveryDisposition } from '../src/public-contract.js';
export declare class ReviewRegistry extends MixerPendingRegistryShard {
    private held;
    private hold;
    holdAcknowledgement(value: boolean): Promise<void>;
    track(input: TrackInput): Promise<TrackAck>;
    inspect(id: string): Promise<unknown>;
}
export declare class ReviewAudit extends MixerPendingAuditCoordinator {
    inspect(): Promise<unknown>;
    fault(mode: string): Promise<unknown>;
}
export declare class ReviewRecovery extends DurableObject<PendingEnv> {
    private held;
    private holding;
    constructor(ctx: DurableObjectState, env: PendingEnv);
    configure(holding: boolean): Promise<void>;
    release(): Promise<void>;
    inspect(): Promise<unknown>;
    recoverKnown(i: PendingIdentity, _r: unknown, _t: WakeTicket): Promise<RecoveryDisposition>;
}
declare const _default: {
    fetch(request: Request, env: PendingEnv): Promise<Response>;
    scheduled(_event: ScheduledController, env: PendingEnv): Promise<void>;
};
export default _default;

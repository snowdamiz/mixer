import { DurableObject } from 'cloudflare:workers';
import type { AuditSummary, PendingAuditCoordinator } from './public-contract.js';
import { PendingEnv } from './pending-types.js';
export declare class MixerPendingAuditCoordinator extends DurableObject<PendingEnv> implements PendingAuditCoordinator {
    private c;
    private available;
    private active;
    private unresolvedWake;
    private completionMemory;
    constructor(ctx: DurableObjectState, env: PendingEnv);
    private meta;
    private cursors;
    private archive;
    private checkpoint;
    private completion;
    private completionBytes;
    private storedCompletion;
    private saveCompletion;
    private retain;
    private page;
    runScheduled(): Promise<AuditSummary>;
}

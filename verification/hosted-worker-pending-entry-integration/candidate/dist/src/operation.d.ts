import { DurableObject } from 'cloudflare:workers';
import { Env } from './operation-state.js';
import type { PendingIdentity, RegistrationReceipt, WakeTicket, RecoveryDisposition, KnownOperationRecovery } from './public-contract.js';
export type { Env } from './operation-state.js';
export declare class MixerWorkerOperation extends DurableObject<Env> implements KnownOperationRecovery {
    #private;
    constructor(ctx: DurableObjectState, env: Env);
    fetch(request: Request): Promise<Response>;
    recoverKnown(i: PendingIdentity, p: RegistrationReceipt, t: WakeTicket): Promise<RecoveryDisposition>;
    enrollExisting(i: PendingIdentity): Promise<'enrolled' | 'missing' | 'conflict' | 'unavailable'>;
    alarm(): Promise<void>;
}

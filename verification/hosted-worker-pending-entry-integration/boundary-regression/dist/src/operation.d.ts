import { DurableObject } from 'cloudflare:workers';
import { Engine } from './engine.js';
import { Ledger } from './ledger.js';
import { PrincipalEnv } from './principal.js';
import type { PendingIdentity, RegistrationReceipt, WakeTicket, RecoveryDisposition, KnownOperationRecovery } from './public-contract.js';
import { PendingEnv } from './pending-types.js';
import { RegistryContext } from './registry-context.js';
export interface Env extends PrincipalEnv, PendingEnv {
}
export declare class MixerWorkerOperation extends DurableObject<Env> implements KnownOperationRecovery {
    protected readonly ledger: Ledger;
    protected engine: Engine | null;
    private c;
    private selected;
    private initialization;
    private failed;
    constructor(ctx: DurableObjectState, env: Env);
    protected resourceKind(_platform: 'ios' | 'android'): 'unavailable' | 'cloudflare-linux' | 'external-macos';
    protected createEngine(context: RegistryContext): Engine;
    private checkedTarget;
    private initialize;
    fetch(request: Request): Promise<Response>;
    recoverKnown(value: PendingIdentity, p: RegistrationReceipt, t: WakeTicket): Promise<RecoveryDisposition>;
    enrollExisting(value: PendingIdentity): Promise<'enrolled' | 'missing' | 'conflict' | 'unavailable'>;
    alarm(): Promise<void>;
}

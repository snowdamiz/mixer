import { DurableObject } from 'cloudflare:workers';
import type { PendingIdentity, RegistrationResult, TrackInput, TrackAck, ScanCursor, PendingPage, WakeReservation, WakeTicket, RecoveryDisposition, PendingRegistryShard } from './public-contract.js';
import { PendingEnv } from './pending-types.js';
export declare class MixerPendingRegistryShard extends DurableObject<PendingEnv> implements PendingRegistryShard {
    private c;
    private shard;
    private available;
    constructor(ctx: DurableObjectState, env: PendingEnv);
    private row;
    private receipt;
    private matches;
    private bounded;
    register(value: PendingIdentity): Promise<RegistrationResult>;
    track(input: TrackInput): Promise<TrackAck>;
    scan_due(cursor: ScanCursor, limit: number): Promise<PendingPage>;
    reserve_wake(recordId: string, expectedTrackVersion: string, runId: string): Promise<WakeReservation>;
    finish_wake(value: WakeTicket, result: RecoveryDisposition): Promise<'accepted' | 'stale' | 'unavailable'>;
}
export declare class RegistryPort {
    private env;
    constructor(env: PendingEnv);
    register(i: PendingIdentity): Promise<RegistrationResult>;
    track(a: TrackInput): Promise<TrackAck>;
}

import { DurableObject } from 'cloudflare:workers';
import type { PendingIdentity, TrackInput, TrackAck } from '../src/vendor/public-contract.js';
import { MixerPendingRegistryShard } from '../src/vendor/pending-registry.js';
import { PendingEnv } from '../src/vendor/pending-types.js';
interface Env extends PendingEnv {
    FIXTURE_IDENTITY: string;
}
export declare class TestRegistry extends MixerPendingRegistryShard {
    private releaseAck;
    private setting;
    private set;
    constructor(ctx: DurableObjectState, env: PendingEnv);
    register(i: PendingIdentity): Promise<import("../src/vendor/public-contract.js").RegistrationResult>;
    track(a: TrackInput): Promise<TrackAck>;
    fixture(action: string, arg: Record<string, unknown>): Promise<{
        ok: boolean;
        settings?: undefined;
        records?: undefined;
    } | {
        settings: {
            mode: string;
            skip: number;
            blocked: boolean;
        };
        records: Record<string, SqlStorageValue>[];
        ok?: undefined;
    }>;
}
export declare class TestOperation extends DurableObject<Env> {
    private ledger;
    private engine;
    private store;
    private hooks;
    private provider;
    private identity;
    constructor(ctx: DurableObjectState, env: Env);
    fixture(action: string, arg: Record<string, unknown>): Promise<unknown>;
    alarm(): Promise<void>;
}
declare const _default: {
    fetch(request: Request, env: Env): Promise<Response>;
};
export default _default;

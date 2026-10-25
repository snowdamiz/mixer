import { DurableObject } from "cloudflare:workers";
import { PrincipalEnv } from "../src/principal.js";
import { PendingEnv } from '../src/pending-types.js';
import { MixerPendingRegistryShard } from '../src/pending-registry.js';
import { MixerPendingAuditCoordinator } from '../src/pending-audit.js';
export { MixerPendingRegistryShard, MixerPendingAuditCoordinator };
interface Env extends PrincipalEnv, PendingEnv {
    FIXTURE_IDENTITY: string;
}
export declare class TestOperation extends DurableObject<Env> {
    private ledger;
    private engine;
    private selected;
    private store;
    private hooks;
    private provider;
    constructor(ctx: DurableObjectState, env: Env);
    private derive;
    private select;
    private registry;
    fetch(request: Request): Promise<Response>;
    alarm(): Promise<void>;
}
declare const _default: {
    fetch(request: Request, env: Env): Promise<Response>;
};
export default _default;

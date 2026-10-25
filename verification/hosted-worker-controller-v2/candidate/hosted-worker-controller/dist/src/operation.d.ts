import { DurableObject } from "cloudflare:workers";
import { PrincipalEnv } from "./principal.js";
export interface Env extends PrincipalEnv {
    OPERATIONS: DurableObjectNamespace;
}
export declare class MixerWorkerOperation extends DurableObject<Env> {
    private engine;
    constructor(ctx: DurableObjectState, env: Env);
    fetch(request: Request): Promise<Response>;
    alarm(): Promise<void>;
}

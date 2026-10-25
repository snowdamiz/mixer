import { DurableObject } from "cloudflare:workers";
import { PrincipalEnv } from "../src/principal.js";
interface Env extends PrincipalEnv {
    OPERATIONS: DurableObjectNamespace;
}
export declare class TestOperation extends DurableObject<Env> {
    private ledger;
    private engine;
    private store;
    private hooks;
    private provider;
    constructor(ctx: DurableObjectState, env: Env);
    fetch(request: Request): Promise<Response>;
    alarm(): Promise<void>;
}
declare const _default: {
    fetch(request: Request, env: Env): Promise<Response>;
};
export default _default;

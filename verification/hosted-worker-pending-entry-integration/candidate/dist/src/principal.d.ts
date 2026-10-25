import { WireRequest } from "./wire.js";
export interface Principal {
    environment_id: string;
    pool_id: string;
    controller_id: string;
    platforms: ("ios" | "android")[];
    token_sha256: string;
}
export interface PrincipalEnv {
    MIXER_PRINCIPAL?: string;
    MIXER_POOL_TOKEN_SHA256?: string;
}
export declare function principal(env: PrincipalEnv): Principal | null;
export declare function authenticate(request: Request, p: Principal): Promise<boolean>;
export declare function body(request: Request): Promise<Uint8Array>;
export declare function ingress(request: Request, env: PrincipalEnv): Promise<{
    r: WireRequest;
    bytes: Uint8Array;
} | Response>;
export declare function operationKey(r: WireRequest): Promise<string>;

import type { PendingIdentity, RegistrationReceipt, PendingRegistry, RegistrationResult } from './public-contract.js';
import { PendingConfig, PendingEnv, config, identity, receipt, same } from './pending-types.js';
import { WireRequest } from './wire.js';
export interface Budget {
    check(): void;
    remaining(): number;
}
export declare function budget(signal?: AbortSignal): Budget;
export declare function pendingIdentity(r: WireRequest, c: PendingConfig, b?: Budget): Promise<{
    value: PendingIdentity;
    bytes: string;
    digest: string;
    shard: number;
}>;
export declare function registration(env: PendingEnv, c: PendingConfig, i: PendingIdentity, b?: Budget): Promise<RegistrationReceipt>;
export declare function checkedReceipt(v: RegistrationResult, c: PendingConfig, digest: string, shard: number): RegistrationReceipt;
export declare function registryPort(env: PendingEnv, c: PendingConfig, i: PendingIdentity): PendingRegistry;
export { config, identity, receipt, same };

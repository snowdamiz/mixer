import type { PendingIdentity, RegistrationReceipt, PendingRegistry } from './public-contract.js';
import { identityBytes, same } from './pending-types.js';
import type { Row } from './ledger.js';
import { WireRequest } from './wire.js';
export interface RegistryContext {
    identity: PendingIdentity;
    registry: PendingRegistry;
}
export declare const unavailableRegistry: PendingRegistry;
export declare function checkedContext(context: RegistryContext | undefined, value: PendingIdentity, p: RegistrationReceipt): Promise<{
    identity: PendingIdentity;
    receipt: RegistrationReceipt;
    bytes: string;
}>;
export declare function matchesRequest(i: PendingIdentity, r: WireRequest): boolean;
export declare function matchesRow(i: PendingIdentity, r: Row): boolean;
export declare function retained(context: RegistryContext | undefined, r: Row): boolean;
export { identityBytes, same };

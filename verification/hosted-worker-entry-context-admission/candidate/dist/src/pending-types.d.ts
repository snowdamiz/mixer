import type { PendingIdentity, RegistrationReceipt, Projection, RecoveryDisposition, WakeTicket } from './public-contract.js';
export declare const MAX = 9223372036854775807n;
export declare const encoder: TextEncoder;
export interface PendingConfig {
    generation: string;
    operationsNamespace: string;
    registryNamespace: string;
}
export interface PendingEnv {
    MIXER_PENDING_CONFIG?: string;
    PENDING_REGISTRY: DurableObjectNamespace;
    PENDING_AUDIT: DurableObjectNamespace;
    OPERATIONS: DurableObjectNamespace;
}
export declare function invalid(): never;
export declare function exact(v: unknown, keys: readonly string[]): Record<string, unknown>;
export declare function hex(v: unknown, bits?: number): string;
export declare function decimal(v: unknown): string;
export declare function integer(v: unknown, min: number, max: number): number;
export declare function principal(v: unknown): string;
export declare function config(env: PendingEnv): PendingConfig;
export declare function registryName(c: PendingConfig, index: number): string;
export declare function auditName(c: PendingConfig): string;
export declare const randomId: () => string;
export declare const sha: (s: string) => Promise<string>;
export declare function identityBytes(i: PendingIdentity): string;
export declare function identityFromBytes(s: string): PendingIdentity;
export declare function identity(v: unknown, c: PendingConfig): Promise<{
    value: PendingIdentity;
    bytes: string;
    digest: string;
    shard: number;
}>;
export declare function receipt(v: unknown, c: PendingConfig): RegistrationReceipt;
export declare function projection(v: unknown): Projection;
export declare function ticket(v: unknown, c: PendingConfig): WakeTicket;
export declare function disposition(v: unknown): RecoveryDisposition;
export declare function same(a: unknown, b: unknown): boolean;
export declare function next(v: string): string;
export declare function wait<T>(promise: Promise<T>, ms: number): Promise<{
    ok: true;
    value: T;
} | {
    ok: false;
}>;

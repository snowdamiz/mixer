export declare const MAX = 9223372036854775807n;
export declare const encoder: TextEncoder;
export declare class InvalidInput extends Error {
    constructor();
}
export declare function invalid(): never;
export declare function exact(v: unknown, keys: readonly string[]): asserts v is Record<string, unknown>;
export declare function decimal(v: unknown, min?: bigint, max?: bigint): string;
export declare function text(v: unknown, max?: number): string;
export declare function hex(v: unknown, length?: number): string;
export interface Scope {
    organization_id: string;
    project_id: string;
    application_id: string;
    build_id: string;
    platform: "ios" | "android";
}
export interface Ref extends Scope {
    attempt: number;
    fence: string;
}
export interface Spec extends Scope {
    source: {
        kind: "revision" | "upload";
        sha256: string;
        reference: string;
    };
    toolchain_lock_sha256: string;
    build_definition_sha256: string;
}
export interface Guard {
    record_id: string;
    revision: string;
    owner_id: string;
    epoch: string;
    expires_at_us: string;
}
export interface WireRequest {
    version: 1;
    environment_id: string;
    pool_id: string;
    controller_id: string;
    request_id: string;
    command: "query" | "ensure_started" | "stop";
    operation_id: string;
    immutable_sha256: string;
    ref: Ref;
    spec: Spec;
    deadline_ms: string;
    guard: Guard;
}
export type Observation = {
    status: "absent" | "running";
} | {
    status: "error";
    code: "stale" | "unavailable" | "uncertain";
} | {
    status: "stopped";
    diagnostic_sha256: string;
} | {
    status: "completed";
    result: BuildResult;
};
export type BuildResult = {
    outcome: "succeeded";
    artifacts: {
        kind: string;
        sha256: string;
        size_bytes: string;
    }[];
} | {
    outcome: "failed";
    class: string;
    code: string;
    diagnostic_sha256: string;
};
export declare function parseJSON(raw: Uint8Array, limit?: number): unknown;
export declare function sha(s: string | Uint8Array): Promise<string>;
export declare function immutableBytes(r: WireRequest): string;
export declare function operationBytes(r: WireRequest): string;
export declare function decode(raw: Uint8Array): Promise<WireRequest>;
export declare function reply(r: WireRequest, observation: Observation): Response;
export declare const errorResponse: (status: number) => Response;
export declare function result(v: unknown): BuildResult;

import { Clock } from "./clock.js";
import { Ledger } from "./ledger.js";
import { ObjectVerifier, Provider, ResourceIdentity } from "./provider.js";
import { BuildResult, Observation, WireRequest } from "./wire.js";
import type { PendingIdentity, RegistrationReceipt, WakeTicket, RecoveryDisposition } from "./vendor/public-contract.js";
import { RegistryContext } from "./registry-context.js";
export interface Hooks {
    point(name: string): Promise<void>;
}
export interface RunnerClaim {
    identity: ResourceIdentity;
    instanceId: string;
    bootId: string;
    immutableSha256: string;
}
export interface RunnerReport extends RunnerClaim {
    operationId: string;
    claimId: string;
    result: BuildResult;
    attestationSha256: string;
}
export declare class Engine {
    readonly ledger: Ledger;
    readonly clock: Clock;
    readonly provider: Provider;
    readonly verifier: ObjectVerifier;
    private hooks;
    private pending?;
    private inFlight;
    constructor(ledger: Ledger, clock: Clock, provider: Provider, verifier: ObjectVerifier, hooks?: Hooks, pending?: RegistryContext | undefined);
    private registry;
    private fence;
    private checked;
    private trustedKind;
    private providerMatches;
    private fenceIdentity;
    private providerFenceInTransaction;
    private reportBinding;
    private unenrolledMigrationShape;
    private terminalProjection;
    private terminalConsistent;
    private trackSnapshotValid;
    flushTrack(): Promise<boolean>;
    commandRegistered(request: WireRequest, resource: ResourceIdentity, identity: PendingIdentity, receipt: RegistrationReceipt): Promise<Observation>;
    private sample;
    private acceptTime;
    private live;
    private stop;
    private due;
    private terminal;
    private current;
    command(request: WireRequest, identity: ResourceIdentity): Promise<Observation>;
    private commandAdmitted;
    private prepare;
    private sameGuard;
    private finalCheck;
    private observation;
    private accept;
    reconcile(): Promise<void>;
    arm(): Promise<void>;
    alarm(): Promise<void>;
    recover(): Promise<void>;
    private validClaim;
    claim(claim: RunnerClaim): Promise<{
        granted: boolean;
        claimId?: string;
    }>;
    report(report: RunnerReport): Promise<"accepted" | "duplicate" | "rejected">;
    recoverKnown(identity: PendingIdentity, receipt: RegistrationReceipt, value: WakeTicket): Promise<RecoveryDisposition>;
    enrollExisting(identity: PendingIdentity): Promise<'enrolled' | 'missing' | 'conflict' | 'unavailable'>;
    quarantine(): Promise<void>;
}

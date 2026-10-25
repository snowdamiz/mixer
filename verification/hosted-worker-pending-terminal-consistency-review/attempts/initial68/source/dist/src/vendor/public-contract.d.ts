export type Decimal = string;
export type Hex64 = string;
export type Hex128 = string;
export interface PendingIdentity {
    namespaceGeneration: Hex64;
    environmentId: string;
    poolId: string;
    controllerId: string;
    platform: "ios" | "android";
    operationKey: Hex64;
    operationId: Hex64;
    immutableSha256: Hex64;
}
export interface RegistrationReceipt {
    identityDigest: Hex64;
    namespaceGeneration: Hex64;
    recordId: Hex128;
    shard: number;
    allocationIndex: number;
}
export type RegistrationResult = {
    status: "registered" | "duplicate";
    receipt: RegistrationReceipt;
} | {
    status: "unavailable" | "capacity" | "conflict";
};
export interface PendingProjection {
    kind: "pending";
    nextDueUs: Decimal | null;
}
export interface TerminalProjection {
    kind: "terminal";
    nextDueUs: null;
    phase: "completed" | "stopped";
    evidenceSha256: Hex64;
}
export type Projection = PendingProjection | TerminalProjection;
export interface TrackInput {
    receipt: RegistrationReceipt;
    stateVersion: Decimal;
    projection: Projection;
}
export type TrackAck = {
    status: "accepted" | "duplicate";
    stateVersion: Decimal;
} | {
    status: "stale";
    stateVersion: Decimal;
} | {
    status: "unavailable" | "conflict";
};
export interface ScanCursor {
    afterAllocationIndex: number;
}
export interface ScannedPending {
    identity: PendingIdentity;
    receipt: RegistrationReceipt;
    stateVersion: Decimal;
    needsAttention: boolean;
    skipVisits: number;
}
export interface PendingPage {
    records: readonly ScannedPending[];
    wrapped: boolean;
}
export interface WakeTicket {
    runId: Decimal;
    wakeId: Hex128;
    receipt: RegistrationReceipt;
    trackedVersion: Decimal;
    attemptSequence: Decimal;
}
export type WakeReservation = {
    status: "reserved";
    ticket: WakeTicket;
} | {
    status: "duplicate" | "stale" | "backoff" | "terminal" | "unavailable";
};
export type RecoveryDisposition = {
    status: "pending";
    stateVersion: Decimal;
} | {
    status: "terminal";
    stateVersion: Decimal;
    projection: TerminalProjection;
} | {
    status: "empty_orphan" | "quarantined" | "busy" | "unavailable" | "conflict";
};
export interface PendingRegistry {
    register(identity: PendingIdentity): Promise<RegistrationResult>;
    track(input: TrackInput): Promise<TrackAck>;
}
export interface PendingRegistryShard extends PendingRegistry {
    scan_due(cursor: ScanCursor, limit: number): Promise<PendingPage>;
    reserve_wake(recordId: Hex128, expectedTrackVersion: Decimal, runId: Decimal): Promise<WakeReservation>;
    finish_wake(ticket: WakeTicket, disposition: RecoveryDisposition): Promise<"accepted" | "stale" | "unavailable">;
}
export interface KnownOperationRecovery {
    recoverKnown(identity: PendingIdentity, receipt: RegistrationReceipt, ticket: WakeTicket): Promise<RecoveryDisposition>;
    enrollExisting(identity: PendingIdentity): Promise<"enrolled" | "missing" | "conflict" | "unavailable">;
}
export interface AuditSummary {
    status: "finished" | "bounded" | "busy" | "unavailable";
    runId: Decimal | null;
    pages: number;
    examined: number;
    wakesStarted: number;
    needsAttention: boolean;
}
export interface PendingAuditCoordinator {
    runScheduled(): Promise<AuditSummary>;
}
export interface PersistedRegistryBarrier {
    registration: RegistrationReceipt;
    acknowledgedVersion: Decimal;
    effectBarrierVersion: Decimal | null;
    claimBarrierVersion: Decimal | null;
}
export interface CoalescedTrackOutbox {
    stateVersion: Decimal;
    nextDueUs: Decimal | null;
    terminal: null | {
        phase: "completed" | "stopped";
        exactJson: string;
    };
}

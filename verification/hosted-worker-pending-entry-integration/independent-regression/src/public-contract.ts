// Type-only proposed interface. No production implementation or test override.
export type Decimal = string; // canonical 0..9223372036854775807, validated at runtime
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
  shard: number; // internally recomputed 0..15; never caller-selected routing
  allocationIndex: number; // 1..4096, permanent; no reuse
}
export type RegistrationResult =
  | { status: "registered" | "duplicate"; receipt: RegistrationReceipt }
  | { status: "unavailable" | "capacity" | "conflict" };
export interface PendingProjection {
  kind: "pending";
  nextDueUs: Decimal | null; // exact hint only
}
export interface TerminalProjection {
  kind: "terminal";
  nextDueUs: null;
  phase: "completed" | "stopped";
  evidenceSha256: Hex64; // hash of exact durable local terminal JSON, no result body
}
export type Projection = PendingProjection | TerminalProjection;
export interface TrackInput {
  receipt: RegistrationReceipt;
  stateVersion: Decimal;
  projection: Projection;
}
export type TrackAck =
  | { status: "accepted" | "duplicate"; stateVersion: Decimal }
  | { status: "stale"; stateVersion: Decimal }
  | { status: "unavailable" | "conflict" };
export interface ScanCursor {
  afterAllocationIndex: number; // 0..4096, bounded internal index
}
export interface ScannedPending {
  identity: PendingIdentity;
  receipt: RegistrationReceipt;
  stateVersion: Decimal;
  needsAttention: boolean;
  skipVisits: number; // 0..7, never hides the row from scans
}
export interface PendingPage {
  records: readonly ScannedPending[]; // <=32 and encoded page <=65536 bytes
  wrapped: boolean;
}
export interface WakeTicket {
  runId: Decimal;
  wakeId: Hex128;
  receipt: RegistrationReceipt;
  trackedVersion: Decimal;
  attemptSequence: Decimal;
}
export type WakeReservation =
  | { status: "reserved"; ticket: WakeTicket }
  | { status: "duplicate" | "stale" | "backoff" | "terminal" | "unavailable" };
export type RecoveryDisposition =
  | { status: "pending"; stateVersion: Decimal }
  | { status: "terminal"; stateVersion: Decimal; projection: TerminalProjection }
  | { status: "empty_orphan" | "quarantined" | "busy" | "unavailable" | "conflict" };
export interface PendingRegistry {
  register(identity: PendingIdentity): Promise<RegistrationResult>;
  track(input: TrackInput): Promise<TrackAck>;
}
export interface PendingRegistryShard extends PendingRegistry {
  // Read-only: never decrements backoff, reserves delivery or advances cursor.
  scan_due(cursor: ScanCursor, limit: number): Promise<PendingPage>;
  // Sole skipVisits decrement; duplicate (runId,recordId) cannot decrement twice.
  reserve_wake(recordId: Hex128, expectedTrackVersion: Decimal, runId: Decimal): Promise<WakeReservation>;
  finish_wake(ticket: WakeTicket, disposition: RecoveryDisposition): Promise<"accepted" | "stale" | "unavailable">;
}
export interface KnownOperationRecovery {
  recoverKnown(identity: PendingIdentity, receipt: RegistrationReceipt, ticket: WakeTicket): Promise<RecoveryDisposition>;
  // Maintenance can enroll only an already existing exact matching row.
  // It never clears migration/restore/clock quarantine or constructs authority.
  enrollExisting(identity: PendingIdentity): Promise<"enrolled" | "missing" | "conflict" | "unavailable">;
}
export interface AuditSummary {
  status: "finished" | "bounded" | "busy" | "unavailable";
  runId: Decimal | null;
  pages: number; // <=16
  examined: number; // <=512
  wakesStarted: number; // <=8, including timeouts/failures
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
  // Local bytes only; hash outside SQL transaction, never send bytes to registry.
  terminal: null | { phase: "completed" | "stopped"; exactJson: string };
}

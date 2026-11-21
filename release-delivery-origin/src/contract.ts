export const targetFields = ["organization", "project", "app", "environment", "platform", "runtime", "channel"];
const scopeFields = ["organization", "project", "app", "environment", "platform"];
export const tenantFields = ["organization", "project"];
export const assignmentLimit = 65_536;
export const artifactLimit = 6 * 1024 * 1024;
export const snapshotLimit = 16_384;
export const maxLeaseMs = 300_000;

export interface Target {
  organization: string;
  project: string;
  app: string;
  environment: string;
  platform: "ios" | "android";
  runtime: string;
  channel: string;
}

export interface Artifact {
  manifest_sha256: string;
  envelope_sha256: string;
}

export interface Head {
  sequence: string;
  assignment_sha256: string;
  artifact_sha256: string;
  rollout_basis_points: number;
  enabled: boolean;
}

export interface Snapshot {
  version: 1;
  target: Target;
  revision: string;
  issued_at_ms: number;
  expires_at_ms: number;
  head: Head;
  artifacts: Artifact[];
}

export const encoder = new TextEncoder();
export const decoder = new TextDecoder("utf-8", {fatal: true, ignoreBOM: true});

export function exact(value: unknown, fields: readonly string[]): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    && Object.keys(value).length === fields.length && fields.every(field => Object.hasOwn(value, field));
}

export function id(value: unknown): value is string {
  return typeof value === "string" && value.length >= 1 && value.length <= 128 && !/[^a-zA-Z0-9_.-]/.test(value);
}

export function digest(value: unknown): value is string {
  return typeof value === "string" && value.length === 64 && !/[^a-f0-9]/.test(value);
}

function uint64(value: unknown): value is string {
  return typeof value === "string" && value.length >= 1 && value.length <= 20
    && value[0] !== "0" && !/[^0-9]/.test(value) && BigInt(value) <= 18_446_744_073_709_551_615n;
}

function timestamp(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0;
}

function rollout(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 10_000;
}

export function isTarget(value: unknown): value is Target {
  return exact(value, targetFields)
    && id(value.organization) && id(value.project) && id(value.app) && id(value.environment)
    && (value.platform === "ios" || value.platform === "android") && digest(value.runtime) && id(value.channel);
}

function matchingScope(value: unknown, target: Target): boolean {
  return exact(value, scopeFields) && value.organization === target.organization && value.project === target.project
    && value.app === target.app && value.environment === target.environment && value.platform === target.platform;
}

export function prefix(target: Target): string {
  return ["v1", target.organization, target.project, target.app, target.environment,
    target.platform, target.runtime, target.channel].join(":");
}

function isArtifact(value: unknown): value is Artifact {
  return exact(value, ["manifest_sha256", "envelope_sha256"]) && digest(value.manifest_sha256)
    && digest(value.envelope_sha256);
}

function isHead(value: unknown): value is Head {
  return exact(value, ["sequence", "assignment_sha256", "artifact_sha256", "rollout_basis_points", "enabled"])
    && uint64(value.sequence) && digest(value.assignment_sha256) && digest(value.artifact_sha256)
    && rollout(value.rollout_basis_points) && typeof value.enabled === "boolean";
}

export function offers(head: Head): boolean {
  return head.enabled && head.rollout_basis_points > 0;
}

export function isSnapshot(value: unknown): value is Snapshot {
  if (!exact(value, ["version", "target", "revision", "issued_at_ms", "expires_at_ms", "head", "artifacts"])
    || value.version !== 1 || !isTarget(value.target) || !uint64(value.revision) || !isHead(value.head)
    || !timestamp(value.issued_at_ms) || !timestamp(value.expires_at_ms)
    || value.expires_at_ms <= value.issued_at_ms || value.expires_at_ms - value.issued_at_ms > maxLeaseMs
    || !Array.isArray(value.artifacts) || value.artifacts.length > 32 || !value.artifacts.every(isArtifact)) return false;

  const digests = new Set(value.artifacts.map(artifact => artifact.manifest_sha256));
  return digests.size === value.artifacts.length && (!offers(value.head) || digests.has(value.head.artifact_sha256));
}

export function fresh(snapshot: Snapshot, now: number): boolean {
  return snapshot.issued_at_ms <= now && now < snapshot.expires_at_ms;
}

export async function sha256(bytes: ArrayBuffer): Promise<string> {
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return Array.from(hash, byte => byte.toString(16).padStart(2, "0")).join("");
}

function signature(value: unknown): boolean {
  if (typeof value !== "string" || value.length !== 88) return false;
  const decoded = atob(value);
  return decoded.length === 64 && btoa(decoded) === value;
}

export function decodeAssignment(
  bytes: ArrayBuffer, target: Target,
): Pick<Head, "sequence" | "artifact_sha256" | "rollout_basis_points"> | null {
  // Preserve uint64 fields using their original numeric lexemes.
  const envelope: unknown = JSON.parse(decoder.decode(bytes), (key, value: unknown, context?: {source?: string}) => {
    if (key !== "sequence" && key !== "created_at_unix") return value;
    return typeof value === "number" ? context?.source : undefined;
  });
  if (!exact(envelope, ["assignment", "signature"]) || !signature(envelope.signature)) return null;
  const assignment = envelope.assignment;
  if (!exact(assignment, ["schema", "scope", "channel", "cohort", "rollout_basis_points", "sequence",
    "release_id", "artifact_sha256", "runtime", "key_id", "created_at_unix"])
    || assignment.schema !== 3 || assignment.cohort !== "sha256-v1"
    || !matchingScope(assignment.scope, target) || assignment.channel !== target.channel
    || assignment.runtime !== target.runtime || !uint64(assignment.sequence) || !uint64(assignment.created_at_unix)
    || !id(assignment.release_id) || !id(assignment.key_id) || !digest(assignment.artifact_sha256)
    || !rollout(assignment.rollout_basis_points)) return null;
  return {sequence: assignment.sequence, artifact_sha256: assignment.artifact_sha256,
    rollout_basis_points: assignment.rollout_basis_points};
}

export function matchesArtifact(bytes: ArrayBuffer, target: Target): boolean {
  const envelope: unknown = JSON.parse(decoder.decode(bytes));
  if (!exact(envelope, ["signed_manifest", "payload"]) || typeof envelope.payload !== "string"
    || !exact(envelope.signed_manifest, ["manifest", "signature"]) || !signature(envelope.signed_manifest.signature)) return false;
  const manifest = envelope.signed_manifest.manifest;
  return exact(manifest, ["schema", "scope", "release_id", "source_commit", "provenance_id", "runtime", "protocol",
    "guest_abi", "ui_schema", "capability_hashes", "capability_grants", "state_min", "state_max", "payload_sha256",
    "compressed_bytes", "expanded_bytes", "compression", "asset_hashes", "source_map_sha256", "limits", "key_id", "created_at_unix"])
    && manifest.schema === 3 && manifest.protocol === 3 && manifest.guest_abi === 2 && manifest.ui_schema === 1
    && matchingScope(manifest.scope, target) && manifest.runtime === target.runtime;
}

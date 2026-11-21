import {
  type Artifact, type Snapshot, type Target, artifactLimit, assignmentLimit, encoder,
  isSnapshot, maxLeaseMs, prefix, sha256,
} from "./contract.js";
import {current} from "./storage.js";
import {applySnapshot, stageArtifact, stageAssignment} from "./writer.js";

type PointerResult = Awaited<ReturnType<typeof applySnapshot>>;
export type PublicationResult = PointerResult | "unavailable" | "stale" | "indeterminate";

type Authority = Pick<Snapshot, "target" | "head" | "artifacts"> & {
  validUntilUnix: bigint | null;
};

interface Projection extends Authority {
  assignmentBytes: ArrayBuffer;
}

export interface ReleaseProjectionSource {
  read(target: Target): Promise<Projection | null>;
  readArtifact(authority: Authority, artifact: Artifact): Promise<ArrayBuffer>;

  // Compare the exact authority again and keep it current until publish settles.
  // The permit checks the current callback deadline just before a pointer write.
  // An authority or transport failure after dispatch requires reconciliation.
  withCurrent(
    authority: Authority, publish: (mayWrite: () => boolean) => Promise<PublicationResult>,
  ): Promise<PublicationResult>;
}

interface Publication {
  bucket: Parameters<typeof applySnapshot>[0];
  target: Target;
  source: ReleaseProjectionSource;
  leaseMs: number;
}

function snapshot(authority: Authority, revision: string, leaseMs: number): Snapshot | null {
  const now = Date.now();
  const requestedExpiry = now + leaseMs;
  const deadline = authority.validUntilUnix === null ? null : authority.validUntilUnix * 1000n;
  const expiry = deadline !== null && deadline < BigInt(requestedExpiry) ? Number(deadline) : requestedExpiry;
  if (expiry <= now) return null;
  return {
    version: 1,
    target: authority.target,
    revision,
    issued_at_ms: now,
    expires_at_ms: expiry,
    head: authority.head,
    artifacts: authority.artifacts,
  };
}

export async function publishProjection({bucket, target, source, leaseMs}: Publication): Promise<PublicationResult> {
  if (!Number.isSafeInteger(leaseMs) || leaseMs < 1 || leaseMs > maxLeaseMs) {
    throw new Error("publication_lease");
  }
  const projection = await source.read(target);
  if (!projection) return "unavailable";

  const authority = {
    target: {...projection.target},
    head: {...projection.head},
    artifacts: projection.artifacts.map(artifact => ({...artifact})),
    validUntilUnix: projection.validUntilUnix,
  };
  const initial = snapshot(authority, "1", leaseMs);
  if (!initial) return "expired";
  if (!isSnapshot(initial) || prefix(authority.target) !== prefix(target)) {
    throw new Error("publication_projection");
  }
  const assignment = projection.assignmentBytes.slice(0);
  if (assignment.byteLength > assignmentLimit || await sha256(assignment) !== authority.head.assignment_sha256) {
    throw new Error("publication_assignment");
  }
  await stageAssignment(bucket, target, assignment);
  for (const artifact of authority.artifacts) {
    const bytes = (await source.readArtifact(authority, artifact)).slice(0);
    if (bytes.byteLength > artifactLimit || await sha256(bytes) !== artifact.envelope_sha256) {
      throw new Error("publication_artifact");
    }
    await stageArtifact(bucket, target, artifact.manifest_sha256, bytes);
  }

  let attempted = false;
  return source.withCurrent(authority, async mayWrite => {
    if (attempted) throw new Error("publication_repeated");
    attempted = true;
    if (!mayWrite()) return "expired";
    const prior = await current(bucket, target);
    if (prior && BigInt(authority.head.sequence) < BigInt(prior.snapshot.head.sequence)) return "stale";
    const revision = (BigInt(prior?.snapshot.revision ?? "0") + 1n).toString();
    const next = snapshot(authority, revision, leaseMs);
    if (!next) return "expired";
    const bytes = Uint8Array.from(encoder.encode(JSON.stringify(next)));
    return applySnapshot(bucket, target, bytes.buffer, mayWrite);
  });
}

import {
  type Artifact, type Target, artifactLimit, assignmentLimit, decodeAssignment, decoder, digest, fresh, isSnapshot, isTarget,
  matchesArtifact, prefix, sha256, snapshotLimit,
} from "./contract.js";
import {type Reader, artifactKey, assignmentKey, checked, current, manifestKey, pointerKey, readyArtifact, readAssignment} from "./storage.js";

type Writer = Reader & Pick<R2Bucket, "put">;

async function putImmutable(bucket: Writer, key: string, bytes: ArrayBuffer, hash: string): Promise<void> {
  const object = await bucket.put(key, bytes, {sha256: hash, onlyIf: {etagDoesNotMatch: "*"}});
  if (!object) await checked(bucket, key, hash, bytes.byteLength);
}

// The authorized exporter is responsible for strict v3 admission, including the
// canonical manifest digest and signatures, before it calls this storage API.
export async function stageArtifact(bucket: Writer, target: Target, manifestHash: string, bytes: ArrayBuffer): Promise<Artifact> {
  if (!isTarget(target) || !digest(manifestHash) || bytes.byteLength < 1 || bytes.byteLength > artifactLimit
    || !matchesArtifact(bytes, target)) throw new Error("artifact_input");
  const artifact = {manifest_sha256: manifestHash, envelope_sha256: await sha256(bytes)};
  await putImmutable(bucket, artifactKey(target, artifact), bytes, artifact.envelope_sha256);
  return artifact;
}

export async function stageAssignment(bucket: Writer, target: Target, bytes: ArrayBuffer): Promise<string> {
  if (!isTarget(target) || bytes.byteLength < 1 || bytes.byteLength > assignmentLimit
    || !decodeAssignment(bytes, target)) throw new Error("assignment_input");
  const hash = await sha256(bytes);
  await putImmutable(bucket, assignmentKey(target, hash), bytes, hash);
  return hash;
}

export async function applySnapshot(
  bucket: Writer, enrolled: Target, manifest: ArrayBuffer, mayWrite: () => boolean = () => true,
): Promise<"applied" | "unchanged" | "retry" | "expired"> {
  if (!isTarget(enrolled) || manifest.byteLength < 1 || manifest.byteLength > snapshotLimit) throw new Error("snapshot_size");
  const bytes = manifest.slice(0);
  const input: unknown = JSON.parse(decoder.decode(bytes));
  if (!isSnapshot(input) || prefix(input.target) !== prefix(enrolled) || !fresh(input, Date.now())) {
    throw new Error("snapshot_input");
  }
  const hash = await sha256(bytes);
  const previous = await current(bucket, enrolled);
  if (previous?.hash === hash) return "unchanged";

  if (previous) {
    const old = previous.snapshot;
    const sameSequence = input.head.sequence === old.head.sequence;
    if (BigInt(input.revision) <= BigInt(old.revision) || input.issued_at_ms < old.issued_at_ms
      || BigInt(input.head.sequence) < BigInt(old.head.sequence)
      || (sameSequence && (input.head.assignment_sha256 !== old.head.assignment_sha256
        || (input.head.enabled && !old.head.enabled)))) throw new Error("snapshot_stale");
  }

  const assignment = decodeAssignment(await readAssignment(bucket, input), enrolled);
  if (!assignment || assignment.sequence !== input.head.sequence || assignment.artifact_sha256 !== input.head.artifact_sha256
    || assignment.rollout_basis_points !== input.head.rollout_basis_points) throw new Error("snapshot_assignment");
  const artifacts = await Promise.all(input.artifacts.map(artifact => readyArtifact(bucket, enrolled, artifact)));
  if (!artifacts.every(Boolean)) throw new Error("snapshot_artifact");
  await putImmutable(bucket, manifestKey(enrolled, hash), bytes, hash);

  if (!fresh(input, Date.now())) throw new Error("snapshot_expired");
  if (!mayWrite()) return "expired";
  const condition = previous ? {etagMatches: previous.etag} : {etagDoesNotMatch: "*"};
  return await bucket.put(pointerKey(enrolled), hash, {onlyIf: condition}) ? "applied" : "retry";
}

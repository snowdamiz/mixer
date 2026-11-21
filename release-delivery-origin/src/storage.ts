import {
  type Artifact, type Snapshot, type Target, artifactLimit, assignmentLimit, decoder, digest,
  isSnapshot, prefix, sha256, snapshotLimit,
} from "./contract.js";

export type Reader = Pick<R2Bucket, "get" | "head">;

export function pointerKey(target: Target): string {
  return prefix(target) + "/current";
}

export function manifestKey(target: Target, hash: string): string {
  return prefix(target) + "/snapshot/" + hash;
}

export function assignmentKey(target: Target, hash: string): string {
  return prefix(target) + "/assignment/" + hash;
}

export function artifactKey(target: Target, artifact: Artifact): string {
  return prefix(target) + "/artifact/" + artifact.manifest_sha256;
}

async function bounded(body: R2ObjectBody, limit: number): Promise<ArrayBuffer> {
  if (body.size < 1 || body.size > limit) {
    await body.body.cancel();
    throw new Error("object_size");
  }
  const bytes = await body.arrayBuffer();
  if (bytes.byteLength !== body.size) throw new Error("object_size");
  return bytes;
}

export async function checked(bucket: Reader, key: string, digest: string, limit: number): Promise<ArrayBuffer> {
  const object = await bucket.get(key);
  if (!object) throw new Error("object_missing");
  const bytes = await bounded(object, limit);
  if (await sha256(bytes) !== digest) throw new Error("object_digest");
  return bytes;
}

export async function current(bucket: Reader, target: Target) {
  const pointer = await bucket.get(pointerKey(target));
  if (!pointer) return null;
  const hash = decoder.decode(await bounded(pointer, 64));
  if (!digest(hash)) throw new Error("pointer_digest");
  const bytes = await checked(bucket, manifestKey(target, hash), hash, snapshotLimit);
  const snapshot: unknown = JSON.parse(decoder.decode(bytes));
  if (!isSnapshot(snapshot) || prefix(snapshot.target) !== prefix(target)) throw new Error("snapshot");
  return {snapshot, hash, etag: pointer.etag};
}

export function readAssignment(bucket: Reader, snapshot: Snapshot): Promise<ArrayBuffer> {
  const hash = snapshot.head.assignment_sha256;
  return checked(bucket, assignmentKey(snapshot.target, hash), hash, assignmentLimit);
}

export function readArtifact(bucket: Reader, target: Target, artifact: Artifact): Promise<ArrayBuffer> {
  return checked(bucket, artifactKey(target, artifact), artifact.envelope_sha256, artifactLimit);
}

export async function readyArtifact(bucket: Reader, target: Target, artifact: Artifact): Promise<boolean> {
  const object = await bucket.head(artifactKey(target, artifact));
  const checksum = object?.checksums.toJSON().sha256;
  return !!object && object.size >= 1 && object.size <= artifactLimit && checksum === artifact.envelope_sha256;
}

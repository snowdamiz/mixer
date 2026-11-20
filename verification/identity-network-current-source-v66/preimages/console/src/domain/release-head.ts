import { catalogRecord, isBuildCatalogId } from "./build-catalog.js";

type Sha256 = string & { readonly __brand: "Sha256" };
type ReleaseSequence = string & { readonly __brand: "ReleaseSequence" };

export interface ReleaseHeadTarget {
  readonly organizationId: string;
  readonly projectId: string;
  readonly applicationId: string;
  readonly environmentId: string;
  readonly platform: "ios" | "android";
  readonly runtimeFingerprint: Sha256;
  readonly channel: string;
}

export interface PublishedRelease {
  readonly releaseId: string;
  readonly sequence: ReleaseSequence;
  readonly rolloutBasisPoints: number;
  readonly manifestSha256: Sha256;
  readonly payloadSha256: Sha256;
}

export type ReleaseHead =
  | { readonly kind: "empty"; readonly target: ReleaseHeadTarget }
  | { readonly kind: "published"; readonly target: ReleaseHeadTarget; readonly release: PublishedRelease };

const targetFields = [
  ["organization_id", "organizationId"],
  ["project_id", "projectId"],
  ["application_id", "applicationId"],
  ["environment_id", "environmentId"],
  ["platform", "platform"],
  ["runtime_fingerprint", "runtimeFingerprint"],
  ["channel", "channel"],
] as const satisfies readonly (readonly [string, keyof ReleaseHeadTarget])[];
const targetKeys = targetFields.map(([, key]) => key);

function requireValid(value: boolean): asserts value {
  if (!value) throw new TypeError("Invalid release head");
}

function isSha256(value: unknown): value is Sha256 {
  return typeof value === "string" && value.length === 64 && !/[^a-f0-9]/u.test(value);
}

function isReleaseSequence(value: unknown): value is ReleaseSequence {
  return typeof value === "string" && value.length <= 20 && /^[1-9]/u.test(value) &&
    !/[^0-9]/u.test(value) && BigInt(value) <= 18_446_744_073_709_551_615n;
}

export function snapshotReleaseHeadTarget(value: unknown): ReleaseHeadTarget {
  requireValid(catalogRecord(value, targetKeys));
  const { organizationId, projectId, applicationId, environmentId, platform, runtimeFingerprint, channel } = value;
  requireValid(isBuildCatalogId(organizationId) && isBuildCatalogId(projectId) &&
    isBuildCatalogId(applicationId) && isBuildCatalogId(environmentId) && isBuildCatalogId(channel) &&
    (platform === "ios" || platform === "android") && isSha256(runtimeFingerprint));
  return Object.freeze({ organizationId, projectId, applicationId, environmentId, platform, runtimeFingerprint, channel });
}

export type ReleaseHeadLocation =
  | { readonly kind: "missing" | "invalid" }
  | { readonly kind: "target"; readonly target: ReleaseHeadTarget };

export function parseReleaseHeadSearch(search: string): ReleaseHeadLocation {
  if (search === "") return { kind: "missing" };
  const query = new URLSearchParams(search);
  // Count raw segments too: URLSearchParams skips empty segments.
  if (query.size !== targetFields.length || search.split("&").length !== targetFields.length) return { kind: "invalid" };
  try {
    const target = snapshotReleaseHeadTarget(Object.fromEntries(targetFields.map(([param, key]) => [key, query.get(param)])));
    return { kind: "target", target };
  } catch {
    return { kind: "invalid" };
  }
}

export function releaseHeadQuery(target: ReleaseHeadTarget): string {
  return new URLSearchParams(targetFields.map(([param, key]) => [param, target[key]])).toString();
}

export function parseReleaseHead(value: unknown, expected: ReleaseHeadTarget): ReleaseHead {
  requireValid(catalogRecord(value, ["kind", "target"], ["release"]));
  const target = snapshotReleaseHeadTarget(value.target);
  requireValid(targetKeys.every(key => target[key] === expected[key]));
  if (value.kind === "empty" && !Object.hasOwn(value, "release")) return Object.freeze({ kind: "empty", target });
  requireValid(value.kind === "published" &&
    catalogRecord(value.release, ["releaseId", "sequence", "rolloutBasisPoints", "manifestSha256", "payloadSha256"]));
  const { releaseId, sequence, rolloutBasisPoints, manifestSha256, payloadSha256 } = value.release;
  requireValid(isBuildCatalogId(releaseId) && isReleaseSequence(sequence) &&
    typeof rolloutBasisPoints === "number" && Number.isInteger(rolloutBasisPoints) &&
    rolloutBasisPoints >= 0 && rolloutBasisPoints <= 10_000 &&
    isSha256(manifestSha256) && isSha256(payloadSha256));
  return Object.freeze({
    kind: "published", target,
    release: Object.freeze({ releaseId, sequence, rolloutBasisPoints, manifestSha256, payloadSha256 }),
  });
}

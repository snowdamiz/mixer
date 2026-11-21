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
  readonly details: ReleaseHeadDetails;
}

export type PromotionPublication = Pick<PublishedRelease, "sequence" | "manifestSha256"> & {
  readonly target: ReleaseHeadTarget;
};

export type PromotionReceipt = PromotionPublication & {
  readonly head: { readonly kind: "current" } |
    { readonly kind: "advanced"; readonly sequence: ReleaseSequence };
};

export interface PromotionGroup {
  readonly kind: "committed";
  readonly ios: PromotionReceipt;
  readonly android: PromotionReceipt;
}

const manifestPermissions = {
  "network.http.v1": "network.https",
  "storage.keyValue.v1": "storage.appPrivate",
} as const;

type CapabilityId = keyof typeof manifestPermissions;
type Permission = typeof manifestPermissions[CapabilityId];
type LedgerAction = "publish" | "promote" | "stage_promote" | "rollback" | "halt";

interface ReleaseCapability {
  readonly id: CapabilityId;
  readonly permissions: readonly Permission[] | null;
}

interface ReleaseHeadDetails {
  readonly sourceCommit: string;
  readonly payloadBytes: number;
  readonly artifactKeyId: string;
  readonly assignmentKeyId: string;
  readonly action: LedgerAction;
  readonly capabilities: readonly ReleaseCapability[];
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

function isCapabilityId(value: unknown): value is CapabilityId {
  return typeof value === "string" && Object.hasOwn(manifestPermissions, value);
}

function parseCapabilities(value: unknown): readonly ReleaseCapability[] {
  requireValid(Array.isArray(value) && value.length <= 2);
  let previous = "";
  return Object.freeze(Array.from(value, (entry: unknown) => {
    requireValid(catalogRecord(entry, ["id", "permissions"]));
    const { id, permissions } = entry;
    requireValid(isCapabilityId(id) && id > previous);
    previous = id;
    if (permissions === null) return Object.freeze({ id, permissions: null });
    const permission = manifestPermissions[id];
    requireValid(Array.isArray(permissions) &&
      (permissions.length === 0 || (permissions.length === 1 && permissions[0] === permission)));
    return Object.freeze({ id, permissions: Object.freeze(permissions.length === 0 ? [] : [permission]) });
  }));
}

function parseDetails(value: unknown): ReleaseHeadDetails {
  requireValid(catalogRecord(value, ["sourceCommit", "payloadBytes", "artifactKeyId", "assignmentKeyId", "action", "capabilities"]));
  const { sourceCommit, payloadBytes, artifactKeyId, assignmentKeyId, action, capabilities } = value;
  requireValid(typeof sourceCommit === "string" && (sourceCommit.length === 40 || isSha256(sourceCommit)) &&
    !/[^a-f0-9]/u.test(sourceCommit) && typeof payloadBytes === "number" &&
    Number.isInteger(payloadBytes) && payloadBytes >= 1 && payloadBytes <= 4_194_304 &&
    isBuildCatalogId(artifactKeyId) && isBuildCatalogId(assignmentKeyId) &&
    (action === "publish" || action === "promote" || action === "stage_promote" ||
      action === "rollback" || action === "halt"));
  return Object.freeze({ sourceCommit, payloadBytes, artifactKeyId, assignmentKeyId, action, capabilities: parseCapabilities(capabilities) });
}

export function parseReleaseHeadDetails(value: unknown, expected: ReleaseHeadTarget): ReleaseHead {
  requireValid(catalogRecord(value, ["kind", "target"], ["release"]));
  const target = snapshotReleaseHeadTarget(value.target);
  requireValid(targetKeys.every(key => target[key] === expected[key]));
  if (value.kind === "empty" && !Object.hasOwn(value, "release")) return Object.freeze({ kind: "empty", target });
  requireValid(value.kind === "published" &&
    catalogRecord(value.release, ["releaseId", "sequence", "rolloutBasisPoints", "manifestSha256", "payloadSha256", "details"]));
  const { releaseId, sequence, rolloutBasisPoints, manifestSha256, payloadSha256, details } = value.release;
  requireValid(isBuildCatalogId(releaseId) && isReleaseSequence(sequence) &&
    typeof rolloutBasisPoints === "number" && Number.isInteger(rolloutBasisPoints) &&
    rolloutBasisPoints >= 0 && rolloutBasisPoints <= 10_000 &&
    isSha256(manifestSha256) && isSha256(payloadSha256));
  return Object.freeze({
    kind: "published", target,
    release: Object.freeze({ releaseId, sequence, rolloutBasisPoints, manifestSha256, payloadSha256, details: parseDetails(details) }),
  });
}

export function promotionGroupQuery(publication: PromotionPublication): string {
  const { target, sequence, manifestSha256 } = publication;
  requireValid(isReleaseSequence(sequence) && isSha256(manifestSha256));
  return releaseHeadQuery(target) + "&view=promotion-group&sequence=" + sequence +
    "&manifest_sha256=" + manifestSha256;
}

export function parsePromotionGroup(value: unknown, selected: PromotionPublication): PromotionGroup {
  requireValid(catalogRecord(value, ["kind", "ios", "android"]) && value.kind === "committed");
  const expected = selected.target;

  function receipt(input: unknown, platform: ReleaseHeadTarget["platform"]): PromotionReceipt {
    requireValid(catalogRecord(input, ["target", "sequence", "manifestSha256", "headSequence"]));
    const { sequence, manifestSha256, headSequence } = input;
    const target = snapshotReleaseHeadTarget(input.target);
    requireValid(target.platform === platform &&
      target.organizationId === expected.organizationId && target.projectId === expected.projectId &&
      target.applicationId === expected.applicationId && target.environmentId === expected.environmentId &&
      isReleaseSequence(sequence) && isSha256(manifestSha256) && isReleaseSequence(headSequence) &&
      BigInt(headSequence) >= BigInt(sequence));
    const head: PromotionReceipt["head"] = headSequence === sequence ? { kind: "current" } :
      { kind: "advanced", sequence: headSequence };
    return Object.freeze({ target, sequence, manifestSha256, head: Object.freeze(head) });
  }

  const ios = receipt(value.ios, "ios");
  const android = receipt(value.android, "android");
  const anchor = expected.platform === "ios" ? ios : android;
  requireValid(targetKeys.every(key => anchor.target[key] === expected[key]) &&
    anchor.sequence === selected.sequence && anchor.manifestSha256 === selected.manifestSha256);
  return Object.freeze({ kind: "committed", ios, android });
}

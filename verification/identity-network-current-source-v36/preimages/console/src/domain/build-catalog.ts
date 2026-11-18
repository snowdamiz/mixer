import { parseBuildRead, snapshotBuildReadSelection } from "./build-read.js";
import type { BuildReadSelection, BuildReadSnapshot } from "./build-read.js";

export type ProjectSelection = Readonly<Pick<BuildReadSelection, "organizationId" | "projectId">>;
export type ApplicationSelection = Readonly<Pick<BuildReadSelection, "organizationId" | "projectId" | "applicationId">>;
export interface CatalogPageRequest { readonly cursor?: string }
export interface ApplicationPage extends ProjectSelection {
  readonly applications: readonly Readonly<Pick<BuildReadSelection, "applicationId">>[];
  readonly nextCursor: string | null;
}
export interface BuildCatalogRow {
  readonly selection: BuildReadSelection;
  readonly snapshot: BuildReadSnapshot;
}
export interface BuildPage extends ApplicationSelection {
  readonly builds: readonly BuildCatalogRow[];
  readonly nextCursor: string | null;
}

function requireValid(value: boolean): asserts value {
  if (!value) throw new TypeError("Invalid build catalog");
}

/** Closed data records only: never invoke caller accessors while capturing intent. */
export function catalogRecord(value: unknown, required: readonly string[], optional: readonly string[] = []): value is Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value) ||
    (Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null)) return false;
  const descriptors = Object.getOwnPropertyDescriptors(value);
  return required.every(key => Object.hasOwn(descriptors, key)) && Reflect.ownKeys(descriptors).every(key => {
    if (typeof key !== "string" || (!required.includes(key) && !optional.includes(key))) return false;
    const descriptor = descriptors[key];
    return descriptor !== undefined && Object.hasOwn(descriptor, "value") && descriptor.enumerable === true;
  });
}

function identifier(value: unknown): value is string {
  return typeof value === "string" && value.length >= 1 && value.length <= 128 && /^[A-Za-z0-9._-]+$/u.test(value);
}

/** Opaque continuation syntax is checked here; only the server interprets its contents. */
function cursor(value: unknown): value is string {
  if (typeof value !== "string" || value.length === 0 || value.length > 1400 || !/^[A-Za-z0-9_-]+$/u.test(value)) return false;
  try {
    const decoded = atob(value.replace(/-/gu, "+").replace(/_/gu, "/"));
    return decoded.length <= 1024 && btoa(decoded).replace(/\+/gu, "-").replace(/\//gu, "_").replace(/=+$/u, "") === value;
  } catch { return false; }
}

export function snapshotProjectSelection(input: unknown): ProjectSelection {
  requireValid(catalogRecord(input, ["organizationId", "projectId"]));
  const { organizationId, projectId } = input;
  requireValid(identifier(organizationId) && identifier(projectId));
  return Object.freeze({ organizationId, projectId });
}

export function snapshotApplicationSelection(input: unknown): ApplicationSelection {
  requireValid(catalogRecord(input, ["organizationId", "projectId", "applicationId"]));
  const { organizationId, projectId, applicationId } = input;
  requireValid(identifier(organizationId) && identifier(projectId) && identifier(applicationId));
  return Object.freeze({ organizationId, projectId, applicationId });
}

export function snapshotCatalogPageRequest(input: unknown): CatalogPageRequest {
  requireValid(catalogRecord(input, [], ["cursor"]));
  if (!Object.hasOwn(input, "cursor")) return Object.freeze({});
  const value = input.cursor;
  requireValid(cursor(value));
  return Object.freeze({ cursor: value });
}

function rows(input: unknown): readonly unknown[] {
  requireValid(Array.isArray(input) && Object.getPrototypeOf(input) === Array.prototype && input.length <= 25);
  requireValid(Reflect.ownKeys(input).length === input.length + 1);
  for (let index = 0; index < input.length; index++) {
    const descriptor = Object.getOwnPropertyDescriptor(input, String(index));
    requireValid(descriptor !== undefined && Object.hasOwn(descriptor, "value") && descriptor.enumerable === true);
  }
  return input;
}

function nextCursor(input: unknown): string | null {
  requireValid(input === null || cursor(input));
  return input;
}

export function parseApplicationPage(input: unknown, expected: ProjectSelection): ApplicationPage {
  const scope = snapshotProjectSelection(expected);
  requireValid(catalogRecord(input, ["organizationId", "projectId", "applications", "nextCursor"]));
  requireValid(input.organizationId === scope.organizationId && input.projectId === scope.projectId);
  let previous: string | undefined;
  const applications = rows(input.applications).map(row => {
    requireValid(catalogRecord(row, ["applicationId"]));
    const applicationId = row.applicationId;
    requireValid(identifier(applicationId) && (previous === undefined || previous < applicationId));
    previous = applicationId;
    return Object.freeze({ applicationId });
  });
  return Object.freeze({ ...scope, applications: Object.freeze(applications), nextCursor: nextCursor(input.nextCursor) });
}

export function parseBuildPage(input: unknown, expected: ApplicationSelection): BuildPage {
  const scope = snapshotApplicationSelection(expected);
  requireValid(catalogRecord(input, ["organizationId", "projectId", "applicationId", "builds", "nextCursor"]));
  requireValid(input.organizationId === scope.organizationId && input.projectId === scope.projectId && input.applicationId === scope.applicationId);
  let previous: BuildReadSelection | undefined;
  const builds = rows(input.builds).map(row => {
    requireValid(catalogRecord(row, ["organizationId", "projectId", "applicationId", "buildId", "platform",
      "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256", "revision", "state", "attempt",
      "maxAttempts", "failureCode", "workerCompletionPending"]));
    const selection = snapshotBuildReadSelection({ organizationId: row.organizationId, projectId: row.projectId,
      applicationId: row.applicationId, buildId: row.buildId, platform: row.platform,
      sourceSha256: row.sourceSha256, toolchainLockSha256: row.toolchainLockSha256,
      buildDefinitionSha256: row.buildDefinitionSha256 });
    requireValid(selection.organizationId === scope.organizationId && selection.projectId === scope.projectId &&
      selection.applicationId === scope.applicationId);
    requireValid(previous === undefined || previous.buildId < selection.buildId ||
      (previous.buildId === selection.buildId && previous.platform < selection.platform));
    const snapshot = parseBuildRead({ build: row }, selection);
    previous = selection;
    return Object.freeze({ selection, snapshot });
  });
  return Object.freeze({ ...scope, builds: Object.freeze(builds), nextCursor: nextCursor(input.nextCursor) });
}

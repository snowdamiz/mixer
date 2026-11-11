import { summarizeBuildOverview } from "./build-overview.js";
import type { ReportedPlatformBuild } from "./build-overview.js";

export type BuildReadSelection = Readonly<Pick<ReportedPlatformBuild,
  "organizationId" | "projectId" | "applicationId" | "buildId" | "platform" |
  "sourceSha256" | "toolchainLockSha256" | "buildDefinitionSha256">>;
export interface BuildReadSnapshot {
  readonly revision: number;
  readonly report: ReportedPlatformBuild;
}

const selectionKeys = ["organizationId", "projectId", "applicationId", "buildId", "platform",
  "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256"] as const;
const buildKeys = [...selectionKeys, "revision", "state", "attempt", "maxAttempts", "failureCode", "workerCompletionPending"];

function requireValid(value: boolean): asserts value {
  if (!value) throw new TypeError("Invalid build read");
}
function closed(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    Reflect.ownKeys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
}
function identifier(value: unknown): value is string {
  return typeof value === "string" && value.length >= 1 && value.length <= 128 && /^[A-Za-z0-9._-]+$/u.test(value);
}
function digest(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/u.test(value);
}

/** Capture caller intent before any asynchronous work; this conveys no authority. */
export function snapshotBuildReadSelection(input: unknown): BuildReadSelection {
  requireValid(closed(input, selectionKeys));
  const { organizationId, projectId, applicationId, buildId, platform,
    sourceSha256, toolchainLockSha256, buildDefinitionSha256 } = input;
  requireValid(identifier(organizationId) && identifier(projectId) && identifier(applicationId) && identifier(buildId) &&
    (platform === "ios" || platform === "android") && digest(sourceSha256) &&
    digest(toolchainLockSha256) && digest(buildDefinitionSha256));
  return Object.freeze({ organizationId, projectId, applicationId, buildId, platform,
    sourceSha256, toolchainLockSha256, buildDefinitionSha256 });
}

/** Decode only the closed server projection for the caller's exact selection. */
export function parseBuildRead(input: unknown, expected: BuildReadSelection): BuildReadSnapshot {
  const selection = snapshotBuildReadSelection(expected);
  requireValid(closed(input, ["build"]) && closed(input.build, buildKeys));
  const build = input.build;
  requireValid(selectionKeys.every(key => build[key] === selection[key]));
  const revision = build.revision;
  // Snapshot.project equals revision to Journal's event count, bounded to 32.
  requireValid(typeof revision === "number" && Number.isSafeInteger(revision) && revision >= 0 && revision <= 32);
  const { organizationId, projectId, applicationId, ...target } = selection;
  const scope = { organizationId, projectId, applicationId };
  const display = summarizeBuildOverview({ scope, expected: [target], reports: [{ ...selection,
    state: build.state, attempt: build.attempt, maxAttempts: build.maxAttempts,
    workerCompletionPending: build.workerCompletionPending,
    ...(build.failureCode === null ? {} : { failureCode: build.failureCode }),
  }] });
  const observation = display.builds[0]?.observation;
  requireValid(observation !== undefined && observation !== null);
  return Object.freeze({ revision, report: Object.freeze({ ...selection, ...observation }) });
}

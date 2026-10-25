export type BuildPlatform = "ios" | "android";
export type BuildState = "queued" | "running" | "cancelling" | "reconciling" |
  "succeeded" | "failed" | "cancelled" | "timed_out";
export type BuildFailureCode = "worker_unavailable" | "worker_lost" | "dependency_transport" |
  "artifact_transport" | "worker_timeout" | "compiler_error" | "test_failure" |
  "policy_rejection" | "invalid_input" | "unknown_failure";

export interface BuildScope {
  readonly organizationId: string;
  readonly projectId: string;
  readonly applicationId: string;
}

export interface PlatformBuildIdentity {
  readonly platform: BuildPlatform;
  readonly buildId: string;
  readonly sourceSha256: string;
  readonly toolchainLockSha256: string;
  readonly buildDefinitionSha256: string;
}

export interface ExpectedPlatformBuild extends PlatformBuildIdentity {
  readonly source?: { readonly kind: "revision" | "upload"; readonly reference: string };
}

export interface BuildObservation {
  readonly state: BuildState;
  readonly attempt: number;
  readonly maxAttempts: number;
  readonly workerCompletionPending: boolean;
  readonly failureCode?: BuildFailureCode;
}

/** Internal display input. A future authorized Phoenix adapter must join spec and status. */
export interface ReportedPlatformBuild extends BuildScope, PlatformBuildIdentity, BuildObservation {}

export interface BuildOverviewInput {
  readonly scope: BuildScope;
  readonly expected: readonly ExpectedPlatformBuild[];
  readonly reports: readonly ReportedPlatformBuild[];
}

export interface BuildOverviewSnapshot {
  readonly scope: BuildScope;
  readonly builds: readonly {
    readonly target: ExpectedPlatformBuild;
    readonly observation: BuildObservation | null;
  }[];
  readonly reportedCount: number;
}

const scopeKeys = ["organizationId", "projectId", "applicationId"] as const;
const identityKeys = ["platform", "buildId", "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256"] as const;
const observationKeys = ["state", "attempt", "maxAttempts", "workerCompletionPending"] as const;
const states: readonly string[] = ["queued", "running", "cancelling", "reconciling", "succeeded", "failed", "cancelled", "timed_out"];
const pendingStates: readonly string[] = ["running", "cancelling", "reconciling"];
const failureCodes: readonly string[] = ["worker_unavailable", "worker_lost", "dependency_transport",
  "artifact_transport", "worker_timeout", "compiler_error", "test_failure", "policy_rejection", "invalid_input", "unknown_failure"];

function requireValid(value: boolean, reason: string): asserts value {
  if (!value) throw new TypeError(reason);
}

function object(value: unknown, required: readonly string[], optional: readonly string[] = []): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) &&
    required.every(key => Object.hasOwn(value, key)) &&
    Object.keys(value).every(key => required.includes(key) || optional.includes(key));
}

function text(value: unknown, maximum = 256): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maximum &&
    value.trim() === value && !/[\u0000-\u001f\u007f]/u.test(value);
}

function sha256(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/u.test(value);
}

function identity(value: Record<string, unknown>): boolean {
  return (value.platform === "ios" || value.platform === "android") && text(value.buildId) &&
    sha256(value.sourceSha256) && sha256(value.toolchainLockSha256) && sha256(value.buildDefinitionSha256);
}

function copyTarget(value: Record<string, unknown>): ExpectedPlatformBuild {
  const target: PlatformBuildIdentity = {
    platform: value.platform as BuildPlatform, buildId: value.buildId as string,
    sourceSha256: value.sourceSha256 as string, toolchainLockSha256: value.toolchainLockSha256 as string,
    buildDefinitionSha256: value.buildDefinitionSha256 as string,
  };
  if (!Object.hasOwn(value, "source")) return Object.freeze(target);
  const source = value.source;
  requireValid(object(source, ["kind", "reference"]) &&
    (source.kind === "revision" || source.kind === "upload") && text(source.reference, 1024), "Invalid source label");
  return Object.freeze({ ...target, source: Object.freeze({ kind: source.kind, reference: source.reference }) });
}

/** Validate and snapshot a bounded display selection. This grants no build or release authority. */
export function summarizeBuildOverview(input: unknown): BuildOverviewSnapshot {
  requireValid(object(input, ["scope", "expected", "reports"]), "Invalid build overview");
  const { scope, expected, reports } = input;
  requireValid(object(scope, scopeKeys) && scopeKeys.every(key => text(scope[key])), "Invalid build scope");
  requireValid(Array.isArray(expected) && expected.length > 0 && expected.length <= 2, "Invalid expected platforms");
  requireValid(Array.isArray(reports) && reports.length <= expected.length, "Invalid build report count");
  const targets = new Map<BuildPlatform, ExpectedPlatformBuild>();
  for (const value of expected) {
    requireValid(object(value, identityKeys, ["source"]) && identity(value), "Invalid expected build identity");
    const target = copyTarget(value);
    requireValid(!targets.has(target.platform), "Duplicate expected platform");
    targets.set(target.platform, target);
  }
  const observations = new Map<BuildPlatform, BuildObservation>();
  for (const value of reports) {
    requireValid(object(value, [...scopeKeys, ...identityKeys, ...observationKeys], ["failureCode"]) &&
      identity(value) && scopeKeys.every(key => value[key] === scope[key]), "Invalid reported build identity");
    const target = targets.get(value.platform as BuildPlatform);
    requireValid(target !== undefined && identityKeys.every(key => value[key] === target[key]), "Report does not match selected build");
    requireValid(!observations.has(target.platform), "Duplicate build report");
    requireValid(typeof value.state === "string" && states.includes(value.state) &&
      typeof value.attempt === "number" && Number.isInteger(value.attempt) && value.attempt >= 1 &&
      typeof value.maxAttempts === "number" && Number.isInteger(value.maxAttempts) && value.maxAttempts <= 5 &&
      value.attempt <= value.maxAttempts &&
      typeof value.workerCompletionPending === "boolean" && value.workerCompletionPending === pendingStates.includes(value.state),
    "Invalid build status");
    const failed = value.state === "failed" || value.state === "timed_out";
    requireValid(failed ? typeof value.failureCode === "string" && failureCodes.includes(value.failureCode) :
      !Object.hasOwn(value, "failureCode"), "Invalid failure status");
    const observation: BuildObservation = {
      state: value.state as BuildState, attempt: value.attempt, maxAttempts: value.maxAttempts,
      workerCompletionPending: value.workerCompletionPending,
      ...(failed ? { failureCode: value.failureCode as BuildFailureCode } : {}),
    };
    observations.set(target.platform, Object.freeze(observation));
  }
  return Object.freeze({
    scope: Object.freeze({ organizationId: scope.organizationId as string, projectId: scope.projectId as string,
      applicationId: scope.applicationId as string }),
    builds: Object.freeze([...targets.values()].map(target => Object.freeze({ target,
      observation: observations.get(target.platform) ?? null }))),
    reportedCount: observations.size,
  });
}

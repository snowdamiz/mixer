import { summarizeBuildOverview } from "./build-overview.js";
import type { BuildState, ReportedPlatformBuild } from "./build-overview.js";

export type BuildReadSelection = Readonly<Pick<ReportedPlatformBuild,
  "organizationId" | "projectId" | "applicationId" | "buildId" | "platform" |
  "sourceSha256" | "toolchainLockSha256" | "buildDefinitionSha256">>;
export interface BuildReadSnapshot {
  readonly revision: number;
  readonly report: ReportedPlatformBuild;
  readonly artifacts?: readonly RetainedNativeArtifact[];
}

export interface RetainedNativeArtifact {
  readonly kind: typeof nativeArtifactKinds[number];
  readonly sizeBytes: number;
  readonly sha256: string;
  readonly downloadPath: string;
}
const selectionKeys = ["organizationId", "projectId", "applicationId", "buildId", "platform",
  "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256"] as const;
const buildKeys = [...selectionKeys, "revision", "state", "attempt", "maxAttempts", "failureCode", "workerCompletionPending"];
const nativeBuildKeys = [...buildKeys, "artifacts"];
const logKeys = [...buildKeys, "events"];
const nativeArtifactKinds = ["unsigned_native_binary", "debug_symbols", "resource_inventory"] as const;
const compilerPhases: readonly ("compile" | "link" | "package")[] = ["compile", "link", "package"];

type RetainedLogState = Extract<BuildState, "native_succeeded" | "failed" | "cancelled" | "timed_out">;
export interface BuildLogTarget {
  readonly selection: BuildReadSelection & { readonly platform: "ios" };
  readonly revision: number;
  readonly attempt: number;
  readonly state: RetainedLogState;
}

interface CommandFinished {
  readonly event: "build_command_finished";
  readonly exitCode: number;
}
interface CompilerFinished {
  readonly event: "compiler_finished";
  readonly exitCode: number;
  readonly stdoutBytes: number;
  readonly stderrBytes: number;
  readonly tailTruncated: boolean;
  readonly phases: typeof compilerPhases;
}
export type BuildLogEvents = readonly [CommandFinished] | readonly [CompilerFinished, CommandFinished];

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
function integerIn(value: unknown, min: number, max: number): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= min && value <= max;
}
function retainedLogState(value: unknown): value is RetainedLogState {
  return value === "native_succeeded" || value === "failed" || value === "cancelled" || value === "timed_out";
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

export function buildSelectionQuery(selection: BuildReadSelection): string {
  const fields: readonly (readonly [string, string])[] = [
    ["organization_id", selection.organizationId], ["project_id", selection.projectId],
    ["application_id", selection.applicationId], ["build_id", selection.buildId], ["platform", selection.platform],
    ["source_sha256", selection.sourceSha256], ["toolchain_lock_sha256", selection.toolchainLockSha256],
    ["build_definition_sha256", selection.buildDefinitionSha256],
  ];
  return fields.map(([key, value]) => `${key}=${encodeURIComponent(value)}`).join("&");
}

/** Decode only the closed server projection for the caller's exact selection. */
export function parseBuildRead(input: unknown, expected: BuildReadSelection): BuildReadSnapshot {
  const selection = snapshotBuildReadSelection(expected);
  requireValid(closed(input, ["build"]));
  if (closed(input.build, nativeBuildKeys)) {
    requireValid(selection.platform === "ios" && input.build.state === "native_succeeded");
    const snapshot = parseBuildFields(input.build, selection);
    return Object.freeze({ ...snapshot, artifacts: parseNativeArtifacts(input.build.artifacts, selection) });
  }
  requireValid(closed(input.build, buildKeys) && input.build.state !== "native_succeeded");
  return parseBuildFields(input.build, selection);
}

function parseNativeArtifacts(input: unknown, selection: BuildReadSelection): readonly RetainedNativeArtifact[] {
  requireValid(Array.isArray(input) && input.length === nativeArtifactKinds.length);
  const query = buildSelectionQuery(selection);
  const expected = new URLSearchParams(query);
  return Object.freeze(nativeArtifactKinds.map((expectedKind, index) => {
    const item: unknown = input[index];
    requireValid(closed(item, ["kind", "sizeBytes", "sha256", "downloadPath"]));
    const { kind, sizeBytes, sha256, downloadPath } = item;
    const prefix = `/console-api/v1/build-artifacts/${expectedKind}?`;
    requireValid(kind === expectedKind && integerIn(sizeBytes, 1, 16 * 1024 * 1024) && digest(sha256) &&
      typeof downloadPath === "string" && downloadPath.length <= 2048 && downloadPath.startsWith(prefix));
    const supplied = new URLSearchParams(downloadPath.slice(prefix.length));
    requireValid(supplied.size === expected.size);
    expected.forEach((value, key) => requireValid(supplied.get(key) === value));
    return Object.freeze({ kind: expectedKind, sizeBytes, sha256, downloadPath: prefix + query });
  }));
}

function parseBuildFields(build: Record<string, unknown>, selection: BuildReadSelection): BuildReadSnapshot {
  requireValid(selectionKeys.every(key => build[key] === selection[key]));
  const revision = build.revision;
  // Snapshot.project equals revision to Journal's event count, bounded to 32.
  requireValid(integerIn(revision, 0, 32));
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

export function buildLogTarget({ selection, snapshot }: Readonly<{
  selection: BuildReadSelection;
  snapshot: BuildReadSnapshot;
}>): BuildLogTarget | undefined {
  const { state, attempt, workerCompletionPending } = snapshot.report;
  if (selection.platform !== "ios" || workerCompletionPending || !retainedLogState(state) ||
    !integerIn(snapshot.revision, 1, 32)) return undefined;
  return { selection: { ...selection, platform: selection.platform }, state, attempt, revision: snapshot.revision };
}

/** Capture both the immutable build key and the displayed terminal attempt. */
export function snapshotBuildLogTarget(input: unknown): BuildLogTarget {
  requireValid(closed(input, ["selection", "revision", "attempt", "state"]));
  const selection = snapshotBuildReadSelection(input.selection);
  const { revision, attempt, state } = input;
  requireValid(selection.platform === "ios" && retainedLogState(state) &&
    integerIn(revision, 1, 32) && integerIn(attempt, 1, 5));
  return Object.freeze({ selection: Object.freeze({ ...selection, platform: selection.platform }), revision, attempt, state });
}

export function parseBuildLogs(input: unknown, target: BuildLogTarget): BuildLogEvents {
  requireValid(closed(input, ["buildLogs"]) && closed(input.buildLogs, logKeys));
  const build = input.buildLogs;
  requireValid(build.state === target.state);
  const snapshot = parseBuildFields(build, target.selection);
  requireValid(snapshot.revision === target.revision && snapshot.report.attempt === target.attempt);

  const events: unknown = build.events;
  requireValid(Array.isArray(events) && (events.length === 1 || events.length === 2));
  const command: unknown = events[events.length - 1];
  requireValid(closed(command, ["event", "exitCode"]) && command.event === "build_command_finished" &&
    integerIn(command.exitCode, -255, 255));
  const commandFinished: CommandFinished = Object.freeze({ event: command.event, exitCode: command.exitCode });
  if (events.length === 1) return Object.freeze([commandFinished]);

  const compiler: unknown = events[0];
  requireValid(closed(compiler, ["event", "exitCode", "stdoutBytes", "stderrBytes", "tailTruncated", "phases"]));
  const { event, exitCode, stdoutBytes, stderrBytes, tailTruncated, phases } = compiler;
  requireValid(event === "compiler_finished" && integerIn(exitCode, -255, 255) &&
    integerIn(stdoutBytes, 0, 2 ** 32) && integerIn(stderrBytes, 0, 2 ** 32) &&
    typeof tailTruncated === "boolean" && Array.isArray(phases) && phases.length <= compilerPhases.length);
  const knownPhases = compilerPhases.filter(phase => phases.includes(phase));
  requireValid(knownPhases.length === phases.length && knownPhases.every((phase, index) => phase === phases[index]));
  return Object.freeze([
    Object.freeze({ event, exitCode, stdoutBytes, stderrBytes, tailTruncated, phases: Object.freeze(knownPhases) }),
    commandFinished,
  ]);
}

import { catalogRecord, snapshotApplicationSelection, snapshotCatalogPageRequest } from "./build-catalog.js";
import type { ApplicationSelection } from "./build-catalog.js";
import { snapshotBuildReadSelection } from "./build-read.js";
import type { BuildReadSelection } from "./build-read.js";
import type { BuildState } from "./build-overview.js";

export type BuildInput = Readonly<Pick<BuildReadSelection, "platform" | "sourceSha256" | "toolchainLockSha256" | "buildDefinitionSha256"> & { sourceInputId: string }>;
export interface BuildInputPage extends ApplicationSelection { readonly inputs: readonly BuildInput[]; readonly nextCursor: string | null }
export interface BuildAttempt { readonly scope: ApplicationSelection; readonly input: BuildInput; readonly key: string; readonly body: string }
export interface BuildReceipt { readonly outcome: "applied" | "duplicate"; readonly selection: BuildReadSelection; readonly state: BuildState; readonly revision: number }
function valid(value: boolean): asserts value { if (!value) throw new TypeError("Invalid build submission"); }
const id = (value: unknown): value is string => typeof value === "string" && /^[A-Za-z0-9._-]{1,128}$/u.test(value);
const digest = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/u.test(value);
export function parseBuildInput(value: unknown): BuildInput {
  valid(catalogRecord(value, ["platform", "sourceInputId", "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256"]));
  const { platform, sourceInputId, sourceSha256, toolchainLockSha256, buildDefinitionSha256 } = value;
  valid((platform === "ios" || platform === "android") && id(sourceInputId) && digest(sourceSha256) && digest(toolchainLockSha256) && digest(buildDefinitionSha256));
  return Object.freeze({ platform, sourceInputId, sourceSha256, toolchainLockSha256, buildDefinitionSha256 });
}
export function parseBuildInputs(value: unknown, expected: ApplicationSelection): BuildInputPage {
  const scope = snapshotApplicationSelection(expected);
  valid(catalogRecord(value, ["organizationId", "projectId", "applicationId", "inputs", "nextCursor"]));
  valid(value.organizationId === scope.organizationId && value.projectId === scope.projectId && value.applicationId === scope.applicationId);
  valid(Array.isArray(value.inputs) && value.inputs.length <= 25 && Reflect.ownKeys(value.inputs).length === value.inputs.length + 1);
  let previous: BuildInput | undefined;
  const inputs = value.inputs.map(raw => {
    const row = parseBuildInput(raw);
    valid(previous === undefined || previous.platform < row.platform || (previous.platform === row.platform && previous.sourceInputId < row.sourceInputId));
    previous = row; return row;
  });
  const nextCursor = value.nextCursor === null ? null : snapshotCatalogPageRequest({ cursor: value.nextCursor }).cursor;
  valid(nextCursor !== undefined && (nextCursor === null || inputs.length === 25));
  return Object.freeze({ ...scope, inputs: Object.freeze(inputs), nextCursor });
}
export function captureBuildAttempt(scopeInput: ApplicationSelection, inputValue: BuildInput): BuildAttempt {
  const scope = snapshotApplicationSelection(scopeInput), input = parseBuildInput(inputValue);
  const key = crypto.randomUUID();
  valid(/^[a-f0-9-]{36}$/u.test(key));
  return Object.freeze({ scope, input, key, body: buildBody(scope, input) });
}
function buildBody(scope: ApplicationSelection, input: BuildInput): string {
  return JSON.stringify({ organization_id: scope.organizationId, project_id: scope.projectId, application_id: scope.applicationId,
    platform: input.platform, source_input_id: input.sourceInputId, source_sha256: input.sourceSha256,
    toolchain_lock_sha256: input.toolchainLockSha256, build_definition_sha256: input.buildDefinitionSha256 });
}
/** Capture the public client boundary, including exact retry bytes, before dispatch. */
export function snapshotBuildAttempt(value: unknown): BuildAttempt {
  valid(catalogRecord(value, ["scope", "input", "key", "body"]));
  const scope = snapshotApplicationSelection(value.scope), input = parseBuildInput(value.input);
  const { key, body } = value;
  valid(typeof key === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/u.test(key));
  valid(typeof body === "string" && body === buildBody(scope, input));
  return Object.freeze({ scope, input, key, body });
}
export function parseBuildReceipt(value: unknown, attempt: BuildAttempt, status: number): BuildReceipt {
  valid(catalogRecord(value, ["outcome", "selection", "state", "revision"]));
  valid((status === 201 && value.outcome === "applied") || (status === 200 && value.outcome === "duplicate"));
  const s = value.selection;
  valid(catalogRecord(s, ["organization_id", "project_id", "application_id", "build_id", "platform", "source_sha256", "toolchain_lock_sha256", "build_definition_sha256"]));
  const selection = snapshotBuildReadSelection({ organizationId: s.organization_id, projectId: s.project_id, applicationId: s.application_id,
    buildId: s.build_id, platform: s.platform, sourceSha256: s.source_sha256, toolchainLockSha256: s.toolchain_lock_sha256, buildDefinitionSha256: s.build_definition_sha256 });
  valid(/^build-[a-f0-9]{64}$/u.test(selection.buildId));
  valid(selection.organizationId === attempt.scope.organizationId && selection.projectId === attempt.scope.projectId && selection.applicationId === attempt.scope.applicationId &&
    selection.platform === attempt.input.platform && selection.sourceSha256 === attempt.input.sourceSha256 && selection.toolchainLockSha256 === attempt.input.toolchainLockSha256 && selection.buildDefinitionSha256 === attempt.input.buildDefinitionSha256);
  const { revision, state, outcome } = value;
  valid(typeof revision === "number" && Number.isSafeInteger(revision) && revision >= 0 && revision <= 32);
  valid(state === "queued" || state === "running" || state === "cancelling" || state === "reconciling" || state === "succeeded" || state === "failed" || state === "cancelled" || state === "timed_out");
  valid(outcome === "applied" || outcome === "duplicate");
  valid(outcome !== "applied" || state === "queued");
  return Object.freeze({ outcome, selection, revision, state });
}

/** Bounded wire grammar rejects duplicate object keys before schema decoding. */
export function parseSubmissionJSON(text: string): unknown {
  let at = 0;
  const ws = () => { while (/[\x20\t\r\n]/u.test(text[at] ?? "x")) at++; };
  const string = (): string => {
    valid(text[at] === '"'); const start = at++;
    while (at < text.length) {
      const c = text[at++];
      if (c === '"') { const value: unknown = JSON.parse(text.slice(start, at)); valid(typeof value === "string"); return value; }
      if (c === "\\") at++;
    }
    throw new TypeError();
  };
  const value = (depth: number): unknown => {
    valid(depth < 8); ws();
    if (text[at] === '"') return string();
    if (text[at] === "{") {
      at++; const result: Record<string, unknown> = Object.create(null); ws();
      if (text[at] === "}") { at++; return result; }
      while (true) {
        ws(); const key = string(); valid(!Object.hasOwn(result, key)); ws(); valid(text[at++] === ":"); result[key] = value(depth + 1); ws();
        const c = text[at++]; if (c === "}") return result; valid(c === ",");
      }
    }
    if (text[at] === "[") {
      at++; const result: unknown[] = []; ws(); if (text[at] === "]") { at++; return result; }
      while (true) { valid(result.length < 25); result.push(value(depth + 1)); ws(); const c = text[at++]; if (c === "]") return result; valid(c === ","); }
    }
    const token = /^(?:null|true|false|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/u.exec(text.slice(at))?.[0];
    valid(token !== undefined); at += token.length; return JSON.parse(token) as unknown;
  };
  const result = value(0); ws(); valid(at === text.length); return result;
}

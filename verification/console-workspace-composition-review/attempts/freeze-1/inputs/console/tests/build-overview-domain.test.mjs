import assert from "node:assert/strict";
import test from "node:test";
import { summarizeBuildOverview } from "../src/domain/build-overview.ts";

const scope = { organizationId: "org", projectId: "project", applicationId: "app" };
const expected = [
  { platform: "ios", buildId: "ios-build-42", sourceSha256: "a".repeat(64),
    toolchainLockSha256: "b".repeat(64), buildDefinitionSha256: "c".repeat(64),
    source: { kind: "revision", reference: "feature/fieldlog" } },
  { platform: "android", buildId: "android-build-73", sourceSha256: "d".repeat(64),
    toolchainLockSha256: "e".repeat(64), buildDefinitionSha256: "f".repeat(64) },
];
const states = ["queued", "running", "cancelling", "reconciling", "succeeded", "failed", "cancelled", "timed_out"];
function report(target, state = "succeeded") {
  const { source: _source, ...identity } = target;
  return { ...scope, ...identity, state, attempt: 2, maxAttempts: 3,
    workerCompletionPending: ["running", "cancelling", "reconciling"].includes(state),
    ...(state === "failed" ? { failureCode: "compiler_error" } : state === "timed_out" ? { failureCode: "worker_timeout" } : {}),
  };
}
const input = () => structuredClone({ scope, expected, reports: expected.map(target => report(target)) });

test("all 64 platform state pairs preserve exact outcomes, attempt counts, and expected order", () => {
  for (const ios of states) for (const android of states) {
    const value = input(); value.reports = [report(expected[1], android), report(expected[0], ios)];
    const result = summarizeBuildOverview(value);
    assert.deepEqual(result.builds.map(row => [row.target.buildId, row.observation.state, row.observation.attempt, row.observation.maxAttempts]),
      [["ios-build-42", ios, 2, 3], ["android-build-73", android, 2, 3]]);
    assert.equal(result.reportedCount, 2);
    assert.equal(Object.hasOwn(result, "state"), false);
  }
});

test("every missing platform remains selected and unreported, including zero updates", () => {
  for (const reports of [[], [report(expected[0])], [report(expected[1])]]) {
    const result = summarizeBuildOverview({ scope, expected, reports });
    assert.equal(result.builds.length, 2);
    assert.equal(result.reportedCount, reports.length);
    for (const row of result.builds) assert.equal(row.observation === null,
      !reports.some(update => update.platform === row.target.platform));
  }
  const value = input(); value.expected = [value.expected[1]]; value.reports = [value.reports[1]];
  assert.equal(summarizeBuildOverview(value).builds[0].target.platform, "android");
});

test("each scope and immutable identity mismatch fails closed, even beside another valid platform", () => {
  for (const key of ["organizationId", "projectId", "applicationId", "buildId", "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256"]) {
    const value = input(); value.reports[1][key] = key.endsWith("Sha256") ? "0".repeat(64) : "different";
    assert.throws(() => summarizeBuildOverview(value), TypeError, key);
  }
});

test("duplicate, unexpected, malformed and unsupported platform/status data cannot be summarized", () => {
  const cases = [null, {}, { ...input(), extra: true },
    { ...input(), scope: { ...scope, permission: true } },
    { ...input(), expected: [] }, { ...input(), expected: [...expected, expected[0]] },
    { ...input(), expected: [expected[0], expected[0]] },
    { ...input(), reports: [report(expected[0]), report(expected[0])] },
    { ...input(), reports: [null] }, { ...input(), reports: "" },
  ];
  for (const change of [
    { platform: "web" }, { state: "success" }, { state: undefined }, { attempt: 0 }, { attempt: 4 },
    { attempt: 1.5 }, { maxAttempts: 6 }, { maxAttempts: 0 }, { workerCompletionPending: "false" },
    { sourceSha256: "A".repeat(64) }, { toolchainLockSha256: "b".repeat(63) },
    { buildId: "\u0000invalid" }, { buildId: "x".repeat(129) }, { buildId: "" }, { downloadUrl: "https://invalid.test" },
  ]) { const value = input(); Object.assign(value.reports[1], change); cases.push(value); }
  for (const value of cases) assert.throws(() => summarizeBuildOverview(value), TypeError);
});

test("worker uncertainty must match the accepted lifecycle in all eight states", () => {
  for (const state of states) {
    const value = input(); value.reports[0] = report(expected[0], state);
    value.reports[0].workerCompletionPending = !value.reports[0].workerCompletionPending;
    assert.throws(() => summarizeBuildOverview(value), TypeError, state);
  }
});

test("failure codes are closed lifecycle values and only describe failed or timed-out attempts", () => {
  const codes = ["worker_unavailable", "worker_lost", "dependency_transport", "artifact_transport", "worker_timeout",
    "compiler_error", "test_failure", "policy_rejection", "invalid_input", "unknown_failure"];
  for (const state of ["failed", "timed_out"]) for (const failureCode of codes) {
    const value = input(); value.reports[0] = { ...report(expected[0], state), failureCode };
    assert.equal(summarizeBuildOverview(value).builds[0].observation.failureCode, failureCode);
  }
  for (const state of states) {
    const value = input(); value.reports[0] = { ...report(expected[0], state), failureCode: "unknown-code" };
    assert.throws(() => summarizeBuildOverview(value), TypeError);
  }
  for (const state of ["failed", "timed_out"]) {
    const value = input(); value.reports[0] = report(expected[0], state); delete value.reports[0].failureCode;
    assert.throws(() => summarizeBuildOverview(value), TypeError);
  }
  const value = input(); value.reports[0].failureCode = "compiler_error";
  assert.throws(() => summarizeBuildOverview(value), TypeError);
});

test("optional source labels are selected metadata with closed bounded shape", () => {
  for (const source of [null, { kind: "git", reference: "main" }, { kind: "revision", reference: "" },
    { kind: "revision", reference: "x".repeat(1025) }, { kind: "upload", reference: "x", url: "x" }]) {
    const value = input(); value.expected[0].source = source;
    assert.throws(() => summarizeBuildOverview(value), TypeError);
  }
  const value = input(); value.reports[0].source = { kind: "revision", reference: "other" };
  assert.throws(() => summarizeBuildOverview(value), TypeError);
  delete value.reports[0].source; delete value.expected[0].source;
  assert.equal(Object.hasOwn(summarizeBuildOverview(value).builds[0].target, "source"), false);
});

test("the complete snapshot is copied and frozen without caller-owned aliases", () => {
  const value = input(); const result = summarizeBuildOverview(value);
  value.scope.projectId = "other"; value.expected[0].source.reference = "changed";
  value.expected[0].toolchainLockSha256 = "0".repeat(64); value.reports[0].state = "failed";
  assert.equal(result.scope.projectId, "project");
  assert.equal(result.builds[0].target.source.reference, "feature/fieldlog");
  assert.equal(result.builds[0].target.toolchainLockSha256, "b".repeat(64));
  assert.equal(result.builds[0].observation.state, "succeeded");
  for (const object of [result, result.scope, result.builds, result.builds[0], result.builds[0].target,
    result.builds[0].target.source, result.builds[0].observation]) assert.equal(Object.isFrozen(object), true);
  assert.throws(() => { result.builds[0].observation.state = "failed"; }, TypeError);
});

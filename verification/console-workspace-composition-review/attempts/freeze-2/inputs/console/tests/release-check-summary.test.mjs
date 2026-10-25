import assert from "node:assert/strict";
import test from "node:test";
import { summarizeReleaseChecks } from "../src/domain/release-check-summary.ts";

const targets = [{ id: "ios-26", platform: "ios" }, { id: "android-37", platform: "android" }];
const checks = ["compatibility", "policy", "tests"];
const revision = "release-current";
const allPassing = () => targets.flatMap(target => checks.map(checkId => ({
  targetId: target.id, checkId, revision, state: "passed",
})));
const summary = reports => summarizeReleaseChecks(revision, targets, checks, reports);

test("only a complete current set passes, preserving target and check order", () => {
  const result = summary(allPassing().reverse());
  assert.equal(result.state, "passed");
  assert.deepEqual(result.targets.map(group => [group.id, group.platform, group.state]),
    [["ios-26", "ios", "passed"], ["android-37", "android", "passed"]]);
  assert.deepEqual(result.targets.map(group => group.checks.map(row => row.checkId)), [checks, checks]);
});

test("a platform failure stays visible even when another check is pending", () => {
  const reports = allPassing(); reports[1].state = "pending"; reports[5].state = "failed";
  const result = summary(reports);
  assert.equal(result.state, "failed");
  assert.equal(result.targets[0].state, "incomplete");
  assert.equal(result.targets[1].state, "failed");
  assert.equal(result.targets[1].checks[2].state, "failed");
});

test("every missing expected result remains an explicit unrun row", () => {
  const result = summary([]);
  assert.equal(result.state, "incomplete");
  assert.equal(result.targets.flatMap(group => group.checks).length, 6);
  assert.ok(result.targets.flatMap(group => group.checks).every(row =>
    row.state === "not_run" && row.reportedState === null && row.reportedRevision === null));
  for (let omitted = 0; omitted < 6; omitted++) {
    const reports = allPassing(); reports.splice(omitted, 1);
    assert.equal(summary(reports).state, "incomplete");
  }
});

test("stale passing and failing results cannot describe the selected revision", () => {
  for (const oldState of ["passed", "failed"]) {
    const reports = allPassing(); reports[0] = { ...reports[0], state: oldState, revision: "previous" };
    const result = summary(reports);
    assert.equal(result.state, "incomplete");
    assert.deepEqual(result.targets[0].checks[0], {
      checkId: "compatibility", state: "stale", reportedState: oldState, reportedRevision: "previous",
    });
  }
});

test("all 4096 combinations preserve failure precedence and incomplete states", () => {
  const states = ["passed", "failed", "pending", "not_run"];
  for (let combination = 0; combination < 4096; combination++) {
    const reports = allPassing().map((report, index) =>
      ({ ...report, state: states[(combination >> (2 * index)) & 3] }));
    const expected = reports.some(row => row.state === "failed") ? "failed" :
      reports.every(row => row.state === "passed") ? "passed" : "incomplete";
    assert.equal(summary(reports).state, expected, String(combination));
  }
});

test("duplicate, unexpected, unknown and malformed results cannot pass", () => {
  const cases = [
    [{ ...allPassing()[0], state: "success" }],
    [{ ...allPassing()[0], targetId: "other" }],
    [{ ...allPassing()[0], checkId: "other" }],
    [{ ...allPassing()[0], revision: "" }],
    [allPassing()[0], allPassing()[0]], [null], [true],
    [...allPassing(), allPassing()[0]],
  ];
  for (const reports of cases) assert.throws(() => summary(reports), TypeError);
});

test("empty, duplicate, unsupported and oversized expectation sets fail closed", () => {
  for (const args of [
    ["", targets, checks, []], [revision, [], checks, []], [revision, targets, [], []],
    [revision, [targets[0], targets[0]], checks, []],
    [revision, [{ id: "web", platform: "web" }], checks, []],
    [revision, targets, ["tests", "tests"], []], [revision, targets, [" tests"], []],
    [revision, targets, ["tests\n"], []], [revision, targets, ["x".repeat(257)], []],
    [revision, Array.from({ length: 129 }, (_, i) => ({ id: `ios-${i}`, platform: "ios" })), checks, []],
    [revision, targets, Array.from({ length: 65 }, (_, i) => `check-${i}`), []],
  ]) assert.throws(() => summarizeReleaseChecks(...args), TypeError);
});

test("result rows are immutable snapshots without caller-owned aliases", () => {
  const reports = allPassing(); const expectedTargets = targets.map(target => ({ ...target }));
  const result = summarizeReleaseChecks(revision, expectedTargets, checks, reports);
  reports[0].state = "failed"; expectedTargets[0].id = "changed";
  assert.equal(result.state, "passed"); assert.equal(result.targets[0].id, "ios-26");
  assert.equal(result.targets[0].checks[0].state, "passed");
  assert.throws(() => { result.targets[0].checks[0].state = "failed"; }, TypeError);
  assert.throws(() => { result.targets.push({}); }, TypeError);
});

test("identifiers containing separators cannot collide across target/check pairs", () => {
  const result = summarizeReleaseChecks(revision,
    [{ id: "ios/a", platform: "ios" }, { id: "ios", platform: "ios" }], ["b", "a/b"], [
      { targetId: "ios/a", checkId: "b", revision, state: "failed" },
      { targetId: "ios", checkId: "a/b", revision, state: "passed" },
    ]);
  assert.equal(result.targets[0].checks[0].state, "failed");
  assert.equal(result.targets[1].checks[1].state, "passed");
  assert.equal(result.state, "failed");
});

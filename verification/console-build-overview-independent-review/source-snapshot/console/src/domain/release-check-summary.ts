export type Platform = "ios" | "android";
export type ReportedState = "passed" | "failed" | "pending" | "not_run";
export type DisplayState = ReportedState | "stale";
export type SummaryState = "passed" | "failed" | "incomplete";

export interface ReleaseTarget {
  readonly id: string;
  readonly platform: Platform;
}

export interface ReportedCheck {
  readonly targetId: string;
  readonly checkId: string;
  readonly revision: string;
  readonly state: ReportedState;
}

export interface CheckRow {
  readonly checkId: string;
  readonly state: DisplayState;
  readonly reportedState: ReportedState | null;
  readonly reportedRevision: string | null;
}

export interface TargetSummary extends ReleaseTarget {
  readonly state: SummaryState;
  readonly checks: readonly CheckRow[];
}

export interface ReleaseCheckSummary {
  readonly revision: string;
  readonly state: SummaryState;
  readonly targets: readonly TargetSummary[];
}

const MAX_TARGETS = 128;
const MAX_CHECKS = 64;
const states: readonly string[] = ["passed", "failed", "pending", "not_run"];

function requireValid(value: boolean, reason: string): asserts value {
  if (!value) throw new TypeError(reason);
}

function identifier(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= 256 &&
    value.trim() === value && !/[\u0000-\u001f\u007f]/u.test(value);
}

function aggregate(values: readonly DisplayState[]): SummaryState {
  if (values.includes("failed")) return "failed";
  return values.every(value => value === "passed") ? "passed" : "incomplete";
}

/** Display current reported checks only. This function cannot authorize release. */
export function summarizeReleaseChecks(
  revision: string,
  expectedTargets: readonly ReleaseTarget[],
  requiredChecks: readonly string[],
  reports: readonly ReportedCheck[],
): ReleaseCheckSummary {
  requireValid(identifier(revision), "Invalid release revision");
  requireValid(Array.isArray(expectedTargets) && expectedTargets.length > 0 &&
    expectedTargets.length <= MAX_TARGETS, "Invalid expected targets");
  requireValid(Array.isArray(requiredChecks) && requiredChecks.length > 0 &&
    requiredChecks.length <= MAX_CHECKS, "Invalid required checks");
  requireValid(Array.isArray(reports) && reports.length <= expectedTargets.length * requiredChecks.length,
    "Invalid result count");

  const targets = new Map<string, Platform>();
  for (const target of expectedTargets) {
    requireValid(target !== null && typeof target === "object" && identifier(target.id) &&
      (target.platform === "ios" || target.platform === "android"), "Invalid target");
    requireValid(!targets.has(target.id), "Duplicate target");
    targets.set(target.id, target.platform);
  }
  const checks = new Set<string>();
  for (const check of requiredChecks) {
    requireValid(identifier(check) && !checks.has(check), "Invalid or duplicate required check");
    checks.add(check);
  }
  const indexed = new Map<string, Map<string, ReportedCheck>>();
  for (const report of reports) {
    requireValid(report !== null && typeof report === "object" &&
      identifier(report.targetId) && identifier(report.checkId) && identifier(report.revision) &&
      states.includes(report.state), "Invalid check result");
    requireValid(targets.has(report.targetId) && checks.has(report.checkId), "Unexpected check result");
    let group = indexed.get(report.targetId);
    if (!group) { group = new Map(); indexed.set(report.targetId, group); }
    requireValid(!group.has(report.checkId), "Duplicate check result");
    // Never retain a caller-owned mutable result object.
    group.set(report.checkId, { targetId: report.targetId, checkId: report.checkId,
      revision: report.revision, state: report.state });
  }

  const groups: TargetSummary[] = [];
  for (const [id, platform] of targets) {
    const rows: CheckRow[] = [];
    for (const checkId of checks) {
      const report = indexed.get(id)?.get(checkId);
      rows.push(Object.freeze({ checkId,
        state: report ? (report.revision === revision ? report.state : "stale") : "not_run",
        reportedState: report?.state ?? null, reportedRevision: report?.revision ?? null }));
    }
    groups.push(Object.freeze({ id, platform, state: aggregate(rows.map(row => row.state)),
      checks: Object.freeze(rows) }));
  }
  return Object.freeze({ revision, state: aggregate(groups.flatMap(group => group.checks.map(row => row.state))),
    targets: Object.freeze(groups) });
}

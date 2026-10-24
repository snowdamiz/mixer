#!/usr/bin/env python3
"""V2 private R14/R18 candidate. Default is read-only preflight, never fallback."""
import argparse
import dataclasses
import datetime
from pathlib import Path
import json
import os
import subprocess
import sys
import time

import checkpoint
import lifecycle as life

HERE = Path(__file__).resolve().parent
ROOT = checkpoint.ROOT
base = checkpoint.load_controller()
SOURCES = ("run.py", "linux_backend.py", "lifecycle.py", "role.exs", "fault_helper.c", "control_nif.c", "checkpoint.py", "signal-authority.json")
AMENDMENT = ROOT / "verification/stripe-webhook-resource-ingress-root-review/r14-r18-private-interface-amendment.json"
SIGNAL_AMENDMENT = ROOT / "verification/stripe-webhook-resource-ingress-root-review/r14-real-signal-amendment.json"


def fault_table():
    return [dataclasses.asdict(boundary) for boundary in life.BOUNDARIES]


def harness_digest():
    return base.digest({"v1Seal": checkpoint.SEAL_SHA256,
                        "sources": {name: base.sha(HERE / name) for name in SOURCES},
                        "amendmentSHA256": base.sha(AMENDMENT), "signalAmendmentSHA256": base.sha(SIGNAL_AMENDMENT)})


def check_amendment():
    m = base.load(AMENDMENT)
    base.require(m["status"] == "selected-private-v2-authoring-interface-runtime-pending"
                 and m["r14Phases"] == list(life.PHASES) and m["httpCanSelectPhaseOrFault"] is False,
                 "profile_invalid")
    for name, expected in m["bindings"].items():
        base.require(base.sha(ROOT / name) == expected, "source_mismatch")
    s = base.load(SIGNAL_AMENDMENT)
    base.require(s["status"] == "selected-private-v2-real-signal-authoring-runtime-pending"
                 and s["r14Phases"] == list(life.PHASES) and s["runtimeApproved"] is False,
                 "profile_invalid")
    for name, expected in s["bindings"].items():
        base.require(base.sha(ROOT / name) == expected, "source_mismatch")
    authority = base.load(HERE / "signal-authority.json")
    base.require(authority["schema"] == 1 and authority["runtimeVerified"] is False
                 and [(r["name"], r["sha256"]) for r in authority["sources"]] == [
                     ("elixir-1.20.4-System", "3aa3576a1f7ef24ab2cd30aa8d2d5b384e84e00542b52fd39044eb734c0beb54"),
                     ("otp-29.1.1-default-signal-handler", "f6cc636fdc1b479532042063a67b3eed9584688614e2c84a69e004dbc60853a7")],
                 "source_mismatch")


def check_review(path):
    m = base.load(path)
    fields = {"schema", "status", "harnessDigest", "profileDigest", "sourceDigest", "reviewer",
              "faultEnumDigest", "checkpointSealDigest"}
    base.require(set(m) == fields and type(m["schema"]) is int and m["schema"] == 1, "ownership")
    base.require(m["status"] == "independent-source-and-lifecycle-enum-review-approved-for-private-runtime"
                 and m["harnessDigest"] == harness_digest() and m["profileDigest"] == base.PROFILE_SHA
                 and m["sourceDigest"] == base.SOURCE_SHA and m["faultEnumDigest"] == base.digest(fault_table())
                 and m["checkpointSealDigest"] == checkpoint.SEAL_SHA256 and type(m["reviewer"]) is str
                 and 0 < len(m["reviewer"]) <= 128, "ownership")


def require_capabilities():
    env = base.linux_capabilities()
    base.require(env["linux"] and env["cgroupV2"] and env["rootLauncherAvailable"]
                 and hasattr(os, "pidfd_open") and hasattr(signal_module(), "pidfd_send_signal"),
                 "capability_unavailable", True)
    base.core_policy()
    return env


def signal_module():
    import signal
    return signal


def validate_release(path):
    manifest, release_digest = base.release_manifest(path)
    version = subprocess.run(["/usr/bin/cc", "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, env=base.FIXED_ENV, timeout=10)
    base.require(version.returncode == 0 and not version.stderr
                 and version.stdout.decode("ascii").splitlines()[0] == manifest["compiler"], "source_mismatch")
    return manifest, release_digest


def output_directory(path):
    output = Path(path).absolute()
    base.require(output.is_relative_to(HERE / "results") and output == output.resolve()
                 and not output.exists() and all(not p.is_symlink() for p in (output, *output.parents)), "ownership")
    return output


def execute_row(case, args, profile, environment, release_digest, suite_start):
    # Imported only after the outer exact Linux/source/review gate.
    from linux_backend import LinuxBackend
    row = base.receipt(case, environment, release_digest, "failed", "runtime_error")
    started = row["startedMonotonicNs"]
    budget = life.Budget(suite_start, started)
    backend = LinuxBackend(args.delegated_cgroup, args.release, profile, harness_digest(), {
        "profile": lambda: base.profile(args.profile), "sources": lambda: base.source_inputs(),
        "capabilities": require_capabilities, "release": lambda: validate_release(args.release),
        "review": lambda: check_review(args.review)})
    try:
        checks = life.run_r14(backend, budget) if case == "R14" else life.run_r18(backend, budget)
        budget.check()
        row.update(status="passed", reason="completed")
        row["termination"]["observedSubcases"] = checks
    except base.Refusal as error:
        row.update(status="unavailable" if error.unavailable else "failed", reason=error.reason)
    except (life.Unavailable, OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError):
        row.update(status="unavailable", reason="capability_unavailable")
    finally:
        # The runner always calls non-injectable cleanup. Preserve any partial
        # failure state and never convert an incomplete disposal into a pass.
        active = backend.active
        if active is not None and not active.cleaned:
            try:
                active.cleanup(budget)
            except (life.Unavailable, base.Refusal, OSError, ValueError, subprocess.SubprocessError):
                row.update(status="failed", reason="cleanup")
        if active is not None and active.failed:
            row.update(status="failed", reason=active.error_reason if active.error_reason != "completed" else "cleanup")
        history = backend.history
        row["cgroupBefore"] = {"runs": [r["cgroupBefore"] for r in history]}
        row["cgroupAfter"] = {"runs": [r["cgroupAfter"] for r in history]}
        row["samples"] = sorted([s for r in history for s in r["samples"]], key=lambda s: s["monotonicNs"])
        row["termination"]["runs"] = [{"phase": r["phase"], "selectedStage": r["selectedStage"],
            **r["termination"], "exitCode": r["exitCode"], "signal": r["signal"]} for r in history]
        row["outputAudit"] = {"runs": [r["outputAudit"] for r in history], "compilerCommands": backend.commands}
        row["outputAudit"].update(allowedSchemaCount=sum(s.audit.allowed for s in backend.sessions),
                                  rejectedOutputCount=sum(s.audit.rejected for s in backend.sessions),
                                  stdoutBytes=backend.output_totals["stdout"], stderrBytes=backend.output_totals["stderr"],
                                  sentinelMatches={key: any(s.audit.receipt()["sentinelMatches"][key] for s in backend.sessions)
                                                   for key in ("body", "signature", "trailer")})
        row["cleanup"] = {"complete": active is None or active.cleaned, "runtimeSessions": len(history),
            "runtimeSessionsAttempted": len(backend.sessions), "launcherStarts": sum(s.proc is not None for s in backend.sessions),
            "roleReadinessObserved": sum(bool(s.channel and s.channel.ready) for s in backend.sessions),
            "runs": [r["cleanup"] for r in history], "controllerOutsideCgroup": True}
        if active is not None and not active.cleaned:
            row["cleanup"].update(remainingOwnedCgroup=str(active.cg.path) if active.cg and active.cg.path.exists() else None,
                                  remainingOwnedScratch=str(active.scratch) if active.scratch and active.scratch.exists() else None,
                                  partialBoundaries=active.boundaries, knownNamespaceIds=sorted(active.namespace_ids),
                                  knownDescriptorInodes=sorted(active.descriptor_inodes), observedHolderCounts=active.last_counts,
                                  partialOutputAudit=active.audit.receipt())
        row["elapsedNs"] = time.monotonic_ns() - started
        if row["elapsedNs"] > life.ROW_WALL_NS:
            row.update(status="failed", reason="deadline")
    return row


def main():
    suite_started = time.monotonic_ns()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=base.CONTRACT / "profile.json")
    parser.add_argument("--delegated-cgroup", type=Path)
    parser.add_argument("--release", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = output_directory(args.output)
    output.mkdir(parents=True, mode=0o700)
    environment = base.linux_capabilities()
    environment.update(v2ProfileDigest=base.PROFILE_SHA, v1CheckpointSealDigest=checkpoint.SEAL_SHA256,
                       v2FaultEnumDigest=base.digest(fault_table()), v2HarnessDigest=harness_digest(),
                       rolePhases=list(life.PHASES))
    rows, release_digest = [], ""
    try:
        check_amendment()
        profile = base.profile(args.profile)
        base.source_inputs()
        require_capabilities()
        base.require(args.release is not None and args.delegated_cgroup is not None, "capability_unavailable", True)
        args.release = args.release.absolute()
        _, release_digest = validate_release(args.release)
        base.ancestors(args.delegated_cgroup, profile)
        base.require(args.execute, "capability_unavailable", True)
        base.require(args.review is not None, "ownership")
        check_review(args.review)
        for case in base.CASES:
            rows.append(execute_row(case, args, profile, environment, release_digest, suite_started)
                        if case in ("R14", "R18") else base.receipt(case, environment, release_digest))
    except base.Refusal as error:
        rows = [base.receipt(case, environment, release_digest,
                            "unavailable" if error.unavailable else "failed", error.reason) for case in base.CASES]
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError):
        rows = [base.receipt(case, environment, release_digest, "failed", "runtime_error") for case in base.CASES]
    for row in rows:
        (output / (row["caseId"] + ".json")).write_bytes(base.canonical(row) + b"\n")
    counts = {status: sum(row["status"] == status for row in rows) for status in ("passed", "failed", "unavailable")}
    summary = {"schema": 1, "status": "failed" if counts["failed"] else "unavailable",
               "counts": counts, "environment": environment, "harnessDigest": harness_digest(),
               "runtimeRowsExecuted": sum(bool(r["cleanup"].get("launcherStarts")) for r in rows),
               "scope": "R14/R18 candidate only; other matrix rows forced unavailable",
               "faultEnumReview": "required-before-runtime", "LinuxCompileAndRuntimeAccepted": False,
               "gaAccepted": False, "implementationComplete": False}
    (output / "summary.json").write_bytes(base.canonical(summary) + b"\n")
    print(json.dumps({k: summary[k] for k in ("status", "counts", "runtimeRowsExecuted")}, sort_keys=True))
    return 1 if counts["failed"] else 78


if __name__ == "__main__":
    try:
        sys.exit(main())
    except base.Refusal as error:
        print(json.dumps({"schema": 1, "status": "failed", "reason": error.reason}))
        sys.exit(1)

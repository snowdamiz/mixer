#!/usr/bin/env python3
"""One 256/64M/60s trial; one 256/128M/60s trial only after clean CacheWork exhaustion.

check is pure source/data work. run is restricted to the selected remote CI lane.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
V1 = HERE.parent / "swift-cache-capacity-campaign-v1"
REVIEW = HERE.parent / "github-delivery-blocker-campaign/cache-campaign-review"
V1_DRIVER_SHA = "5266e70df6e79054ffdc1abfc64b300d9f6252f11e55eb340716ab346bc4c556"
REVIEW_SEAL_SHA = "4dcf3f8bf9533d0234a5966d111b1d3373299cbfb816ab871d0764c0a1024cec"
if hashlib.sha256((V1 / "campaign.py").read_bytes()).hexdigest() != V1_DRIVER_SHA:
    raise RuntimeError("frozen v1 helper changed")
spec = importlib.util.spec_from_file_location("capacity_campaign_v1", V1 / "campaign.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
require, save, sha = base.require, base.save, base.sha

PROFILES = (("deadline-60-work-64m", 64_000_000), ("deadline-60-work-128m", 128_000_000))
DEADLINE_FILES = ("src/experimental_swift_reactor/control.rs", "src/experimental_wasi/mod.rs")
CAMPAIGN_SECONDS = 540
FULL_SECONDS = 200
MAX_FULL_ATTEMPTS = 2
RSS_LIMITATION = "Raw wait4 value retained; prior campaign showed a common launcher high-water floor. VM-attributable RSS unavailable; no per-profile RSS comparison."
NEXT_ARCHITECTURE = "If both-corpus-plus-cleanup milestone remains unmet, require Astra architecture comparison of algorithm change, resource-policy change and a different implementation; no further accounting-only preparation chain."


def inputs():
    bindings = json.loads((HERE / "bindings.json").read_text())
    for name, row in bindings.items():
        data = (ROOT / name).read_bytes()
        require(len(data) == row["bytes"] and sha(data) == row["sha256"], "bound input changed: " + name)
    require(sha((REVIEW / "seal.json").read_bytes()) == REVIEW_SEAL_SHA, "prior review seal changed")
    seal = json.loads((REVIEW / "seal.json").read_text())
    for name in ("REVIEW.md", "verified-results.json"):
        require(sha((REVIEW / name).read_bytes()) == seal["files"][name]["sha256"], "prior review binding changed")
    reviewed = json.loads((REVIEW / "verified-results.json").read_text())
    require(reviewed["fullAttempts"] == 4 and reviewed["hostFeasibilityProfiles"] == 0
            and reviewed["allConsumingCleanupAndOwnedGroupChecksPassed"], "prior campaign decision changed")
    source, artifact, _ = base.inputs()
    return source, artifact, bindings


def parameterize(original, work):
    require(work in (64_000_000, 128_000_000), "unsupported v2 profile")
    source = base.parameterize(original, 256, work)
    # Both contexts receive the original single started Instant from the unchanged
    # harness. No per-call reset, changed clock origin, or new profile loader.
    for name in DEADLINE_FILES:
        source[name] = base.replace(source[name].decode(), "deadline_ms: 30_000,", "deadline_ms: 60_000,").encode()
    return source


def event(result, name):
    values = [e["payload"] for e in result["events"] if e["event"] == name]
    require(len(values) == 1, "missing or duplicate event: " + name)
    return values[0]


def historical():
    return base.classify(base.INPUTS / "historical-attribution.stdout",
                         {"exitCode": 101, "timedOut": False, "processGroupEmpty": True})


def expected_bounds(work):
    old = historical()
    bounds = {name: event(old, name) for name in ("validation_budget", "run_budget", "wasi_budget", "wasi_grants")}
    bounds["run_budget"] |= {"cache_entries": 256, "cache_work": work, "deadline_ms": 60_000}
    bounds["wasi_budget"] |= {"deadline_ms": 60_000}
    return bounds


def validate_result(result, full, work):
    expected = expected_bounds(work)
    actual = {name: event(result, name) for name in expected}
    # Python considers True == 1; retain the emitted scalar types as well as values.
    require(actual == expected and all(type(actual[name][key]) is type(value)
        for name, fields in expected.items() for key, value in fields.items()),
        "actual budgets/grants differ from selected complete bounds")
    result["actualBounds"] = actual
    first = result["firstFailure"]
    final = event(result, "final_failure")
    preserved = (final is None if first is None else
                 type(final) is dict and (final | {"after_cleanup": None}) == first["payload"])
    result["originalFinalFailurePreserved"] = preserved
    require(preserved, "original first failure not preserved through consuming cleanup")
    require(result["consumingCleanup"] and event(result, "cleanup_reservations_and_live_empty") is True,
            "consuming cleanup unresolved; stop resource reuse")
    require(event(result, "cleanup_empty") is (first is None), "cleanup success/failure semantics changed")
    require(result["telemetry"]["status"] == "valid", "invalid attribution; stop comparison")
    require(full["processGroupEmpty"] and not full["timedOut"] and full.get("cancelled") is None,
            "external timeout/cancellation or unresolved owned group")
    require(full["exitCode"] == (0 if result["hostFeasibility"] else 101), "unexpected full target exit")


def conditional_second(result, full, unchanged):
    """Fail closed: no second attempt for fuel/deadline/invariant/other failures."""
    failure = result.get("firstFailure") or {}
    payload = failure.get("payload") or {}
    return bool(unchanged and result.get("consumingCleanup") and result.get("originalFinalFailurePreserved")
        and result.get("telemetry", {}).get("status") == "valid" and not result.get("complete")
        and not result.get("hostFeasibility") and full.get("exitCode") == 101
        and full.get("processGroupEmpty") and not full.get("timedOut") and not full.get("cancelled")
        and failure.get("event") == "runtime_failure" and payload.get("kind") == "WorkExhausted"
        and payload.get("code") == "swift_run_work" and payload.get("resource") == "CacheWork"
        and payload.get("limit") == 64_000_000 and payload.get("attempted") == 64_000_001
        and payload.get("at_failure", {}).get("cache_work") == 64_000_000
        and result.get("actualBounds") == expected_bounds(64_000_000))


def check(output):
    original, artifact, bindings = inputs()
    parent = base.parameterize(original, 256, 64_000_000)
    parent_record, _ = base.source_record(original, parent)
    require(parent_record["sha256"] == "204c62d871b05b4b50a6fb7e55ed4251f3c5b664299f7bd410fbdee05e32f05c", "reviewed capacity-256 source changed")
    rows = []
    for name, work in PROFILES:
        source = parameterize(original, work)
        record, delta = base.source_record(parent, source)
        save(output / name / "source.json", record)
        (output / name / "delta-from-reviewed-256.patch").write_text(delta)
        rows.append({"name": name, "sourceSHA256": record["sha256"], "bounds": expected_bounds(work)})
    result = {"schema": 2, "profiles": rows, "inputBindings": bindings, "priorReviewSealSHA256": REVIEW_SEAL_SHA,
              "artifact": {"bytes": len(artifact), "sha256": sha(artifact)}, "maxFullAttempts": MAX_FULL_ATTEMPTS,
              "aggregateDriverSeconds": CAMPAIGN_SECONDS, "fullTargetSeconds": FULL_SECONDS,
              "execution": "pure source/data checks only; compilation and full workload pending"}
    save(output / "check.json", result)
    return result


def run_profile(name, work, original, target_input, scratch, env, output, campaign):
    phase = output / name
    phase.mkdir()
    source = parameterize(original, work)
    record, diff = base.source_record(base.parameterize(original, 256, 64_000_000), source)
    save(phase / "source.json", record)
    (phase / "delta-from-reviewed-256.patch").write_text(diff)
    save(phase / "selected-bounds.json", expected_bounds(work))
    crate = scratch / name / "vm"
    base.materialize(source, crate)
    child_env = env | {"CARGO_TARGET_DIR": str(scratch / name / "target")}
    build = base.command(["cargo", "test", "--lib", "--no-run", "--release", "--locked", "--offline",
        "--no-default-features", "--features", "experimental-swift-reactor", "--message-format=json"],
        crate, child_env, phase / "build", 180)
    require(build["exitCode"] == 0 and not build["timedOut"], "compile failed: " + name)
    candidates = [json.loads(line)["executable"] for line in (phase / "build/stdout").read_text().splitlines()
        if line.startswith("{") and json.loads(line).get("reason") == "compiler-artifact" and json.loads(line).get("executable")]
    require(len(candidates) == 1, "one test executable required")
    binary = Path(candidates[0])
    executable = {"path": str(binary), "bytes": binary.stat().st_size, "sha256": sha(binary.read_bytes())}
    save(phase / "binary.json", executable)
    for label, test in (("finite", "::campaign_"), ("harness-control", base.PREFIX + "exact_reactor_harness_control")):
        control = base.command([str(binary), test, "--nocapture", "--test-threads=1"], crate, child_env, phase / label, 90)
        require(control["exitCode"] == 0 and not control["timedOut"], "finite control failed: " + label)
        require(("test result: ok. 4 passed; 0 failed; 0 ignored" if label == "finite" else
                 "test result: ok. 1 passed; 0 failed; 0 ignored") in (phase / label / "stdout").read_text(), "missing selected controls")
    require(campaign["fullAttempts"] < MAX_FULL_ATTEMPTS, "full attempt cap")
    base.ensure_command_budget(FULL_SECONDS)
    campaign["fullAttempts"] += 1
    save(output / "campaign.json", campaign)  # Count before spawning; no refund/retry.
    full = base.command([str(binary), base.PREFIX + "exact_reactor_target_once", "--exact", "--nocapture", "--test-threads=1"],
                        crate, child_env, phase / "full", FULL_SECONDS)
    result = base.classify(phase / "full/stdout", full)
    save(phase / "result.json", result)  # Preserve first failure even when further checks reject it.
    unchanged = all((crate / n).read_bytes() == b for n, b in source.items()) and sha(target_input.read_bytes()) == base.ARTIFACT_HASH
    validate_result(result, full, work)
    save(phase / "result.json", result)
    row = {"name": name, "residents": 256, "cacheWork": work, "sourceSHA256": record["sha256"],
        "binary": executable, "actualBounds": result["actualBounds"], "result": str((phase / "result.json").relative_to(output)),
        "hostFeasibility": result["hostFeasibility"], "consumingCleanup": result["consumingCleanup"],
        "originalFinalFailurePreserved": result["originalFinalFailurePreserved"], "sourceAndInputUnchanged": unchanged,
        "firstFailure": result["firstFailure"], "timing": {k: full[k] for k in ("wallSeconds", "userSeconds", "systemSeconds", "peakRSSBytes")},
        "peakRSSAvailableForVMComparison": False, "rssLimitation": RSS_LIMITATION}
    campaign["profiles"].append(row)
    save(output / "campaign.json", campaign)
    require(unchanged, "source/input changed during experiment")
    shutil.rmtree(scratch / name)  # base.command has already required every owned group absent.
    return result, full, unchanged


def run(output):
    require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1" and platform.system() == "Linux",
        "requires first-attempt GitHub-hosted Linux CI; local execution and rerun remain held")
    require(not output.exists(), "fresh campaign output required; no retries/resume")
    base.COMMAND_DEADLINE = time.monotonic() + CAMPAIGN_SECONDS
    base.CANCEL_REQUESTED = None
    signal.signal(signal.SIGTERM, base.request_cancel)
    signal.signal(signal.SIGINT, base.request_cancel)
    output.mkdir(parents=True)
    scratch = output / "scratch"
    campaign = {"schema": 2, "model": "gpt-6-astra", "reasoningEffort": "xhigh",
        "githubSHA": os.environ.get("GITHUB_SHA"), "githubRunId": os.environ.get("GITHUB_RUN_ID"),
        "githubRunAttempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "environment": " ".join(os.uname()),
        "profiles": [], "maxFullAttempts": MAX_FULL_ATTEMPTS, "fullAttempts": 0,
        "aggregateDeadlineSeconds": CAMPAIGN_SECONDS, "priorReviewSealSHA256": REVIEW_SEAL_SHA,
        "milestone": "Both full corpus calls on one initialized owner match all 11 original native fields, followed by consuming zero-resource cleanup.",
        "scope": "diagnostic host/profile feasibility; native/public/signed OTA/FieldLog publication/GA pending",
        "rssLimitation": RSS_LIMITATION, "nextArchitectureIfMilestoneUnmet": NEXT_ARCHITECTURE}
    safe_to_remove = True
    try:
        original, artifact, bindings = inputs()
        campaign["inputBindings"] = bindings
        check(output / "preflight")
        scratch.mkdir()
        target_input = scratch / "fieldlog-reactor.wasm"
        target_input.write_bytes(artifact)
        del artifact
        env = {k: os.environ[k] for k in ("HOME", "PATH", "RUSTUP_HOME", "CARGO_HOME", "LANG") if k in os.environ}
        env.update(CARGO_INCREMENTAL="0", CARGO_NET_OFFLINE="true", CARGO_BUILD_JOBS="2", RUSTUP_TOOLCHAIN="1.99.0",
                   MIXER_EXACT_REACTOR_INPUT=str(target_input), TMPDIR=str(scratch))
        for tool, argv in (("rustc", ["rustc", "-vV"]), ("cargo", ["cargo", "-V"]), ("python", [sys.executable, "--version"])):
            row = base.command(argv, HERE, env, output / "tools" / tool, 15)
            require(row["exitCode"] == 0 and not row["timedOut"], "tool identity failed")
        result, full, unchanged = run_profile(*PROFILES[0], original, target_input, scratch, env, output, campaign)
        selected = conditional_second(result, full, unchanged)
        campaign["conditionalSecondSelected"] = selected
        campaign["conditionalSecondReason"] = ("verified CacheWork exhaustion with original cause and complete cleanup" if selected else
            "first attempt completed or hit another limit; conditional work increase not authorized")
        save(output / "campaign.json", campaign)
        if selected:
            result, full, unchanged = run_profile(*PROFILES[1], original, target_input, scratch, env, output, campaign)
        campaign["status"] = "host-feasibility-observed" if result["hostFeasibility"] else "milestone-unmet-campaign-closed"
        campaign["nextDecision"] = ("root reviews the completed host/profile result and selects concrete integration; no production default promotion" if result["hostFeasibility"] else NEXT_ARCHITECTURE)
    except Exception as error:
        campaign["status"] = "stopped"
        campaign["error"] = str(error)
        safe_to_remove = "process group unresolved" not in str(error)
        raise
    finally:
        if safe_to_remove and scratch.exists():
            shutil.rmtree(scratch)
        campaign["cleanup"] = {"ownedScratchRemoved": not scratch.exists(), "nativeOrLocalCustodyProcessesStarted": False}
        save(output / "campaign.json", campaign)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "run"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    (check if args.action == "check" else run)(args.output.resolve())

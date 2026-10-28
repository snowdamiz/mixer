#!/usr/bin/env python3
"""Offline source, artifact and observed-result verification; executes no guest."""
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CANDIDATE = REPO / "verification/swift-cache-capacity-campaign-v1"
ARTIFACT = HERE / "artifact"
EXPECTED_HEAD = "cc350d3303ca71c5d57e87846f6a61304b658fa7"
started = time.monotonic()


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


pins = read(REPO / "verification/swift-cache-capacity-campaign-independent/receipt.json")
for name, row in pins["candidatePins"].items():
    assert sha(CANDIDATE / name) == row["sha256"], name
spec = importlib.util.spec_from_file_location("reviewed_campaign", CANDIDATE / "campaign.py")
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)
original, original_artifact, bindings = campaign.inputs()
run = read(ARTIFACT / "campaign.json")
assert run["githubSHA"] == EXPECTED_HEAD
assert run["githubRunId"] == "40740382537" and run["githubRunAttempt"] == "1"
assert run["fullAttempts"] == 4 and len(run["profiles"]) == 4
assert run["status"] == "primary-comparison-complete"
assert run["inputBindings"] == bindings
assert run["cleanup"] == {"nativeOrLocalCustodyProcessesStarted": False, "ownedScratchRemoved": True}
assert not (ARTIFACT / "scratch").exists()
assert run["machine"] == "x86_64" and run["environment"].startswith("Linux-")
assert read(ARTIFACT / "preflight/check.json")["inputBindings"] == bindings

receipts = []
for path in sorted(ARTIFACT.glob("**/receipt.json")):
    row = read(path)
    begin = read(path.parent / "started.json")
    assert all(row[key] == value for key, value in begin.items()), str(path)
    assert sha(path.parent / "stdout") == row["stdoutSHA256"]
    assert sha(path.parent / "stderr") == row["stderrSHA256"]
    assert row["processGroupEmpty"] and not row["timedOut"] and row["cancelled"] is None
    assert row["signals"] == []
    assert row["wallSeconds"] < row["timeoutSeconds"] + row["cleanupSeconds"]
    assert row["exitCode"] == (101 if path.parent.name == "full" else 0)
    receipts.append({"path": str(path.relative_to(ARTIFACT)), **row})
assert len(receipts) == 19

tools = {name: (ARTIFACT / "tools" / name / "stdout").read_text().strip() for name in ("rustc", "cargo", "python")}
assert tools["rustc"].startswith("rustc 1.99.0 (b940084d7 2026-09-28)")
assert "host: x86_64-unknown-linux-gnu" in tools["rustc"]
assert tools["cargo"].startswith("cargo 1.99.0")
assert "Ran 9 tests" in (HERE / "job-log.sanitized.txt").read_text()

history = campaign.classify(CANDIDATE / "inputs/historical-attribution.stdout", {"exitCode": 101, "timedOut": False, "processGroupEmpty": True})
summary = []
base_budget = None
base_validation = None
base_wasi = None
base_grants = None
expected_tests = ("campaign_budget_geometry_and_reservations", "campaign_full_chain_cycle_and_high_link",
                  "campaign_original_failure_atomicity_and_allocation_controls", "campaign_retention_churn_and_pin_bound")
for observed, (name, n, work) in zip(run["profiles"], campaign.PRIMARY, strict=True):
    assert (observed["name"], observed["residents"], observed["cacheWork"]) == (name, n, work)
    source, diff = campaign.source_record(original, campaign.parameterize(original, n, work))
    assert source == read(ARTIFACT / name / "source.json") == read(ARTIFACT / "preflight" / name / "source.json")
    assert source["sha256"] == observed["sourceSHA256"]
    assert diff == (ARTIFACT / name / "changes.patch").read_text()
    assert observed["sourceAndInputUnchanged"]
    finite = (ARTIFACT / name / "finite/stdout").read_text()
    assert all(f"cache_tests::{test} ..." in finite for test in expected_tests)
    assert "test result: ok. 4 passed; 0 failed; 0 ignored" in finite
    assert f"full_chain={n} high_link={n} cycle_and_invalid_link_fail_closed=true" in finite
    assert f"index_cells={128+n} index_bytes={2*(128+n)} cycle_bytes={n//8} plan_bytes={n} tickets={n+22}" in finite
    assert "PLAN_PROFILE cleanup_zero=true guest_instructions=0 initializes=0 invokes=0" in finite
    harness = (ARTIFACT / name / "harness-control/stdout").read_text()
    assert "exact_reactor_harness_control ..." in harness
    assert "test result: ok. 1 passed; 0 failed; 0 ignored" in harness
    full = read(ARTIFACT / name / "full/receipt.json")
    build = read(ARTIFACT / name / "build/receipt.json")
    artifacts = [json.loads(line) for line in (ARTIFACT / name / "build/stdout").read_text().splitlines() if line.startswith("{")]
    executables = [row["executable"] for row in artifacts if row.get("reason") == "compiler-artifact" and row.get("executable")]
    assert executables == [full["argv"][0]]
    assert all(read(ARTIFACT / name / label / "receipt.json")["argv"][0] == executables[0] for label in ("finite", "harness-control"))
    assert full["argv"][1:] == [campaign.PREFIX + "exact_reactor_target_once", "--exact", "--nocapture", "--test-threads=1"]
    assert full["environment"]["RUSTUP_TOOLCHAIN"] == "1.99.0"
    result = campaign.classify(ARTIFACT / name / "full/stdout", full)
    assert result == read(ARTIFACT / name / "result.json")
    assert result["telemetry"]["status"] == "valid" and not result["telemetry"]["issues"]
    assert not result["complete"] and not result["hostFeasibility"]
    assert result["nativeEqualPhases"] == result["completeGuestObservations"] == []
    assert result["phaseOrder"] == ["validation", "initialize", "corpus_1"]
    assert result["consumingCleanup"] and observed["consumingCleanup"]
    def one(event):
        rows = [e["payload"] for e in result["events"] if e["event"] == event]
        assert len(rows) == 1, event
        return rows[0]
    assert one("cleanup_empty") is False and one("cleanup_reservations_and_live_empty") is True
    final_failure = one("final_failure")
    first_failure = result["firstFailure"]["payload"]
    for key in ("kind", "code", "stage", "resource", "attempted", "limit", "function", "offset", "at_failure"):
        assert final_failure[key] == first_failure[key], key
    clean = one("final_cleanup_usage")
    assert clean["cleanup_invariant"] is None and clean["reservations"]["live_tickets"] == 0
    assert all(row["current"] == 0 for row in clean["reservations"].values() if type(row) is dict)
    assert all(row["current"] == 0 for row in clean["live"].values())
    budget = one("run_budget")
    assert (budget["cache_entries"], budget["cache_work"], budget["active_pins"]) == (n, work, 64)
    normalized_budget = budget | {"cache_entries": 64, "cache_work": 64_000_000}
    if base_budget is None:
        base_budget = normalized_budget
        base_validation, base_wasi, base_grants = one("validation_budget"), one("wasi_budget"), one("wasi_grants")
    assert normalized_budget == base_budget
    assert (one("validation_budget"), one("wasi_budget"), one("wasi_grants")) == (base_validation, base_wasi, base_grants)
    initialization = one("initialize")
    assert initialization["usage"]["instructions"] == 37_328 and initialization["lifecycle"] == "Ready"
    assert initialization["stdout"] == initialization["stderr"] == ""
    failure = result["firstFailure"]["payload"]
    phase = one("corpus_1")
    final_attr = result["telemetry"]["snapshots"][-1]["payload"]
    assert all(s["reset_count"] == 1 for s in result["telemetry"]["snapshots"])
    assert final_attr["distinct"] == 485
    if name == "baseline":
        assert failure["attempted"] == 64_000_001 and failure["limit"] == 64_000_000
        assert failure["at_failure"]["instructions"] == 23_358_291
        assert final_attr == history["telemetry"]["snapshots"][-1]["payload"]
    credits = final_attr["credits"]
    summary.append({"name": name, "residents": n, "cacheWorkAllowance": work,
        "firstFailureKind": failure["kind"], "firstFailureResource": failure["resource"],
        "instructionsAtFailure": failure["at_failure"]["instructions"], "cacheWorkAtFailure": failure["at_failure"]["cache_work"],
        "runElapsedMicrosAtFailure": failure["at_failure"]["elapsed_micros"],
        "initializeComplete": True, "corpus1Complete": False, "corpus2": "unrun after first failure",
        "fullExitCode": full["exitCode"], "finiteTestsPassed": 4, "originalHarnessControlsPassed": 1,
        "consumingCleanup": True, "processGroupEmpty": True, "sourceAndInputUnchanged": True,
        "originalCleanupEmptyFlag": False, "originalFinalFailurePreserved": True,
        "cache": phase["cache"], "logicalReservations": phase["usage"]["reservations"],
        "initializeUsage": initialization["usage"], "initializeCache": initialization["cache"],
        "attribution": final_attr, "groupedCredits": {"freePinProbe": credits[2], "residentHashChain": credits[3],
            "emptyVictimPlanScans": sum(credits[8:11]), "repeatedScan": final_attr["scan_credits"][1],
            "repeatedBuild": final_attr["build_credits"][1]},
        "reportedTiming": observed["timing"], "binaryIdentityReported": observed["binary"],
        "sourceSHA256": source["sha256"]})

small_peaks = {row["peakRSSBytes"] for row in receipts if "/build/" not in row["path"]}
assert len(small_peaks) == 1
record = {"schema": 1, "reviewerModel": "gpt-6-astra", "reasoningEffort": "xhigh",
    "command": "python3 -B verification/github-delivery-blocker-campaign/cache-campaign-review/verify_results.py",
    "python": sys.version, "reviewPlatform": platform.platform(), "reviewSeconds": time.monotonic() - started,
    "runId": 40740382537, "head": EXPECTED_HEAD, "runAttempt": 1,
    "sourceManifestAndInputBindingsVerified": True, "rawOutputHashesVerified": True,
    "rawClassifierReplayMatchesAllFourResults": True, "commandReceiptsVerified": len(receipts),
    "remotePureTestsPassed": 9, "remoteFiniteTestsPassed": 16, "originalHarnessControlsPassed": 4,
    "fullAttempts": 4, "hostFeasibilityProfiles": 0, "fifthSelectedOrRun": False,
    "allConsumingCleanupAndOwnedGroupChecksPassed": True, "ownedScratchRemoved": True,
    "freshBaselineMatchesHistoricalFullAttributionCounters": True,
    "tools": tools, "profiles": summary,
    "rssLimitation": {"commonReportedPeakRSSBytes": next(iter(small_peaks)),
        "alsoPresentFor": ["rustc -vV", "cargo -V", "python --version", "finite tests", "synthetic harness controls", "all four full attempts"],
        "interpretation": "common launcher/process high-water floor; VM-attributable peak RSS cannot be isolated from these receipts; no memory-speedup claim"},
    "binaryLimitation": "executed binary hashes and compiler-output paths are bound by receipts; binaries were removed remotely and are not available for an independent local rehash",
    "holds": "no local compiler, guest, native/UI/capture, PID/custody or global inventory probe; no dispatch, retry or canonical edit"}
(HERE / "verified-results.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
print(json.dumps({key: record[key] for key in ("commandReceiptsVerified", "remotePureTestsPassed", "remoteFiniteTestsPassed", "originalHarnessControlsPassed", "fullAttempts", "hostFeasibilityProfiles", "allConsumingCleanupAndOwnedGroupChecksPassed", "reviewSeconds")}, indent=2))

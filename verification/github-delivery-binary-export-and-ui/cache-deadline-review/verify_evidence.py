#!/usr/bin/env python3
"""Independent, offline evidence joins. Never imports or executes campaign code."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ART = HERE / "artifact"
PACKET = ROOT / "verification/swift-cache-deadline-campaign-v2-finite-correction"
HEAD = "56ff14c925168284761c5aca4f0bd4129cf3c995"
TREE = "75989099938ed5256c4144cbc9e62979ee323183"
SEAL = "d6bf688b0b1333bb10a5c946c14febedbbdac463a884d446da9f5460b66ebdde"
DRIVER = "77ab5079e7e818d551b3c77f7b56b15babdb1dea521151a80643e9fad259763c"
PROFILES = [
    ("deadline-60-work-64m", 64_000_000, "c68fb260b6e282f4c6245ad074d01978d17aa79a155d3688654a0585d711e3d7"),
    ("deadline-60-work-128m", 128_000_000, "fe4e9bd1b05938988c858ec228d95f54f93e662f07d5426c440743bcb9a16c87"),
]
checks = []


def check(value, message):
    if not value:
        raise AssertionError(message)
    checks.append(message)


def pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def parse(text):
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def read(path):
    return parse(path.read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bound(path, item, label):
    data = path.read_bytes()
    check(len(data) == item["bytes"] and sha(data) == item["sha256"], label)


def typed_equal(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(typed_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def raw_events(path, prefix):
    result = []
    for line in path.read_text().splitlines():
        at = line.find(prefix)
        if at >= 0:
            result.append(parse(line[at + len(prefix):]))
    return result


def event(events, name):
    found = [e["payload"] for e in events if e["event"] == name]
    check(len(found) == 1, "one original event: " + name)
    return found[0]


def zero_resources(usage):
    return (usage["cleanup_invariant"] is None
            and usage["reservations"]["live_tickets"] == 0
            and all(v["current"] == 0 for v in usage["reservations"].values() if type(v) is dict)
            and all(v["current"] == 0 for v in usage["live"].values()))


run = read(HERE / "run-metadata.json")
jobs = read(HERE / "job-metadata.json")["jobs"]
artifact = read(HERE / "artifact-metadata.json")["artifacts"]
campaign = read(ART / "campaign.json")
check((run["id"], run["head_sha"], run["head_commit"]["tree_id"], run["run_attempt"], run["event"], run["status"], run["conclusion"])
      == (40755988137, HEAD, TREE, 1, "workflow_dispatch", "completed", "success"), "selected first-attempt dispatch identity")
check(len(jobs) == 1 and jobs[0]["id"] == 123054909834 and jobs[0]["conclusion"] == "success"
      and all(s["conclusion"] == "success" for s in jobs[0]["steps"]), "single completed comparison job")
check(len(artifact) == 1 and artifact[0]["id"] == 12845123804 and not artifact[0]["expired"], "single retained artifact identity")
bound(HERE / "artifact.zip", {"bytes": artifact[0]["size_in_bytes"], "sha256": artifact[0]["digest"].removeprefix("sha256:")}, "archive digest and byte length join GitHub")
extraction = read(HERE / "extraction.json")
check(extraction["fileCount"] == 61 and extraction["expandedBytes"] == 345946, "bounded 61-file archive inventory")
for item in extraction["files"]:
    bound(ART / item["path"], item, "raw retained artifact: " + item["path"])
check(campaign["githubSHA"] == HEAD and campaign["githubRunId"] == str(run["id"]) and campaign["githubRunAttempt"] == "1", "artifact to workflow identity join")
check(sha((PACKET / "seal.json").read_bytes()) == SEAL, "selected finite correction seal remains frozen")
seal = read(PACKET / "seal.json")
check(len(seal["files"]) == 18, "all 18 selected correction files named")
for name, item in seal["files"].items():
    bound(PACKET / name, item, "selected correction byte binding: " + name)
check(sha((PACKET / "campaign.py").read_bytes()) == DRIVER, "selected driver hash")
for name in ("verification/swift-cache-deadline-campaign-v2-finite-correction/campaign.py", ".github/workflows/swift-cache-deadline-campaign-v2.yml"):
    committed = subprocess.run(["git", "show", HEAD + ":" + name], cwd=ROOT, check=True, capture_output=True).stdout
    check(committed == (ROOT / name).read_bytes(), "selected Git object matches reviewed source: " + name)
check(subprocess.run(["git", "rev-parse", HEAD + "^{tree}"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip() == TREE, "local selected commit tree matches remote")
check((ROOT / ".github/workflows/swift-cache-deadline-campaign-v2.yml").read_bytes() == (PACKET / "workflow.yml").read_bytes(), "selected workflow byte identity")
bindings = read(PACKET / "bindings.json")
check(typed_equal(campaign["inputBindings"], bindings), "actual input bindings match selected packet")
for name, item in bindings.items():
    bound(ROOT / name, item, "frozen input: " + name)
prior = ROOT / "verification/github-delivery-runtime-followup/cache-deadline-review"
check(sha((prior / "seal.json").read_bytes()) == "c15eb4a779600d78adcb2b7e99bbe24c30bfed38d6cf3e087e431134a10457a8", "prior failed finite campaign seal unchanged")
for name, item in read(prior / "seal.json")["files"].items():
    bound(prior / name, item, "prior review unchanged: " + name)
inputs = ROOT / "verification/swift-cache-capacity-campaign-v1/inputs"
wasm = gzip.decompress((inputs / "fieldlog-reactor.wasm.gz").read_bytes())
guest = {"bytes": len(wasm), "sha256": sha(wasm)}
check(guest == {"bytes": 53777114, "sha256": "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"}, "same full guest bytes verified without execution")
del wasm
preflight = read(ART / "preflight/check.json")
check(preflight["artifact"] == guest and preflight["maxFullAttempts"] == 2 and preflight["aggregateDriverSeconds"] == 540 and preflight["fullTargetSeconds"] == 200, "actual preflight keeps selected guest and finite campaign bounds")
native = read(inputs / "native-observation.json")
check(len(native) == 11, "original native oracle contains all 11 fields")
historical = raw_events(inputs / "historical-attribution.stdout", "MIXER_EXACT ")
old_bounds = {k: event(historical, k) for k in ("validation_budget", "run_budget", "wasi_budget", "wasi_grants")}
commands = []
for path in sorted(ART.glob("**/receipt.json")):
    row = read(path)
    start = read(path.parent / "started.json")
    label = str(path.parent.relative_to(ART))
    check(all(typed_equal(row[k], v) for k, v in start.items()), "started-to-terminal command join: " + label)
    check(type(row["pid"]) is int and row["pid"] > 0 and type(row["exitCode"]) is int and 0 <= row["exitCode"] <= 255
          and row["processGroupEmpty"] is True and row["timedOut"] is False and row["cancelled"] is None and row["signals"] == [], "actual child exit and absent owned group: " + label)
    check(sha((path.parent / "stdout").read_bytes()) == row["stdoutSHA256"] and sha((path.parent / "stderr").read_bytes()) == row["stderrSHA256"], "command output hashes: " + label)
    commands.append({"command": label, **row})
check(len(commands) == 11 and len({r["pid"] for r in commands}) == 11, "exactly 11 distinct closed child commands")
check({r["command"] for r in commands if r["exitCode"] != 0} == {n + "/full" for n, _, _ in PROFILES}, "only two full-target failures among 11 commands")
check((ART / "tools/rustc/stdout").read_text().startswith("rustc 1.99.0 (b940084d7 2026-09-28)") and "host: x86_64-unknown-linux-gnu" in (ART / "tools/rustc/stdout").read_text(), "actual pinned Linux Rust compiler identity")
check((ART / "tools/cargo/stdout").read_text() == "cargo 1.99.0 (5f94df478 2026-08-27)\n" and (ART / "tools/python/stdout").read_text() == "Python 3.12.3\n", "actual Cargo and Python identities")
log = (HERE / "job.log").read_text()
check(HEAD in log and "Ran 19 tests" in log and "\n" in log, "job log joins selected checkout and 19 pure controls")
check(campaign["fullAttempts"] == campaign["maxFullAttempts"] == 2 and campaign["status"] == "milestone-unmet-campaign-closed", "two full attempts exhausted; milestone remains unmet")
results = []
for index, (name, work, source_hash) in enumerate(PROFILES):
    directory = ART / name
    source = read(directory / "source.json")
    check(typed_equal(source, read(PACKET / "source-check" / name / "source.json")) and typed_equal(source, read(ART / "preflight" / name / "source.json")), name + ": actual generated source equals selected and preflight manifests")
    check(source["sha256"] == source_hash == sha((json.dumps(source["files"], indent=2, sort_keys=True) + "\n").encode()), name + ": generated source manifest digest")
    check((directory / "delta-from-reviewed-256.patch").read_bytes() == (PACKET / "source-check" / name / "delta-from-reviewed-256.patch").read_bytes(), name + ": exact selected source delta")
    bounds = parse(json.dumps(old_bounds))
    bounds["run_budget"].update(cache_entries=256, cache_work=work, deadline_ms=60000)
    bounds["wasi_budget"].update(deadline_ms=60000)
    result = read(directory / "result.json")
    events = raw_events(directory / "full/stdout", "MIXER_EXACT ")
    check(typed_equal(result["events"], events), name + ": classifier events exactly reproduce raw stdout")
    actual = {k: event(events, k) for k in bounds}
    check(typed_equal(bounds, actual) and typed_equal(bounds, read(directory / "selected-bounds.json")) and typed_equal(bounds, result["actualBounds"]), name + ": all budgets and host grants match selected values and types")
    check(typed_equal(campaign["profiles"][index]["actualBounds"], actual) and campaign["profiles"][index]["sourceSHA256"] == source_hash and campaign["profiles"][index]["sourceAndInputUnchanged"] is True, name + ": campaign source/bounds/unchanged join")
    binary = read(directory / "binary.json")
    cargo_messages = [parse(line) for line in (directory / "build/stdout").read_text().splitlines() if line.startswith("{")]
    executables = [r for r in cargo_messages if r.get("reason") == "compiler-artifact" and r.get("executable")]
    check(len(executables) == 1 and executables[0]["executable"] == binary["path"] and campaign["profiles"][index]["binary"] == binary, name + ": build artifact path and recorded binary identity join")
    check(executables[0]["profile"] == {"opt_level": "3", "debuginfo": 0, "debug_assertions": False, "overflow_checks": True, "test": True}, name + ": optimized build preserves overflow checks")
    for stage, exit_code, tests in (("finite", 0, "test result: ok. 4 passed; 0 failed; 0 ignored"), ("harness-control", 0, "test result: ok. 1 passed; 0 failed; 0 ignored"), ("full", 101, "test result: FAILED. 0 passed; 1 failed; 0 ignored")):
        receipt = read(directory / stage / "receipt.json")
        check(receipt["argv"][0] == binary["path"] and receipt["exitCode"] == exit_code and tests in (directory / stage / "stdout").read_text(), name + ": exact binary and observed test counts: " + stage)
    full = read(directory / "full/receipt.json")
    check(full["timeoutSeconds"] == 200 and "--exact" in full["argv"] and full["argv"][1].endswith("::exact_reactor_target_once"), name + ": one exact bounded full target command")
    check([e["payload"] for e in events if e["event"] == "phase_begin"] == ["validation", "initialize", "corpus_1"] and event(events, "phase_failed") == "corpus_1", name + ": one initialization; first corpus failed; second corpus not reached")
    check(event(events, "initialize")["lifecycle"] == "Ready" and event(events, "corpus_1")["lifecycle"] == "Terminal", name + ": lifecycle observed ready then terminal")
    check(event(events, "input")["visible_bytes"] == guest["bytes"] and event(events, "external_input_dropped") is True, name + ": full input visible then external owner dropped")
    check(not [e for e in events if e["event"] == "guest_output_native_equal"] and result["completeGuestObservations"] == [] and result["nativeEqualPhases"] == [] and not result["complete"] and not result["hostFeasibility"], name + ": neither corpus has a complete 11-field native equality result")
    failure = event(events, "runtime_failure")
    final_failure = event(events, "final_failure")
    check(typed_equal(final_failure | {"after_cleanup": None}, failure) and typed_equal(result["firstFailure"], {"event": "runtime_failure", "payload": failure}), name + ": original failure preserved exactly through final cleanup")
    expected = ("WorkExhausted", "swift_run_work", "CacheWork", 64000001, 64000000) if index == 0 else ("FuelExhausted", "swift_run_fuel", "InstructionFuel", 100000001, 100000000)
    check(tuple(failure[k] for k in ("kind", "code", "resource", "attempted", "limit")) == expected, name + ": exact actual first failure")
    clean = event(events, "final_cleanup_usage")
    check(zero_resources(clean) and event(events, "cleanup_reservations_and_live_empty") is True and event(events, "cleanup_empty") is False and event(events, "diagnostic_execution_complete") is False and result["consumingCleanup"] is True, name + ": consuming zero-resource cleanup, with original failure retained")
    snapshots = raw_events(directory / "full/stdout", "MIXER_ATTRIBUTION ")
    check(typed_equal(snapshots, result["telemetry"]["snapshots"]) and result["telemetry"]["status"] == "valid" and result["telemetry"]["issues"] == [], name + ": attribution source lines join classifier")
    check([r["lifecycle"] for r in snapshots] == ["constructed", "initialize", "corpus_1", "before_cleanup", "final_cleanup"], name + ": complete ordered telemetry lifecycle")
    previous = None
    for number, snapshot in enumerate(snapshots, 1):
        payload = snapshot["payload"]
        check(snapshot["sequence"] == number and snapshot["reset_count"] == 1 and snapshot["valid"] is True and snapshot["formatted"] is True and not snapshot["prior_write_failed"] and all(snapshot[k] == 0 for k in ("observer_invalid", "adapter_invalid", "invariant_mask")), name + ": telemetry guards at " + snapshot["lifecycle"])
        check(sum(payload["credits"]) == snapshot["cache_work"] and payload["invalid"] == 0 and payload["completed"] == snapshot["cache_decodes"] == payload["distinct"] + payload["repeated"] and sum(payload["scan_credits"]) == payload["credits"][6] and sum(payload["build_credits"]) == payload["credits"][13] and sum(payload["scan_calls"]) == payload["calls"][6] and sum(payload["build_calls"]) == payload["calls"][13] and sum(payload["scan_published"]) == payload["plans"][3], name + ": independent attribution arithmetic at " + snapshot["lifecycle"])
        bound_snapshot = clean if snapshot["lifecycle"] == "final_cleanup" else event(events, snapshot["lifecycle"])["usage"]
        check(snapshot["cache_work"] == bound_snapshot["cache_work"], name + ": attribution work joins original usage at " + snapshot["lifecycle"])
        if previous:
            check(all(all(a >= b for a, b in zip(payload[k], previous[k])) for k in ("credits", "calls", "plans", "scan_credits", "scan_calls", "scan_published", "build_credits", "build_calls")), name + ": telemetry counters remain cumulative at " + snapshot["lifecycle"])
        previous = payload
    rejection = snapshots[-1]["payload"]["first_rejection"]
    if index == 0:
        check(rejection["site"] == 2 and rejection["requested"] == 1 and rejection["resource"] == "Some(CacheWork)" and all(rejection[k] == failure[k] for k in ("kind", "attempted", "limit", "function", "offset")), name + ": exact attribution rejection matches primary cause")
    else:
        check(rejection is None, name + ": fuel failure does not invent a cache rejection")
    results.append({"name": name, "sourceSHA256": source_hash, "bounds": actual, "failure": failure, "phaseOrder": result["phaseOrder"], "completeCorpusOutputs": 0, "corpus2Started": False, "finalResourceUsage": clean, "attributionAtCorpus1": snapshots[2], "fullCommand": full, "controls": {"finitePassed": 4, "harnessPassed": 1, "fullFailed": 1}, "binary": binary})
check(campaign["conditionalSecondSelected"] is True and campaign["conditionalSecondReason"] == "verified CacheWork exhaustion with original cause and complete cleanup", "conditional second selection justified by independently verified primary predicates")
check(campaign["cleanup"]["ownedScratchRemoved"] is True and campaign["cleanup"]["commandCustodyUnresolved"] is False and campaign["cleanup"]["commandCustody"] == read(ART / "custody.json") and read(ART / "custody.json")["pendingCommand"] is None and read(ART / "custody.json")["provenClosedCommands"] == 11, "all command custody closed and owned scratch removal recorded")
check(all(p["peakRSSAvailableForVMComparison"] is False for p in campaign["profiles"]), "VM-attributable RSS remains unavailable")
report = {"schema": 1, "verifiedAt": datetime.now(timezone.utc).isoformat(), "status": "verified-evidence-milestone-unmet", "checksPassed": len(checks), "checks": checks, "source": {"head": HEAD, "tree": TREE, "selectedSealSHA256": SEAL, "driverSHA256": DRIVER}, "runId": run["id"], "fullAttempts": 2, "hostFeasibilityProfiles": 0, "profiles": results, "commands": commands, "reviewTool": {"python": sys.version, "platform": platform.platform()}, "scope": "Offline bytes, JSON and read-only Git-object review only; no artifact code imported, runtime/compiler/native/custody/UI probe or workflow dispatch.", "limitations": ["Generated source is joined through sealed selected source manifests and the remote unchanged-source observation; generated sources and binaries were removed with owned remote scratch and are not retained in this artifact.", "Recorded binary SHA256 and bytes join compiler executable paths and test commands; binary bytes are not independently rehashed locally.", "Raw wait4 RSS retained; launcher high-water floor prevents per-profile VM RSS comparison.", "Native runtime, physical device, public package/FieldLog, OTA and GA qualification remain pending."]}
(HERE / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"status": report["status"], "checksPassed": len(checks), "fullAttempts": 2, "hostFeasibilityProfiles": 0, "allCommandsClosed": True}))

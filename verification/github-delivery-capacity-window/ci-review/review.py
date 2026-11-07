#!/usr/bin/env python3
"""Offline review of one immutable remote artifact; no guest or compiler execution."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANDIDATE = ROOT / "verification/swift-cachework-128-experiment"
HEAD = "e5670519a0d02b74a95c00d35dbf5f837fca9850"
TREE = "89a9344ecf974105b7ad7df30394485bade6e284"
RUN = 40788458735
JOB = 123167428868
ARMS = ("dense-256-window", "dense-512-window")
START = time.monotonic()
START_UTC = datetime.datetime.now(datetime.timezone.utc).isoformat()
CHECKS, READS, DENIED = [], set(), []
SEALS = {
    "swift-cachework-128-experiment": "dce182dba6c4e4bf38738b486276596c7b0cbc17c798e8780ebd19287bced0d0",
    "swift-capacity-window-independent": "2b657ff19b7218fd20a2371b8dd587bb4ac8a672569361b103317684e8cf3384",
}


def denied(*args, **kwargs):
    DENIED.append("explicit process/network helper")
    raise RuntimeError("offline review forbids process/network effects")


def audit(event, args):
    if event.startswith(("subprocess.", "socket.", "pty.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.kill", "os.killpg", "os.chdir",
    }:
        DENIED.append(event)
        raise RuntimeError("offline reviewer audit denied " + event)
    if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
        p = Path(os.fsdecode(args[0])).absolute()
        mode, flags = args[1], args[2]
        writing = isinstance(mode, str) and any(x in mode for x in "wax+")
        writing = writing or isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        if writing and not p.is_relative_to(HERE):
            raise RuntimeError("write outside review lane: " + str(p))
        if not writing and p.is_relative_to(ROOT) and not p.is_relative_to(HERE):
            READS.add(p)
    if event in {"os.remove", "os.rmdir", "os.mkdir", "os.rename"}:
        for value in args[:2] if event == "os.rename" else args[:1]:
            if isinstance(value, (str, bytes, os.PathLike)) and not Path(os.fsdecode(value)).absolute().is_relative_to(HERE):
                raise RuntimeError("mutation outside review lane")


sys.addaudithook(audit)
socket.socket = socket.create_connection = subprocess.Popen = denied
for key in ("system", "fork", "forkpty", "posix_spawn", "posix_spawnp", "kill", "killpg", "wait", "waitpid", "wait3", "wait4", "popen"):
    if hasattr(os, key):
        setattr(os, key, denied)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(data):
    return {"bytes": len(data), "sha256": sha(data)}


def strict(data):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key " + key)
            out[key] = value
        return out
    return json.loads(data, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def check(label, condition):
    if time.monotonic() - START > 60:
        raise RuntimeError("offline review exceeded sixty-second internal bound")
    CHECKS.append({"check": label, "passed": bool(condition)})
    if not condition:
        raise AssertionError(label)


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class MemoryPath:
    def __init__(self, data):
        self.data = data
    def read_bytes(self):
        return self.data
    def read_text(self):
        return self.data.decode()


def events(data):
    return [strict(line.split("MIXER_EXACT ", 1)[1]) for line in data.decode().splitlines() if "MIXER_EXACT " in line]


def event(rows, name):
    selected = [r["payload"] for r in rows if r["event"] == name]
    check("one raw event " + name, len(selected) == 1)
    return selected[0]


def seals():
    result = []
    for lane, expected in SEALS.items():
        directory = ROOT / "verification" / lane
        data = (directory / "seal.json").read_bytes()
        check("selected seal " + lane, sha(data) == expected)
        s = strict(data)
        files = {n: record((directory / n).read_bytes()) for n in s["files"]}
        check("all sealed bytes " + lane, files == s["files"] and len(files) == s["filesCount"] and sum(r["bytes"] for r in files.values()) == s["totalBytes"])
        result.append({"lane": lane, "sealSHA256": expected, "files": len(files), "bytes": s["totalBytes"]})
    return result


def main():
    before = seals()
    selection = strict((HERE.parent / "selection.json").read_bytes())
    delivery = strict((HERE.parent / "receipt.json").read_bytes())
    dispatch = strict((HERE.parent / "dispatch-receipt.json").read_bytes())
    check("root exact delivery and one selected dispatch", delivery["commit"] == dispatch["head"] == HEAD and delivery["tree"] == dispatch["tree"] == TREE and dispatch["dispatchCallsMade"] == 1 and dispatch["runId"] == RUN and dispatch["runAttempt"] == 1 and dispatch["profile"] == "capacity-window-v1")
    manifest_bytes = (HERE.parent / "manifest.json").read_bytes()
    manifest = strict(manifest_bytes)
    check("root delivery manifest and selection exact hashes", record(manifest_bytes) == {k: delivery["manifest"][k] for k in ("bytes", "sha256")} and record((HERE.parent / "selection.json").read_bytes()) == {k: delivery["sourceSelection"][k] for k in ("bytes", "sha256")})
    selected_sources = [r for r in manifest["members"] if r["path"].startswith(("verification/swift-cachework-128-experiment/", "verification/swift-capacity-window-independent/"))]
    check("all delivered reviewed source bytes unchanged", len(selected_sources) >= 40 and all(record((ROOT / r["path"]).read_bytes()) == {k: r[k] for k in ("bytes", "sha256")} for r in selected_sources))
    check("selected reviewed workflow exact bytes", sha((ROOT / selection["workflow"]["destination"]).read_bytes()) == selection["workflow"]["sha256"] and (ROOT / selection["workflow"]["destination"]).read_bytes() == (CANDIDATE / "workflow.yml").read_bytes())
    inputs = {n: record((HERE / n).read_bytes()) for n in ("artifact.zip", "artifact-metadata.json", "job.log", "final-snapshot.json")}
    metadata = strict((HERE / "artifact-metadata.json").read_bytes())
    snapshot = strict((HERE / "final-snapshot.json").read_bytes())
    check("artifact service digest", metadata["digest"] == "sha256:" + inputs["artifact.zip"]["sha256"] and metadata["size_in_bytes"] == inputs["artifact.zip"]["bytes"])
    check("artifact exact service identity", metadata["workflow_run"]["id"] == RUN and metadata["workflow_run"]["head_sha"] == HEAD and metadata["name"] == f"swift-cachework-128-experiment-{HEAD}-{RUN}-1" and metadata["expired"] is False)
    check("final exact run snapshot", snapshot["capacity"]["id"] == RUN and snapshot["capacity"]["head"] == HEAD and snapshot["capacity"]["attempt"] == 1 and snapshot["capacity"]["status"] == "completed" and snapshot["capacity"]["jobs"][0]["id"] == JOB)
    ordinary = snapshot["ordinary"]
    check("ordinary six jobs green at same head", ordinary["id"] == 40788454624 and ordinary["head"] == HEAD and ordinary["attempt"] == 1 and ordinary["status"] == "completed" and ordinary["conclusion"] == "success" and len(ordinary["jobs"]) == 6 and all(j["conclusion"] == "success" for j in ordinary["jobs"]))
    with zipfile.ZipFile(HERE / "artifact.zip") as archive:
        entries = archive.infolist()
        check("unique safe bounded archive", len(entries) == len({x.filename for x in entries}) and len(entries) <= 100 and all(not x.is_dir() and not Path(x.filename).is_absolute() and ".." not in Path(x.filename).parts and x.file_size < 2_000_000 for x in entries) and sum(x.file_size for x in entries) < 4_000_000)
        raw = {x.filename: archive.read(x.filename) for x in entries}
        check("archive CRC", archive.testzip() is None)
    inventory = {n: record(b) for n, b in sorted(raw.items())}
    parsed = {n: strict(b) for n, b in raw.items() if n.endswith(".json")}
    c, pre = parsed["campaign.json"], parsed["preflight/check.json"]
    check("campaign exact run", (c["githubSHA"], c["githubRunId"], c["githubRunAttempt"]) == (HEAD, str(RUN), "1"))
    check("closed bounded campaign", c["status"] == "comparison-closed" and c["fullAttempts"] == c["maxFullAttempts"] == 2 and c["maxCommands"] == 11 and c["aggregateDeadlineSeconds"] == 2700)
    check("both preparations before any full", c["preparationGate"] == {"bothArmsPrepared": True, "closedPreparationCommands": 9, "fullAttemptsAtAdmission": 0} and [p["name"] for p in c["preparedProfiles"]] == list(ARMS))
    log = (HERE / "job.log").read_text()
    check("published log joins checkout artifact and driver", HEAD in log and f"Artifact ID {metadata['id']}" in log and inputs["artifact.zip"]["sha256"] in log and "verification/swift-cachework-128-experiment/campaign.py run" in log)
    check("published pure tests count", "Ran 43 tests" in log)

    spec = importlib.util.spec_from_file_location("capacity_actual_review_runner", CANDIDATE / "campaign.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    original, wasm, bindings = runner.inputs()
    check("unchanged frozen workload and bindings", record(wasm) == pre["artifact"] == {"bytes": 53777114, "sha256": "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"} and bindings == c["inputBindings"] == pre["inputBindings"])
    check("exact candidate generators", runner.candidate_bindings() == c["candidateSourceBindings"] == pre["candidateSourceBindings"])
    oracle = strict((runner.base.INPUTS / "native-observation.json").read_bytes())
    check("original eleven-field oracle", len(oracle) == 11)
    commands = []
    for n, row in parsed.items():
        if not n.endswith("/receipt.json"):
            continue
        d = n.rsplit("/", 1)[0]
        start = parsed[d + "/started.json"]
        check("started-receipt identity " + d, all(row[k] == v for k, v in start.items()))
        check("complete output hashes " + d, all(sha(raw[d + "/" + stream]) == row[stream + "SHA256"] for stream in ("stdout", "stderr")))
        check("command closed within selected bound " + d, type(row["pid"]) is int and row["pid"] > 0 and row["processGroupEmpty"] is True and row["timedOut"] is False and row["cancelled"] is None and row["signals"] == [] and 0 <= row["wallSeconds"] <= row["timeoutSeconds"] and type(row["exitCode"]) is int and row["exitCode"] in (0, 101))
        check("non-full command success " + d, d.endswith("/full") or row["exitCode"] == 0)
        check("command environment " + d, row["environment"]["RUSTUP_TOOLCHAIN"] == "1.99.0" and row["environment"]["CARGO_NET_OFFLINE"] == "true" and row["environment"]["CARGO_INCREMENTAL"] == "0" and row["environment"]["CARGO_BUILD_JOBS"] == "2")
        commands.append({"directory": d, "startedUTC": row["startedUTC"], "wallSeconds": row["wallSeconds"], "exitCode": row["exitCode"], "argv": row["argv"], "processGroupEmpty": row["processGroupEmpty"]})
    commands.sort(key=lambda x: x["startedUTC"])
    order = ["tools/rustc", "tools/cargo", "tools/python"] + [a + "/" + p for a in ARMS for p in ("build", "finite", "harness-control")] + [a + "/full" for a in ARMS]
    check("exact eleven command order", [x["directory"] for x in commands] == order)
    for left, right in zip(commands, commands[1:]):
        end = datetime.datetime.fromisoformat(left["startedUTC"]) + datetime.timedelta(seconds=left["wallSeconds"])
        check("no command overlap " + right["directory"], datetime.datetime.fromisoformat(right["startedUTC"]) >= end)
    check("aggregate execution inside driver bound", (datetime.datetime.fromisoformat(commands[-1]["startedUTC"]) - datetime.datetime.fromisoformat(commands[0]["startedUTC"])).total_seconds() + commands[-1]["wallSeconds"] <= 2700)
    custody = parsed["custody.json"]
    check("eleven commands and scratch fully closed", custody == c["cleanup"]["commandCustody"] and custody["pendingCommand"] is None and custody["provenClosedCommands"] == 11 and c["cleanup"]["ownedScratchRemoved"] is True and c["cleanup"]["commandCustodyUnresolved"] is False and not any("scratch/" in p for p in raw))
    check("actual pinned Linux compiler", raw["tools/rustc/stdout"].decode().startswith("rustc 1.99.0 (b940084d7 2026-09-28)") and "host: x86_64-unknown-linux-gnu" in raw["tools/rustc/stdout"].decode())
    summaries, generated = [], {}
    for index, arm in enumerate(ARMS):
        source = runner.prepare_source(original, bool(index))
        generated[arm] = source
        src, delta = runner.base.source_record(original, source)
        prepared, profile = c["preparedProfiles"][index], c["profiles"][index]
        check("regenerated source manifests " + arm, src == parsed[arm + "/source.json"] == parsed["preflight/" + arm + "/source.json"] and src["sha256"] == prepared["sourceSHA256"] == profile["sourceSHA256"] == selection["profiles"][index]["sourceSHA256"])
        check("regenerated source patches " + arm, delta.encode() == raw[arm + "/changes.patch"] == raw["preflight/" + arm + "/changes.patch"])
        check("preparation counts and original harness " + arm, prepared["finiteCount"] == 12 and prepared["harnessCount"] == 1 and prepared["fullAttemptsAtPreparation"] == 0 and source["src/experimental_swift_reactor/campaign_harness.rs"] == (runner.base.INPUTS / "harness.rs").read_bytes())
        build = [strict(line) for line in raw[arm + "/build/stdout"].splitlines()]
        binaries = [r for r in build if r.get("executable")]
        binary = parsed[arm + "/binary.json"]
        check("fresh optimized checked binary " + arm, len(binaries) == 1 and binaries[0]["executable"] == binary["path"] and binaries[0]["profile"] == {"opt_level": "3", "debuginfo": 0, "debug_assertions": False, "overflow_checks": True, "test": True} and binaries[0]["fresh"] is False and type(binary["bytes"]) is int and binary["bytes"] > 0 and len(binary["sha256"]) == 64)
        check("binary execution manifest joins " + arm, binary == prepared["binary"] == profile["binary"] and all(parsed[arm + "/" + p + "/receipt.json"]["argv"][0] == binary["path"] for p in ("finite", "harness-control", "full")))
        geometry = runner.geometry_record(MemoryPath(raw[arm + "/finite/stdout"]), bool(index))
        check("geometry receipt reproduction " + arm, geometry == parsed[arm + "/geometry.json"] and sha(raw[arm + "/geometry.json"]) == prepared["geometrySHA256"])
        plan, cache = geometry["plan"], geometry["cache"]
        total = plan["category_ceiling_sum"] + plan["wasi_max"] + plan["shared"] + plan["floor"] + max(plan["execution_construction"], plan["frame_operation"] + cache["operation"])
        check("independent compiled geometry sum " + arm, total == geometry["recomputedConservativeCombined"] == plan["conservative_combined"] <= 268435456)
        check("finite and harness exact pass counts " + arm, "test result: ok. 12 passed; 0 failed; 0 ignored" in raw[arm + "/finite/stdout"].decode() and "test result: ok. 1 passed; 0 failed; 0 ignored" in raw[arm + "/harness-control/stdout"].decode())
        h = events(raw[arm + "/harness-control/stdout"])
        check("harness same-owner phase wiring " + arm, [r["payload"] for r in h if r["event"] == "phase_begin"] == ["validation", "initialize", "corpus_1", "corpus_2"] and event(h, "diagnostic_execution_complete") is True and event(h, "cleanup_empty") is True)
        full = parsed[arm + "/full/receipt.json"]
        result = parsed[arm + "/result.json"]
        reproduced = runner.base.classify(MemoryPath(raw[arm + "/full/stdout"]), full)
        runner.validate_result(reproduced, full, bool(index))
        check("raw full classification reproduction " + arm, reproduced == result)
        prefix, prefix_bytes = runner.prefix_records(MemoryPath(raw[arm + "/full/stderr"]))
        runner.validate_prefix(result, prefix)
        check("raw prefix reproduction " + arm, prefix == parsed[arm + "/prefix.json"] and prefix_bytes == raw[arm + "/prefix.records"])
        rows = events(raw[arm + "/full/stdout"])
        bounds = runner.expected_bounds(bool(index))
        check("raw events and complete selected bounds " + arm, rows == result["events"] and all(event(rows, k) == v for k, v in bounds.items()) and bounds == result["actualBounds"] == profile["actualBounds"] == parsed[arm + "/selected-bounds.json"] == selection["profiles"][index]["bounds"])
        usage, final_failure = event(rows, "final_cleanup_usage"), event(rows, "final_failure")
        failures = [r["payload"] for r in rows if r["event"] == "runtime_failure"]
        check("original failure identity " + arm, len(failures) <= 1 and (final_failure is None if not failures else {**final_failure, "after_cleanup": None} == failures[0]))
        check("all authoritative final resources zero " + arm, usage["cleanup_invariant"] is None and usage["reservations"]["live_tickets"] == 0 and all(v["current"] == 0 for group in ("reservations", "live") for v in usage[group].values() if isinstance(v, dict)) and event(rows, "cleanup_reservations_and_live_empty") is True)
        previous = {k: 0 for k in ("instructions", "instruction_fuel", "elapsed_micros", "execution_work", "cache_work", "host_calls")}
        for observed in [*prefix["records"], usage]:
            check("cumulative counters " + arm + " " + str(observed["instructions"]), all(type(observed[k]) is int and 0 <= previous[k] <= observed[k] < 2**64 for k in previous) and observed["instruction_fuel"] - previous["instruction_fuel"] >= observed["instructions"] - previous["instructions"])
            previous = {k: observed[k] for k in previous}
        check("attribution valid " + arm, result["telemetry"]["status"] == "valid" and result["telemetry"]["issues"] == [] and all(r["valid"] is True and r["reset_count"] == 1 and r["invariant_mask"] == r["adapter_invalid"] == r["observer_invalid"] == 0 for r in result["telemetry"]["snapshots"]))
        complete = result["hostFeasibility"] is True
        check("every completed original corpus matches eleven fields " + arm, [o["phase"] for o in result["completeGuestObservations"]] == result["nativeEqualPhases"] and all(o["phase"] in ("corpus_1", "corpus_2") and type(o["observation"]) is dict and set(o["observation"]) == set(oracle) and all(type(o["observation"][k]) is type(v) and o["observation"][k] == v for k, v in oracle.items()) for o in result["completeGuestObservations"]))
        check("oracle completion is exact or explicitly absent " + arm, (result["complete"] is True and result["nativeEqualPhases"] == ["corpus_1", "corpus_2"] and [o["phase"] for o in result["completeGuestObservations"]] == ["corpus_1", "corpus_2"] and all(o["observation"] == oracle for o in result["completeGuestObservations"])) if complete else result["complete"] is False)
        summaries.append({"arm": arm, "sourceSHA256": src["sha256"], "sourceFiles": len(source), "binary": binary, "binaryIndependentlyRehashed": False, "finitePassed": 12, "harnessPassed": 1, "geometry": geometry, "outcome": result["outcome"], "hostFeasibility": complete, "phaseOrder": result["phaseOrder"], "firstFailure": failures[0] if failures else None, "finalUsage": usage, "completeGuestObservations": result["completeGuestObservations"], "nativeEqualPhases": result["nativeEqualPhases"], "prefixes": prefix["records"], "timing": profile["timing"], "allFinalCurrentResourcesAndTicketsZero": True})
    differing = sorted(n for n in generated[ARMS[0]] if generated[ARMS[0]][n] != generated[ARMS[1]][n])
    check("only resident-capacity source factor", differing == ["src/experimental/cache/mod.rs", "src/experimental_swift_reactor/cache.rs", "src/experimental_swift_reactor/cache_tests.rs", "src/experimental_swift_reactor/control.rs"])
    left_bounds, right_bounds = [runner.expected_bounds(bool(i)) for i in range(2)]
    right_bounds["run_budget"]["cache_entries"] = 256
    check("only selected resident-capacity bound differs", left_bounds == right_bounds)
    pairs = []
    for left, right in zip(summaries[0]["prefixes"], summaries[1]["prefixes"]):
        fields = ("threshold", "instructions", "instruction_fuel", "execution_work", "host_calls", "function", "offset")
        matched = all(left[k] == right[k] for k in fields)
        pairs.append({"instructions": left["instructions"], "observedCountersAndCursorMatched": matched, "matchedFieldNames": list(fields), "arm256": left, "arm512": right})
    baseline_dir = ROOT / "verification/github-delivery-frame-pin-128/ci-review"
    baseline_seal_bytes = (baseline_dir / "seal.json").read_bytes()
    check("retained baseline exact review seal", sha(baseline_seal_bytes) == "3161abdae5f7ee09a0bd67062d3ae393af17bdb99a5859b20efb3ef404affbb8")
    baseline_seal = strict(baseline_seal_bytes)
    check("retained baseline all sealed members", all(record((baseline_dir / n).read_bytes()) == v for n, v in baseline_seal["files"].items()))
    with zipfile.ZipFile(baseline_dir / "artifact.zip") as archive:
        old_campaign = strict(archive.read("campaign.json"))
        old_result = strict(archive.read("dense-frame128-pin128/result.json"))
        old_prefix = strict(archive.read("dense-frame128-pin128/prefix.json"))
    check("retained actual baseline exact run", old_campaign["githubRunId"] == "40779075333" and old_campaign["githubRunAttempt"] == "1" and old_campaign["status"] == "comparison-closed" and old_campaign["fullAttempts"] == 2)
    old_failure = old_result["firstFailure"]["payload"]
    check("retained original baseline CacheWork failure", old_failure["resource"] == "CacheWork" and old_failure["limit"] == 768000000 and old_result["hostFeasibility"] is False)
    baseline_pairs = []
    for left, right in zip(old_prefix["records"], summaries[0]["prefixes"]):
        fields = ("threshold", "instructions", "instruction_fuel", "execution_work", "cache_work", "host_calls", "function", "offset")
        baseline_pairs.append({"instructions": left["instructions"], "observedCountersAndCursorMatched": all(left[k] == right[k] for k in fields), "matchedFieldNames": list(fields), "priorDense256": left, "currentDense256": right})
    check("immutable raw inputs unchanged", inputs == {n: record((HERE / n).read_bytes()) for n in inputs})
    check("selected seals unchanged", before == seals())
    check("no forbidden operations attempted", DENIED == [])
    output = {"schema": 1, "decision": "accept closed actual diagnostic evidence; host feasibility determined separately per arm", "run": RUN, "attempt": 1, "job": JOB, "head": HEAD, "tree": TREE, "artifact": {"id": metadata["id"], **inputs["artifact.zip"]}, "selectedPackets": before, "arms": summaries, "pairedPrefixes": pairs, "retainedBaseline": {"run": 40779075333, "reviewSealSHA256": sha(baseline_seal_bytes), "originalFailure": old_failure, "matchedObservedPrefixes": baseline_pairs, "endpointTimingClaim": False}, "commands": commands, "oracle": {"fields": list(oracle), "fieldCount": 11, "requiredCorpora": ["corpus_1", "corpus_2"]}, "cleanup": c["cleanup"], "allChecksPassed": True, "scopeLimitations": ["One sequential sample per arm. Matched prefix counters and cursor do not prove identical entropy or all guest state.", "Endpoint timing comparison is unsupported when work endpoints differ; prefix elapsed includes more than cache work.", "Policy work credits are not CPU time; logical reservations are not process RSS. Raw wait4 RSS has a launcher high-water floor.", "Binary hashes are CI-reported manifests joined to execution paths; executable bytes were removed before upload and are not independently rehashed here.", "Remote output streams are regular files, closed after wait4 child reaping and owned-group absence, then hashed. No explicit pipe EOF flag exists in this frozen driver.", "Host diagnostic evidence does not accept production defaults, native/mobile, signed OTA, published external FieldLog, customer behavior or GA."]}
    save("review.json", output)
    save("artifact-inventory.json", {"files": inventory, "fileCount": len(inventory), "bytes": sum(r["bytes"] for r in inventory.values())})
    save("checks.json", CHECKS)
    readset = {str(p.relative_to(ROOT)): record(p.read_bytes()) for p in sorted(READS) if p.is_file()}
    save("readset.json", {"files": readset, "filesCount": len(readset), "totalBytes": sum(r["bytes"] for r in readset.values()), "sourceHead": HEAD, "sourceTree": TREE})
    save("receipt.json", {"schema": 1, "command": "python3 -B verification/github-delivery-capacity-window/ci-review/review.py", "python": sys.version, "startedAtUTC": START_UTC, "completedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "elapsedSeconds": time.monotonic() - START, "internalDeadlineSeconds": 60, "checksPassed": len(CHECKS), "sourceHead": HEAD, "sourceTree": TREE, "readsetSHA256": sha((HERE / "readset.json").read_bytes()), "artifactInventorySHA256": sha((HERE / "artifact-inventory.json").read_bytes()), "reviewSHA256": sha((HERE / "review.json").read_bytes()), "childSocketSignalWaitInventoryEffects": 0, "compilerGuestNativeCaptureExecutions": 0, "newFullAttempts": 0, "gitWritesDispatches": 0, "scratchCreated": False, "writesRestrictedToReviewLane": True, "forbiddenAttempts": DENIED, "localCommandCustody": "single exec-tool-owned Python process; no children allowed"})
    print(f"PASS {len(CHECKS)} checks; {len(inventory)} artifact files; 2 full attempts; host-feasible arms: {[r['arm'] for r in summaries if r['hostFeasibility']]}")


if __name__ == "__main__":
    main()

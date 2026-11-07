#!/usr/bin/env python3
"""Bounded offline re-verification of the one selected remote comparison.

No compiler, guest, network, process discovery, signaling or child process calls.
Imported campaign helpers are used only for pure regeneration/classification;
the independent checks below join raw bytes, receipts and actual observations.
"""
import copy
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
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORRECTION = ROOT / "verification/swift-execution-architecture-correction"
START = time.monotonic()
START_UTC = datetime.datetime.now(datetime.timezone.utc).isoformat()
READS = set()
CHECKS = []
DENIED = []
HEAD = "dfd0e3196543cc1749c9cc924cc7accf28c9dc25"
TREE = "3cc58d6744649fdd138b9d3963b436db62480ecf"
ARMS = ("control-original256", "candidate-dense")
SEALS = {
    "swift-execution-architecture-comparison": "b20440be09778e3209de5c1e6dae941e0580b8737fe28ed35be53777e3292f70",
    "swift-execution-architecture-independent": "c1ecb422803c2e43dc69206b28e6f51e2b023b9b8fab13054e20ecc7976a7486",
    "swift-execution-architecture-correction": "4efa21ab9e7bf43cec647c760bdacf6c3e5b2be944976240ec186c738370a6d2",
    "swift-execution-architecture-correction-independent": "4b09d719746ba04fbc722cd83751c2e2082d8997a984ce407031dc7e1f3daceb",
}


def forbidden(*args, **kwargs):
    DENIED.append("explicit process or network helper")
    raise RuntimeError("offline reviewer forbids process/network operations")


def audit(event, args):
    if event.startswith(("subprocess.", "socket.", "pty.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec",
        "os.kill", "os.killpg", "os.startfile", "os.chdir",
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
            if isinstance(value, (str, bytes, os.PathLike)):
                p = Path(os.fsdecode(value)).absolute()
                if not p.is_relative_to(HERE):
                    raise RuntimeError("mutation outside review lane")


sys.addaudithook(audit)
socket.socket = forbidden
socket.create_connection = forbidden
subprocess.Popen = forbidden
for name in ("system", "fork", "forkpty", "posix_spawn", "posix_spawnp", "kill", "killpg",
             "wait", "waitpid", "wait3", "wait4", "popen"):
    if hasattr(os, name):
        setattr(os, name, forbidden)


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
        raise RuntimeError("offline verifier exceeded 60-second internal limit")
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


def events(data, marker="MIXER_EXACT "):
    return [strict(line.split(marker, 1)[1]) for line in data.decode().splitlines() if marker in line]


def event(rows, name):
    values = [row["payload"] for row in rows if row["event"] == name]
    check("one raw event " + name, len(values) == 1)
    return values[0]


def git_object(oid):
    raw = zlib.decompress((ROOT / ".git/objects" / oid[:2] / oid[2:]).read_bytes())
    check("Git object SHA1 " + oid, hashlib.sha1(raw).hexdigest() == oid)
    header, payload = raw.split(b"\0", 1)
    kind, length = header.decode().split(" ")
    check("Git object length " + oid, len(payload) == int(length))
    return kind, payload


TREE_CACHE = {}


def git_entry(path):
    oid = TREE
    components = Path(path).parts
    for component in components:
        if oid not in TREE_CACHE:
            kind, raw = git_object(oid)
            check("Git traversal is tree " + oid, kind == "tree")
            entries = {}
            while raw:
                label, raw = raw.split(b"\0", 1)
                mode, name = label.split(b" ", 1)
                entries[name.decode()] = (mode.decode(), raw[:20].hex())
                raw = raw[20:]
            TREE_CACHE[oid] = entries
        mode, oid = TREE_CACHE[oid][component]
    return mode, oid


def verify_seals():
    summary = []
    for lane, expected in SEALS.items():
        directory = ROOT / "verification" / lane
        data = (directory / "seal.json").read_bytes()
        check("selected seal " + lane, sha(data) == expected)
        seal = strict(data)
        actual = {name: record((directory / name).read_bytes()) for name in seal["files"]}
        check("all sealed bytes " + lane, actual == seal["files"])
        check("sealed count " + lane, len(actual) == seal["fileCount"])
        check("sealed total " + lane, sum(v["bytes"] for v in actual.values()) == seal["totalBytes"])
        summary.append({"lane": lane, "sealSHA256": expected, "files": len(actual), "bytes": seal["totalBytes"]})
    readset = strict((CORRECTION / "readset.json").read_bytes())
    check("complete source readset", all(record((ROOT / p).read_bytes()) == v for p, v in readset["files"].items()))
    return summary


def main():
    before = verify_seals()
    inputs = {n: record((HERE / n).read_bytes()) for n in ("artifact.zip", "job.log", "artifact-metadata.json")}
    metadata = strict((HERE / "artifact-metadata.json").read_bytes())
    check("exact artifact compressed digest", inputs["artifact.zip"] == {"bytes": 151935, "sha256": "362d80ece5ed8b6b3678ba0d7fddfc61ce44368066fc61fd1094de19b6f4f6aa"})
    check("artifact service digest", metadata["digest"] == "sha256:" + inputs["artifact.zip"]["sha256"])
    check("artifact service exact identity", metadata["id"] == 12851363846 and metadata["workflow_run"]["id"] == 40768719255 and metadata["workflow_run"]["head_sha"] == HEAD and metadata["name"].endswith(HEAD + "-40768719255-1"))
    with zipfile.ZipFile(HERE / "artifact.zip") as archive:
        entries = archive.infolist()
        check("67 unique safe artifact files", len(entries) == len({x.filename for x in entries}) == 67 and all(not x.is_dir() and not Path(x.filename).is_absolute() and ".." not in Path(x.filename).parts for x in entries))
        check("bounded archive", sum(x.file_size for x in entries) < 2_000_000)
        raw = {x.filename: archive.read(x.filename) for x in entries}
        check("ZIP CRC", archive.testzip() is None)
    inventory = {name: record(data) for name, data in sorted(raw.items())}
    parsed = {name: strict(data) for name, data in raw.items() if name.endswith(".json")}
    c = parsed["campaign.json"]
    check("campaign exact run", (c["githubSHA"], c["githubRunId"], c["githubRunAttempt"]) == (HEAD, "40768719255", "1"))
    check("closed diagnostic campaign", c["status"] == "comparison-closed" and c["fullAttempts"] == c["maxFullAttempts"] == 2 and c["maxCommands"] == 11 and c["aggregateDeadlineSeconds"] == 2700 and c["milestoneObservedArms"] == [])
    selection = strict((HERE.parent / "selection.json").read_bytes())
    check("selected workflow bytes", record((ROOT / selection["workflow"]["path"]).read_bytes()) == {k: selection["workflow"][k] for k in ("bytes", "sha256")})
    check("selected correction workflow identical", (CORRECTION / "workflow.yml").read_bytes() == (ROOT / selection["workflow"]["path"]).read_bytes())
    check("root committed head receipt", (HERE.parent / "committed-head.stdout").read_text().strip() == HEAD)
    check("root committed tree receipt", (HERE.parent / "committed-tree.stdout").read_text().strip() == TREE)
    kind, commit = git_object(HEAD)
    check("independent exact commit tree", kind == "commit" and commit.splitlines()[0] == ("tree " + TREE).encode())
    bound_paths = [selection["workflow"]["path"], "verification/swift-execution-architecture-correction/campaign.py"]
    bound_paths += ["verification/swift-execution-architecture-correction/" + n for n in ("candidate.py", "dense-index.rs", "dense-mode.rs", "pin-hooks.rs", "dense-assert.rs", "dense-controls.rs")]
    bound_paths += ["verification/" + lane + "/seal.json" for lane in SEALS]
    for path in bound_paths:
        data = (ROOT / path).read_bytes()
        mode, oid = git_entry(path)
        expected_oid = hashlib.sha1(("blob " + str(len(data))).encode() + b"\0" + data).hexdigest()
        check("exact HEAD tree binds reviewed bytes " + path, mode in ("100644", "100755") and oid == expected_oid)
    log = (HERE / "job.log").read_text()
    check("job checkout and artifact identity", HEAD in log and "Artifact ID 12851363846" in log and inputs["artifact.zip"]["sha256"] in log)
    check("CI actual corrected driver and supplied tests", "verification/swift-execution-architecture-correction/campaign.py run" in log and "Ran 38 tests in 2.266s" in log)

    spec = importlib.util.spec_from_file_location("actual_ci_review_campaign", CORRECTION / "campaign.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    original, wasm, bindings = runner.inputs()
    check("frozen 53MB input rehash", record(wasm) == parsed["preflight/check.json"]["artifact"] == {"bytes": 53777114, "sha256": "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"})
    check("all original input bytes", bindings == c["inputBindings"] == parsed["preflight/check.json"]["inputBindings"])
    check("all generator inputs", runner.candidate_bindings() == c["candidateSourceBindings"] == parsed["preflight/check.json"]["candidateSourceBindings"])
    oracle = strict((runner.base.INPUTS / "native-observation.json").read_bytes())
    check("exact original oracle has 11 fields", len(oracle) == 11)
    bounds = runner.expected_bounds()
    check("same finite limits", bounds["run_budget"]["instruction_fuel"] == 1_000_000_000 and bounds["run_budget"]["execution_work"] == 8_000_000_000 and bounds["run_budget"]["cache_work"] == 768_000_000 and bounds["run_budget"]["deadline_ms"] == bounds["wasi_budget"]["deadline_ms"] == 600_000 and bounds["run_budget"]["combined_bytes"] == 268435456 and bounds["run_budget"]["cache_entries"] == 256 and bounds["run_budget"]["active_pins"] == 64)

    commands = []
    for name, receipt in parsed.items():
        if not name.endswith("/receipt.json"):
            continue
        directory = name.rsplit("/", 1)[0]
        start = parsed[directory + "/started.json"]
        check("started/receipt identity " + directory, all(receipt[k] == v for k, v in start.items()))
        check("command raw outputs " + directory, all(sha(raw[directory + "/" + stream]) == receipt[stream + "SHA256"] for stream in ("stdout", "stderr")))
        check("command custody " + directory, receipt["processGroupEmpty"] is True and receipt["timedOut"] is False and receipt["cancelled"] is None and receipt["signals"] == [] and receipt["wallSeconds"] <= receipt["timeoutSeconds"])
        check("command exit " + directory, receipt["exitCode"] == (101 if directory.endswith("/full") else 0))
        check("command selected environment " + directory, receipt["environment"]["RUSTUP_TOOLCHAIN"] == "1.99.0" and receipt["environment"]["CARGO_NET_OFFLINE"] == "true" and receipt["environment"]["CARGO_BUILD_JOBS"] == "2" and receipt["environment"]["CARGO_INCREMENTAL"] == "0")
        commands.append({"directory": directory, "startedUTC": receipt["startedUTC"], "wallSeconds": receipt["wallSeconds"], "exitCode": receipt["exitCode"], "processGroupEmpty": receipt["processGroupEmpty"], "argv": receipt["argv"]})
    commands.sort(key=lambda x: x["startedUTC"])
    check("exact eleven-command order", [x["directory"] for x in commands] == ["tools/rustc", "tools/cargo", "tools/python", "control-original256/build", "control-original256/finite", "control-original256/harness-control", "candidate-dense/build", "candidate-dense/finite", "candidate-dense/harness-control", "control-original256/full", "candidate-dense/full"])
    for previous, current in zip(commands, commands[1:]):
        end = datetime.datetime.fromisoformat(previous["startedUTC"]) + datetime.timedelta(seconds=previous["wallSeconds"])
        check("sequential commands " + current["directory"], datetime.datetime.fromisoformat(current["startedUTC"]) >= end)
    check("nine preparation commands before admission", c["preparationGate"] == {"bothArmsPrepared": True, "closedPreparationCommands": 9, "fullAttemptsAtAdmission": 0})
    check("all custody closed and scratch removed", parsed["custody.json"] == c["cleanup"]["commandCustody"] and parsed["custody.json"]["pendingCommand"] is None and parsed["custody.json"]["provenClosedCommands"] == 11 and c["cleanup"]["ownedScratchRemoved"] is True and c["cleanup"]["commandCustodyUnresolved"] is False)
    check("actual compiler identity", raw["tools/rustc/stdout"].decode().startswith("rustc 1.99.0 (b940084d7 2026-09-28)") and "host: x86_64-unknown-linux-gnu" in raw["tools/rustc/stdout"].decode())
    summaries = []
    generated = {}
    for index, arm in enumerate(ARMS):
        source = runner.prepare_source(original, bool(index))
        generated[arm] = source
        source_record, delta = runner.base.source_record(original, source)
        check("regenerated all 133 source files " + arm, len(source) == 133 and source_record == parsed[arm + "/source.json"] == parsed["preflight/" + arm + "/source.json"])
        check("source patch reproduction " + arm, delta.encode() == raw[arm + "/changes.patch"] == raw["preflight/" + arm + "/changes.patch"])
        prepared = c["preparedProfiles"][index]
        profile = c["profiles"][index]
        check("source closure joins " + arm, source_record["sha256"] == prepared["sourceSHA256"] == profile["sourceSHA256"])
        check("preparation did not consume full attempts " + arm, prepared["fullAttemptsAtPreparation"] == 0 and prepared["finiteCount"] == (4 if index == 0 else 6) and prepared["harnessCount"] == 1)
        check("full original harness bytes " + arm, source["src/experimental_swift_reactor/campaign_harness.rs"] == (runner.base.INPUTS / "harness.rs").read_bytes())
        build = [strict(line) for line in raw[arm + "/build/stdout"].splitlines()]
        executable = [row for row in build if row.get("executable")]
        binary = parsed[arm + "/binary.json"]
        check("one actual optimized executable " + arm, len(executable) == 1 and executable[0]["executable"] == binary["path"] and executable[0]["profile"] == {"opt_level": "3", "debuginfo": 0, "debug_assertions": False, "overflow_checks": True, "test": True} and executable[0]["fresh"] is False)
        check("binary manifest joins " + arm, binary == prepared["binary"] == profile["binary"] and all(parsed[arm + "/" + phase + "/receipt.json"]["argv"][0] == binary["path"] for phase in ("finite", "harness-control", "full")))
        check("binary deliberately not retained " + arm, not any(name.endswith(Path(binary["path"]).name) for name in raw))
        geometry = runner.geometry_record(MemoryPath(raw[arm + "/finite/stdout"]), bool(index))
        check("compiled geometry raw reproduction " + arm, geometry == parsed[arm + "/geometry.json"] and sha(raw[arm + "/geometry.json"]) == prepared["geometrySHA256"])
        plan = geometry["plan"]
        operation = geometry["cache"].get("operation", geometry["cache"].get("operation_bound"))
        independent_sum = plan["category_ceiling_sum"] + plan["wasi_max"] + plan["shared"] + plan["floor"] + max(plan["execution_construction"], plan["frame_operation"] + operation)
        check("independent conservative geometry " + arm, independent_sum == plan["conservative_combined"] <= 268435456)
        check("finite exact count " + arm, f"test result: ok. {4 if index == 0 else 6} passed; 0 failed; 0 ignored" in raw[arm + "/finite/stdout"].decode())
        check("harness exact count " + arm, "test result: ok. 1 passed; 0 failed; 0 ignored" in raw[arm + "/harness-control/stdout"].decode())
        harness_events = events(raw[arm + "/harness-control/stdout"])
        check("harness actual two-call wiring", [x["payload"] for x in harness_events if x["event"] == "phase_begin"] == ["validation", "initialize", "corpus_1", "corpus_2"] and event(harness_events, "diagnostic_execution_complete") is True and event(harness_events, "cleanup_empty") is True)
        full = parsed[arm + "/full/receipt.json"]
        result = parsed[arm + "/result.json"]
        reclassified = runner.base.classify(MemoryPath(raw[arm + "/full/stdout"]), full)
        runner.validate_result(reclassified, full)
        check("full result raw reproduction " + arm, reclassified == result)
        prefix, prefix_bytes = runner.prefix_records(MemoryPath(raw[arm + "/full/stderr"]))
        runner.validate_prefix(result, prefix)
        check("full prefix raw reproduction " + arm, prefix == parsed[arm + "/prefix.json"] and prefix_bytes == raw[arm + "/prefix.records"])
        raw_events = events(raw[arm + "/full/stdout"])
        check("independent raw event join " + arm, raw_events == result["events"])
        check("selected budgets and grants unchanged " + arm, all(event(raw_events, k) == v for k, v in bounds.items()) and parsed[arm + "/selected-bounds.json"] == bounds == result["actualBounds"] == profile["actualBounds"])
        failure = event(raw_events, "runtime_failure")
        final_failure = event(raw_events, "final_failure")
        usage = event(raw_events, "final_cleanup_usage")
        check("independent sticky first failure " + arm, {**final_failure, "after_cleanup": None} == failure)
        recorded_cleanup = final_failure["after_cleanup"]
        check("earlier cleanup observation accounting " + arm,
              {k: v for k, v in recorded_cleanup.items() if k not in ("reservations", "elapsed_micros")} ==
              {k: v for k, v in usage.items() if k not in ("reservations", "elapsed_micros")} and
              recorded_cleanup["elapsed_micros"] <= usage["elapsed_micros"] and
              recorded_cleanup["reservations"]["live_tickets"] == 3 and
              recorded_cleanup["reservations"]["construction"]["current"] == plan["floor"] and
              recorded_cleanup["reservations"]["shared"]["current"] == plan["shared"] and
              recorded_cleanup["reservations"]["combined"]["current"] == plan["floor"] + plan["shared"] and
              all(recorded_cleanup["reservations"][k] == v for k, v in usage["reservations"].items()
                  if k not in ("construction", "shared", "combined", "live_tickets")))
        check("independent all resource cleanup " + arm, usage["cleanup_invariant"] is None and usage["reservations"]["live_tickets"] == 0 and all(v["current"] == 0 for group in ("reservations", "live") for v in usage[group].values() if isinstance(v, dict)))
        check("failed cleanup semantics preserved " + arm, event(raw_events, "cleanup_reservations_and_live_empty") is True and event(raw_events, "cleanup_empty") is False and event(raw_events, "diagnostic_execution_complete") is False)
        check("actual R1 ordinary frame failure " + arm, failure["kind"] == "FrameLimit" and failure["code"] == "swift_frame_depth" and failure["resource"] == "Frames" and failure["attempted"] == 65 and failure["limit"] == 64 and failure["observed_capacity"] is None and (failure["function"], failure["offset"]) == (24126, 4394310))
        check("no full oracle completion " + arm, result["complete"] is False and result["hostFeasibility"] is False and result["completeGuestObservations"] == result["nativeEqualPhases"] == [] and result["phaseOrder"] == ["validation", "initialize", "corpus_1"] and not any(x["event"] == "corpus_2" for x in raw_events))
        cumulative_keys = ("instructions", "instruction_fuel", "elapsed_micros", "execution_work", "cache_work", "host_calls")
        prev = {k: 0 for k in cumulative_keys}
        excess = []
        for observation in [*prefix["records"], usage]:
            check("independent R2 counters " + arm + " " + str(observation["instructions"]), all(type(observation[k]) is int and 0 <= observation[k] < (1 << 64) and observation[k] >= prev[k] for k in cumulative_keys) and observation["instruction_fuel"] - prev["instruction_fuel"] >= observation["instructions"] - prev["instructions"] and observation["instruction_fuel"] >= observation["instructions"])
            excess.append(observation["instruction_fuel"] - observation["instructions"])
            prev = observation
        check("no runtime time/fuel/work ceiling reached " + arm, all(usage[k] < bounds["run_budget"][k] for k in ("cache_work", "execution_work", "instruction_fuel", "host_calls")) and usage["elapsed_micros"] < 600_000_000 and usage["deadline_overshoot_micros"] == 0 and usage["deadline_origin"] == "Run")
        check("telemetry has no invalid observation " + arm, result["telemetry"]["issues"] == [] and all(x["valid"] is True and x["reset_count"] == 1 and x["invariant_mask"] == 0 and x["adapter_invalid"] == 0 and x["observer_invalid"] == 0 for x in result["telemetry"]["snapshots"]))
        summaries.append({"arm": arm, "sourceClosureSHA256": source_record["sha256"], "binaryManifest": binary, "binaryRehashedByThisReview": False, "finiteTestsPassed": prepared["finiteCount"], "harnessTestsPassed": 1, "geometry": geometry, "outcome": result["outcome"], "phaseOrder": result["phaseOrder"], "firstFailure": failure, "runtimeFinalUsage": usage, "fullCommandTiming": profile["timing"], "completeGuestObservations": [], "fuelMinusInstructionsAtPrefixesAndFinal": excess, "allCurrentLogicalReservationsAndLiveCountersZero": True})

    check("algorithm-only copied engine differences", sorted(n for n in generated[ARMS[0]] if generated[ARMS[0]][n] != generated[ARMS[1]][n]) == ["src/experimental/cache/borrowed.rs", "src/experimental_swift_reactor/cache.rs", "src/experimental_swift_reactor/cache_tests.rs"])
    frame_source = generated[ARMS[0]]["src/experimental_swift_reactor/frame_operations.rs"].decode()
    check("64 is a hard execution clamp", "let frame_limit = self.phase.operation.control.budget().frames.min(64);" in frame_source and '"swift_frame_depth"' in frame_source)
    harness = generated[ARMS[0]]["src/experimental_swift_reactor/campaign_harness.rs"].decode()
    check("same owner no intervening reset", '&& phase(&mut owner, Request::Corpus, "corpus_1", compare_native)\n            && phase(&mut owner, Request::Corpus, "corpus_2", compare_native)' in harness and harness.count("let started = Instant::now();") == 1)
    pairs = []
    for left, right in zip(parsed[ARMS[0] + "/prefix.json"]["records"], parsed[ARMS[1] + "/prefix.json"]["records"]):
        matched = ("threshold", "instructions", "instruction_fuel", "execution_work", "host_calls", "function", "offset")
        check("paired observed prefix " + str(left["threshold"]), all(left[k] == right[k] for k in matched))
        pairs.append({"instructions": left["instructions"], "matchedFields": {k: left[k] for k in matched}, "controlElapsedMicros": left["elapsed_micros"], "denseElapsedMicros": right["elapsed_micros"], "elapsedReductionPercent": 100 * (1 - right["elapsed_micros"] / left["elapsed_micros"]), "controlCacheWork": left["cache_work"], "denseCacheWork": right["cache_work"], "cacheDebitReductionPercent": 100 * (1 - right["cache_work"] / left["cache_work"])})
    check("immutable inputs unchanged after analysis", inputs == {n: record((HERE / n).read_bytes()) for n in inputs})
    check("all predecessor seals unchanged after analysis", before == verify_seals())
    check("no forbidden operation attempted", DENIED == [])

    save("artifact-inventory.json", {"files": inventory, "fileCount": len(inventory), "uncompressedBytes": sum(x["bytes"] for x in inventory.values())})
    save("checks.json", CHECKS)
    output = {
        "decision": "accept actual artifact as closed diagnostic comparison; no host-feasibility acceptance or production promotion",
        "exactRun": {"id": 40768719255, "attempt": 1, "jobIdFromRootHandoff": 123099796496, "head": HEAD, "tree": TREE, "artifactId": 12851363846},
        "inputs": inputs, "selectedPackets": before, "commands": commands, "arms": summaries, "pairedPrefixes": pairs,
        "firstCausalStop": "Both arms hit the hard 64-frame execution clamp during corpus_1 at function 24126 offset 4394310, attempted frame 65. It is not cache-work, instruction-fuel, execution-work, time, or combined-memory exhaustion.",
        "nextDecision": "Retain dense as a promising diagnostic candidate; root may select a bounded source investigation of frame representation/admission and recursion. Merely raising budget.frames cannot bypass min(64). Any deeper-frame experiment must re-establish finite pin/frame/owner geometry within the 256MiB envelope before another full attempt, under a newly explicit campaign; this review authorizes none.",
        "oracle": {"fieldCount": 11, "expectedFields": list(oracle), "expectedCorpora": 2, "completedCorporaPerArm": 0, "corpus2Reached": False},
        "scopeLimits": ["One sequential sample per arm; equal prefixes are matched observed counters/cursors, not proof of identical host entropy or all guest state.", "Prefix elapsed is cumulative Runtime-owner elapsed, excluding validation and process launch; includes observer overhead and work outside cache. No timer measures individual cache categories.", "Cache work credits are policy debit units, not CPU time. Credit share must not be reported as CPU share.", "Final instruction counts differ between arms; endpoint wall times are unpaired. Do not infer an overall workload speedup or numeric production winner.", "Raw wait4 RSS has a launcher high-water floor; no VM-attributable per-arm memory comparison. Logical reservations are distinct from process RSS.", "Remote test executables and scratch were removed before upload. Their hashes are CI-reported manifests joined to build/execution paths, not retained bytes independently rehashed by this review.", "Native/mobile runtime, published external FieldLog, signed OTA, customer and GA evidence remain pending; no production defaults changed."],
        "cleanup": c["cleanup"], "allChecksPassed": True,
    }
    save("review.json", output)
    readset = {str(p.relative_to(ROOT)): record(p.read_bytes()) for p in sorted(READS) if p.is_file()}
    save("readset.json", {"files": readset, "fileCount": len(readset), "bytes": sum(x["bytes"] for x in readset.values()), "sourceHead": HEAD, "sourceTree": TREE, "scope": "complete immutable files actually read by offline verifier; artifact member inventory recorded separately"})
    receipt = {"schema": 1, "command": "python3 -B verification/github-delivery-architecture-comparison/ci-review/review.py", "python": sys.version, "startedUTC": START_UTC, "elapsedSeconds": time.monotonic() - START, "internalDeadlineSeconds": 60, "checksPassed": len(CHECKS), "readsetSHA256": sha((HERE / "readset.json").read_bytes()), "artifactInventorySHA256": sha((HERE / "artifact-inventory.json").read_bytes()), "reviewSHA256": sha((HERE / "review.json").read_bytes()), "networkAndChildrenDenied": True, "processInventorySignalsAndWaitsDenied": True, "writesRestrictedToReviewLane": True, "forbiddenAttempts": DENIED, "newFullAttempts": 0, "compilerOrGuestExecutions": 0, "nativeOrCaptureProcessesStarted": False, "heldGroupsProbed": False, "gitWrites": False, "scratchCreated": False, "localVerifierCustody": "single tool-owned Python process; exec tool exit response is completion evidence; no child processes permitted", "workflowJobIdentityScope": "run/head/artifact independently bound by archive, metadata and log; job ID supplied by root handoff"}
    save("receipt.json", receipt)
    text = f"PASS: {len(CHECKS)} checks; all 67 artifact files; two clean FrameLimit diagnostic attempts; no oracle completion; no local compiler/guest/network/process probe.\n"
    (HERE / "review.stdout").write_text(text)
    (HERE / "review.stderr").write_text("")
    print(text, end="")


if __name__ == "__main__":
    main()

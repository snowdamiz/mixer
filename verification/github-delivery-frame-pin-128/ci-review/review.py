#!/usr/bin/env python3
"""Offline, bounded byte review of the single selected 128-frame CI artifact.

No compiler, guest, process discovery, signaling, network or Git writes.
"""
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
CANDIDATE = ROOT / "verification/swift-frame-pin-admission-candidate"
HEAD = "295f3f18a53459449f22253687bd2d0b2c09a0ed"
TREE = "294faafd3be568208a366ea66f85c5538a376ffa"
RUN = 40779075333
ARMS = ("control-frame128-pin128", "dense-frame128-pin128")
SEALS = {
    "swift-frame-pin-admission-candidate": "c5d0e8b29625e09bc5bc6ef73094edc4aebdc03ee5d4e27cafa34b5eda05bd6a",
    "swift-frame-pin-admission-independent": "e14f93bccb9ac5908b7707820456d4c2bab337aef53fc4be105e5285794b8c5f",
}
START = time.monotonic()
START_UTC = datetime.datetime.now(datetime.timezone.utc).isoformat()
CHECKS, DENIED, READS = [], [], set()


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
            if isinstance(value, (str, bytes, os.PathLike)) and not Path(os.fsdecode(value)).absolute().is_relative_to(HERE):
                raise RuntimeError("mutation outside review lane")


sys.addaudithook(audit)
socket.socket = forbidden
socket.create_connection = forbidden
subprocess.Popen = forbidden
for name in ("system", "fork", "forkpty", "posix_spawn", "posix_spawnp", "kill", "killpg", "wait", "waitpid", "wait3", "wait4", "popen"):
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


def events(data):
    return [strict(line.split("MIXER_EXACT ", 1)[1]) for line in data.decode().splitlines() if "MIXER_EXACT " in line]


def event(rows, name):
    values = [row["payload"] for row in rows if row["event"] == name]
    check("one raw event " + name, len(values) == 1)
    return values[0]


def verify_seals():
    summary = []
    for lane, expected in SEALS.items():
        directory = ROOT / "verification" / lane
        data = (directory / "seal.json").read_bytes()
        check("selected seal " + lane, sha(data) == expected)
        seal = strict(data)
        actual = {name: record((directory / name).read_bytes()) for name in seal["files"]}
        check("all sealed bytes " + lane, actual == seal["files"])
        check("sealed count and total " + lane, len(actual) == seal["fileCount"] and sum(v["bytes"] for v in actual.values()) == seal["totalBytes"])
        summary.append({"lane": lane, "sealSHA256": expected, "files": len(actual), "bytes": seal["totalBytes"]})
    return summary


def main():
    before = verify_seals()
    inputs = {n: record((HERE / n).read_bytes()) for n in ("artifact.zip", "job.log", "artifact-metadata.json")}
    metadata = strict((HERE / "artifact-metadata.json").read_bytes())
    check("artifact service digest", metadata["digest"] == "sha256:" + inputs["artifact.zip"]["sha256"])
    check("artifact service exact identity", metadata["workflow_run"]["id"] == RUN and metadata["workflow_run"]["head_sha"] == HEAD and metadata["name"].endswith(HEAD + "-" + str(RUN) + "-1"))
    with zipfile.ZipFile(HERE / "artifact.zip") as archive:
        entries = archive.infolist()
        check("unique safe bounded artifact files", len(entries) == len({x.filename for x in entries}) and 50 <= len(entries) <= 100 and all(not x.is_dir() and not Path(x.filename).is_absolute() and ".." not in Path(x.filename).parts for x in entries) and sum(x.file_size for x in entries) < 3_000_000)
        raw = {x.filename: archive.read(x.filename) for x in entries}
        check("ZIP CRC", archive.testzip() is None)
    inventory = {name: record(data) for name, data in sorted(raw.items())}
    parsed = {name: strict(data) for name, data in raw.items() if name.endswith(".json")}
    c = parsed["campaign.json"]
    check("campaign exact run", (c["githubSHA"], c["githubRunId"], c["githubRunAttempt"]) == (HEAD, str(RUN), "1"))
    check("closed bounded diagnostic campaign", c["status"] == "comparison-closed" and c["fullAttempts"] == c["maxFullAttempts"] == 2 and c["maxCommands"] == 11 and c["aggregateDeadlineSeconds"] == 2700)
    selection = strict((HERE.parent / "selection.json").read_bytes())
    check("explicit selected workflow", selection["profile"] == "paired-128-v1" and record((ROOT / selection["workflow"]["path"]).read_bytes()) == {k: selection["workflow"][k] for k in ("bytes", "sha256")} and (CANDIDATE / "workflow.yml").read_bytes() == (ROOT / selection["workflow"]["path"]).read_bytes())
    check("root committed identity receipts", (HERE.parent / "delivery2-committed-head.stdout").read_text().strip() == HEAD and (HERE.parent / "delivery2-committed-tree.stdout").read_text().strip() == TREE)
    committed = strict((HERE / "committed-source-check.json").read_bytes())
    check("independently verified committed source", committed["head"] == HEAD and committed["tree"] == TREE and committed["allBlobsMatch"] is True and committed["fileCount"] == len(committed["files"]) and all(record((ROOT / row["path"]).read_bytes()) == {k: row[k] for k in ("bytes", "sha256")} for row in committed["files"]))
    log = (HERE / "job.log").read_text()
    check("job checkout and artifact identity", HEAD in log and ("Artifact ID " + str(metadata["id"])) in log and inputs["artifact.zip"]["sha256"] in log)
    check("CI selected driver and pure methods", "verification/swift-frame-pin-admission-candidate/campaign.py run" in log and "Ran 39 tests in " in log)
    spec = importlib.util.spec_from_file_location("actual_ci_review_campaign128", CANDIDATE / "campaign.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    original, wasm, bindings = runner.inputs()
    check("frozen workload bytes", record(wasm) == parsed["preflight/check.json"]["artifact"] == {"bytes": 53777114, "sha256": "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"})
    check("original input bindings", bindings == c["inputBindings"] == parsed["preflight/check.json"]["inputBindings"])
    check("generator input bindings", runner.candidate_bindings() == c["candidateSourceBindings"] == parsed["preflight/check.json"]["candidateSourceBindings"])
    oracle = strict((runner.base.INPUTS / "native-observation.json").read_bytes())
    check("original 11-field oracle", len(oracle) == 11)
    bounds = runner.expected_bounds()
    b = bounds["run_budget"]
    check("selected complete limits", (b["frames"], b["active_pins"], b["cache_entries"], b["combined_bytes"], b["instruction_fuel"], b["execution_work"], b["cache_work"], b["deadline_ms"], bounds["wasi_budget"]["deadline_ms"]) == (128,128,256,268435456,1000000000,8000000000,768000000,600000,600000))
    commands = []
    for name, receipt in parsed.items():
        if not name.endswith("/receipt.json"):
            continue
        directory = name.rsplit("/", 1)[0]
        start = parsed[directory + "/started.json"]
        check("started receipt join " + directory, all(receipt[k] == v for k, v in start.items()))
        check("command raw output hashes " + directory, all(sha(raw[directory + "/" + stream]) == receipt[stream + "SHA256"] for stream in ("stdout", "stderr")))
        check("command custody " + directory, receipt["processGroupEmpty"] is True and receipt["timedOut"] is False and receipt["cancelled"] is None and receipt["signals"] == [] and receipt["wallSeconds"] <= receipt["timeoutSeconds"])
        check("selected command environment " + directory, all(receipt["environment"][k] == v for k, v in {"RUSTUP_TOOLCHAIN":"1.99.0","CARGO_NET_OFFLINE":"true","CARGO_BUILD_JOBS":"2","CARGO_INCREMENTAL":"0"}.items()))
        if not directory.endswith("/full"):
            check("preparation exit " + directory, receipt["exitCode"] == 0)
        commands.append({"directory": directory, "startedUTC": receipt["startedUTC"], "wallSeconds": receipt["wallSeconds"], "exitCode": receipt["exitCode"], "processGroupEmpty": receipt["processGroupEmpty"], "argv": receipt["argv"], "timeoutSeconds": receipt["timeoutSeconds"]})
    commands.sort(key=lambda x: x["startedUTC"])
    expected_order = ["tools/rustc", "tools/cargo", "tools/python"] + [a + "/" + p for a in ARMS for p in ("build","finite","harness-control")] + [a + "/full" for a in ARMS]
    check("exact eleven command order", [x["directory"] for x in commands] == expected_order)
    for previous, current in zip(commands, commands[1:]):
        end = datetime.datetime.fromisoformat(previous["startedUTC"]) + datetime.timedelta(seconds=previous["wallSeconds"])
        check("sequential commands " + current["directory"], datetime.datetime.fromisoformat(current["startedUTC"]) >= end)
    check("aggregate command bound", sum(x["wallSeconds"] for x in commands) < 2700)
    check("both preparations before full", c["preparationGate"] == {"bothArmsPrepared":True,"closedPreparationCommands":9,"fullAttemptsAtAdmission":0})
    check("final command closure and scratch removal", parsed["custody.json"] == c["cleanup"]["commandCustody"] and parsed["custody.json"]["pendingCommand"] is None and parsed["custody.json"]["provenClosedCommands"] == 11 and c["cleanup"]["ownedScratchRemoved"] is True and c["cleanup"]["commandCustodyUnresolved"] is False)
    check("actual compiler identity", raw["tools/rustc/stdout"].decode().startswith("rustc 1.99.0 (b940084d7 2026-09-28)") and "host: x86_64-unknown-linux-gnu" in raw["tools/rustc/stdout"].decode())
    summaries, generated = [], {}
    for index, arm in enumerate(ARMS):
        count = 9 + index
        source = runner.prepare_source(original, bool(index))
        generated[arm] = source
        source_record, delta = runner.base.source_record(original, source)
        check("regenerated complete source closure " + arm, source_record == parsed[arm+"/source.json"] == parsed["preflight/"+arm+"/source.json"])
        check("regenerated complete source patch " + arm, delta.encode() == raw[arm+"/changes.patch"] == raw["preflight/"+arm+"/changes.patch"])
        prepared, profile = c["preparedProfiles"][index], c["profiles"][index]
        check("source closure manifest joins " + arm, source_record["sha256"] == prepared["sourceSHA256"] == profile["sourceSHA256"] == selection["sourceClosures"]["dense" if index else "control"])
        check("finite preparation count " + arm, prepared["fullAttemptsAtPreparation"] == 0 and prepared["finiteCount"] == count and prepared["harnessCount"] == 1)
        check("unchanged original full harness " + arm, source["src/experimental_swift_reactor/campaign_harness.rs"] == (runner.base.INPUTS / "harness.rs").read_bytes())
        build = [strict(line) for line in raw[arm+"/build/stdout"].splitlines()]
        executable = [row for row in build if row.get("executable")]
        binary = parsed[arm+"/binary.json"]
        check("actual optimized overflow checked binary " + arm, len(executable)==1 and executable[0]["executable"]==binary["path"] and executable[0]["profile"]=={"opt_level":"3","debuginfo":0,"debug_assertions":False,"overflow_checks":True,"test":True} and executable[0]["fresh"] is False)
        check("binary manifest execution joins " + arm, binary==prepared["binary"]==profile["binary"] and all(parsed[arm+"/"+phase+"/receipt.json"]["argv"][0]==binary["path"] for phase in ("finite","harness-control","full")))
        check("owned executable deliberately removed " + arm, not any(name.endswith(Path(binary["path"]).name) for name in raw))
        geometry = runner.geometry_record(MemoryPath(raw[arm+"/finite/stdout"]), bool(index))
        check("compiled geometry reproduced " + arm, geometry==parsed[arm+"/geometry.json"] and sha(raw[arm+"/geometry.json"])==prepared["geometrySHA256"])
        plan = geometry["plan"]
        operation = geometry["cache"].get("operation",geometry["cache"].get("operation_bound"))
        independent_sum = plan["category_ceiling_sum"]+plan["wasi_max"]+plan["shared"]+plan["floor"]+max(plan["execution_construction"],plan["frame_operation"]+operation)
        check("independent geometry no double addition " + arm, independent_sum==plan["conservative_combined"]<=268435456)
        check("finite test exact count " + arm, f"test result: ok. {count} passed; 0 failed; 0 ignored" in raw[arm+"/finite/stdout"].decode())
        finite_text = raw[arm+"/finite/stdout"].decode()
        for marker in ("FRAMEPIN constructor_pin_payload_delta=1024 constructor_pin_work_delta=64 additional_allocations=0 additional_tickets=0", "FRAMEPIN frame_payload_delta=4096 frame_size=64 frame_construction_work_delta=0 additional_tickets=0", "FRAMEPIN integrated_constructor_allocation_failures=15 state_capacity_failures=6 cleanup_zero=true", "FRAMEPIN retained_actual_frames=128 release_slots=63,64,127 original_tickets_restored=true cleanup_zero=true", "FRAMEPIN above128_rejected=true original_nonce_owner_exhaustion_controls=true"):
            check("finite admitted representation marker " + arm + " " + marker.split()[1], finite_text.count(marker) == 1)
        check("harness test exact count " + arm, "test result: ok. 1 passed; 0 failed; 0 ignored" in raw[arm+"/harness-control/stdout"].decode())
        harness_events = events(raw[arm+"/harness-control/stdout"])
        check("harness two call wiring " + arm, [x["payload"] for x in harness_events if x["event"]=="phase_begin"]==["validation","initialize","corpus_1","corpus_2"] and event(harness_events,"diagnostic_execution_complete") is True and event(harness_events,"cleanup_empty") is True)
        full = parsed[arm+"/full/receipt.json"]
        result = parsed[arm+"/result.json"]
        reclassified = runner.base.classify(MemoryPath(raw[arm+"/full/stdout"]),full)
        runner.validate_result(reclassified,full)
        check("full result raw reproduction " + arm, reclassified==result)
        prefix,prefix_bytes = runner.prefix_records(MemoryPath(raw[arm+"/full/stderr"]))
        runner.validate_prefix(result,prefix)
        check("full prefix raw reproduction " + arm, prefix==parsed[arm+"/prefix.json"] and prefix_bytes==raw[arm+"/prefix.records"])
        rows = events(raw[arm+"/full/stdout"])
        check("independent lifecycle raw event join " + arm, rows==result["events"])
        check("all original budgets and grants retained " + arm, all(event(rows,k)==v for k,v in bounds.items()) and parsed[arm+"/selected-bounds.json"]==bounds==result["actualBounds"]==profile["actualBounds"])
        failure = result["firstFailure"]["payload"] if result["firstFailure"] else None
        final_failure,usage = event(rows,"final_failure"),event(rows,"final_cleanup_usage")
        check("independent sticky first failure " + arm, (final_failure is None if failure is None else {**final_failure,"after_cleanup":None}==failure))
        check("independent zero final logical ledger " + arm, usage["cleanup_invariant"] is None and usage["reservations"]["live_tickets"]==0 and all(v["current"]==0 for group in ("reservations","live") for v in usage[group].values() if isinstance(v,dict)))
        check("cleanup result preserves execution semantics " + arm, event(rows,"cleanup_reservations_and_live_empty") is True and event(rows,"cleanup_empty") is (failure is None) and event(rows,"diagnostic_execution_complete") is (failure is None))
        check("full exit reflects workload result " + arm, full["exitCode"]==(0 if failure is None else 101))
        if failure is None:
            check("both complete original 11-field corpus observations " + arm, result["nativeEqualPhases"]==["corpus_1","corpus_2"] and len(result["completeGuestObservations"])==2 and all(type(o["observation"]) is dict and o["observation"]==oracle and set(o["observation"])==set(oracle) for o in result["completeGuestObservations"]))
        else:
            check("ordinary resource failure retains all safeguards " + arm, failure["kind"] in runner.RESOURCE_FAILURE_KINDS and failure["code"]!="swift_run_unexpected_capacity" and failure["resource"] not in {*runner.STRUCTURAL_FAILURE_RESOURCES,"ExactCapacity"} and failure["code"] not in runner.STRUCTURAL_FAILURE_CODES and failure["observed_capacity"] is None and result["hostFeasibility"] is False)
        keys=("instructions","instruction_fuel","elapsed_micros","execution_work","cache_work","host_calls")
        previous={k:0 for k in keys}
        excess=[]
        for observation in [*prefix["records"],usage]:
            check("independent fuel and counters " + arm + " " + str(observation["instructions"]), all(type(observation[k]) is int and 0<=observation[k]<(1<<64) and observation[k]>=previous[k] for k in keys) and observation["instruction_fuel"]>=observation["instructions"] and observation["instruction_fuel"]-previous["instruction_fuel"]>=observation["instructions"]-previous["instructions"])
            excess.append(observation["instruction_fuel"]-observation["instructions"])
            previous=observation
        check("actual combined logical peak within unchanged cap " + arm, usage["reservations"]["combined"]["peak"]<=268435456)
        check("telemetry is valid " + arm, result["telemetry"]["issues"]==[] and all(x["valid"] is True and x["reset_count"]==1 and x["invariant_mask"]==0 and x["adapter_invalid"]==0 and x["observer_invalid"]==0 for x in result["telemetry"]["snapshots"]))
        summaries.append({"arm":arm,"sourceClosureSHA256":source_record["sha256"],"sourceFileCount":len(source),"binaryManifest":binary,"binaryRehashedByThisReview":False,"finiteTestsPassed":count,"harnessTestsPassed":1,"geometry":geometry,"outcome":result["outcome"],"phaseOrder":result["phaseOrder"],"firstFailure":failure,"runtimeFinalUsage":usage,"fullCommandTiming":profile["timing"],"completeGuestObservations":result["completeGuestObservations"],"nativeEqualPhases":result["nativeEqualPhases"],"fuelMinusInstructionsAtPrefixesAndFinal":excess,"allCurrentLogicalReservationsAndLiveCountersZero":True})
    harness=generated[ARMS[0]]["src/experimental_swift_reactor/campaign_harness.rs"].decode()
    check("original one owner two calls no reset", '&& phase(&mut owner, Request::Corpus, "corpus_1", compare_native)\n            && phase(&mut owner, Request::Corpus, "corpus_2", compare_native)' in harness and harness.count("let started = Instant::now();")==1)
    pairs=[]
    left_rows,right_rows=(parsed[a+"/prefix.json"]["records"] for a in ARMS)
    for left,right in zip(left_rows,right_rows):
        matched=("threshold","instructions","instruction_fuel","execution_work","host_calls","function","offset")
        mismatches=[k for k in matched if left[k]!=right[k]]
        row={"instructions":left["instructions"],"eligibleForMatchedObservedPrefixTiming":not mismatches,"guardMismatches":mismatches,"control":left,"dense":right}
        if not mismatches:
            row["elapsedReductionPercent"]=100*(1-right["elapsed_micros"]/left["elapsed_micros"])
            row["cacheDebitReductionPercent"]=100*(1-right["cache_work"]/left["cache_work"])
        pairs.append(row)
    end_keys=("instructions","instruction_fuel","execution_work","host_calls")
    end_mismatches=[k for k in end_keys if summaries[0]["runtimeFinalUsage"][k]!=summaries[1]["runtimeFinalUsage"][k]]
    for k in ("function","offset","attempted"):
        if (summaries[0]["firstFailure"] or {}).get(k)!=(summaries[1]["firstFailure"] or {}).get(k):
            end_mismatches.append(k)
    endpoint={"eligibleForEndpointTimingClaim":False,"guardMismatches":end_mismatches,"reason":"Endpoint work/cursor guards differ; no full-workload or endpoint speedup claim. Even matching counters would require complete original corpus evidence and further guard review."}
    check("inputs unchanged after analysis", inputs=={n:record((HERE/n).read_bytes()) for n in inputs})
    check("seals unchanged after analysis", before==verify_seals())
    check("no forbidden operation attempted", DENIED==[])
    save("artifact-inventory.json",{"files":inventory,"fileCount":len(inventory),"uncompressedBytes":sum(x["bytes"] for x in inventory.values())})
    save("review.json",{"schema":1,"decision":"accept closed diagnostic evidence; root owns next selection; no production or GA promotion","exactRun":{"id":RUN,"attempt":1,"jobId":123135853660,"head":HEAD,"tree":TREE,"artifactId":metadata["id"]},"inputs":inputs,"selectedPackets":before,"commands":commands,"arms":summaries,"pairedPrefixes":pairs,"endpointComparison":endpoint,"oracle":{"fieldCount":11,"expectedFields":list(oracle),"expectedCorpora":2},"cleanup":c["cleanup"],"allChecksPassed":True,"scopeLimits":["One sequential sample per arm; matched observed prefixes do not prove identical host entropy or all guest state.","No endpoint speedup claim unless all workload comparison guards hold; policy work credits are not CPU time.","Raw wait4 RSS has known launcher high-water floor; no per-arm VM memory comparison.","Executable manifests are CI reported and checked there; executable bytes removed before artifact upload and not independently rehashed here.","Native/mobile runtime, physical devices, external immutable FieldLog release, signed OTA, customer use and GA remain pending; production defaults unchanged."]})
    readset={str(p.relative_to(ROOT)):record(p.read_bytes()) for p in sorted(READS) if p.is_file()}
    save("readset.json",{"files":readset,"fileCount":len(readset),"bytes":sum(x["bytes"] for x in readset.values()),"sourceHead":HEAD,"sourceTree":TREE})
    save("receipt.json",{"schema":1,"command":"python3 -B verification/github-delivery-frame-pin-128/ci-review/review.py","python":sys.version,"startedUTC":START_UTC,"elapsedSeconds":time.monotonic()-START,"internalDeadlineSeconds":60,"checksPassed":len(CHECKS),"readsetSHA256":sha((HERE/"readset.json").read_bytes()),"artifactInventorySHA256":sha((HERE/"artifact-inventory.json").read_bytes()),"reviewSHA256":sha((HERE/"review.json").read_bytes()),"networkAndChildrenDenied":True,"processInventorySignalsAndWaitsDenied":True,"writesRestrictedToReviewLane":True,"forbiddenAttempts":DENIED,"newFullAttempts":0,"compilerOrGuestExecutions":0,"nativeOrCaptureProcessesStarted":False,"heldGroupsProbed":False,"gitWrites":False,"scratchCreated":False})
    output=f"PASS: {len(CHECKS)} offline checks; {len(inventory)} artifact files; two full attempts; no local compiler, guest, network, process probe or Git write.\n"
    (HERE/"review.stdout").write_text(output)
    (HERE/"review.stderr").write_text("")
    print(output,end="")


if __name__=="__main__":
    try:
        main()
    finally:
        save("checks.json",CHECKS)

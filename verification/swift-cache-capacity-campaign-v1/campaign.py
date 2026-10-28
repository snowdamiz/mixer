#!/usr/bin/env python3
"""Bounded isolated CI experiment; original validator, owner, oracle and cleanup.

`check` is pure source/data work. `run` is limited to a GitHub-hosted CI runner.
No local guest, compiler, process-custody or native execution path is provided.
"""
import argparse
import datetime
import difflib
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "inputs"
ARTIFACT_HASH = "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"
ARTIFACT_BYTES = 53_777_114
PRIMARY = (("baseline", 64, 64_000_000), ("work-only", 64, 128_000_000),
           ("capacity-128", 128, 64_000_000), ("capacity-256", 256, 64_000_000))
PREFIX = "experimental_swift_reactor::execution::frame_operations::memory_growth_operations::lifecycle::tests::exact_diagnostic::"
BASELINE_CLOSURE = "16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd"
CAMPAIGN_SECONDS = 1_080
COMMAND_DEADLINE = None
CANCEL_REQUESTED = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def replace(source, old, new, count=1):
    require(source.count(old) == count, "changed source anchor: " + old)
    return source.replace(old, new)


def inputs():
    bindings = json.loads((INPUTS / "bindings.json").read_text())
    for name, row in bindings.items():
        data = (INPUTS / name).read_bytes()
        require(len(data) == row["bytes"] and sha(data) == row["sha256"], "input changed: " + name)
    manifest = json.loads((INPUTS / "source-manifest.json").read_text())
    with tarfile.open(INPUTS / "source.tar.gz", "r:gz") as archive:
        members = archive.getmembers()
        require(len(members) == len(manifest) == 132, "source member count")
        require(len({m.name for m in members}) == 132, "duplicate source member")
        require(all(m.isfile() and not Path(m.name).is_absolute() and ".." not in Path(m.name).parts for m in members), "source member path")
        source = {m.name: archive.extractfile(m).read() for m in members}
    require({n: sha(b) for n, b in source.items()} == manifest, "accepted observer source manifest")
    with gzip.open(INPUTS / "fieldlog-reactor.wasm.gz", "rb") as stream:
        artifact = stream.read(ARTIFACT_BYTES + 1)
        require(len(artifact) == ARTIFACT_BYTES and sha(artifact) == ARTIFACT_HASH, "exact full Swift artifact")
        require(stream.read(1) == b"", "artifact trailing data")
    return source, artifact, bindings


def parameterize(source, residents, work):
    require(residents in (64, 128, 256) and work in (64_000_000, 128_000_000), "unsupported profile")
    out = dict(source)
    def edit(name, transform):
        out[name] = transform(out[name].decode()).encode()
    # Private copied test binary only. All four builds use u16 link encoding.
    # The fixed bucket count/hash and debit sequence remain unchanged.
    def cache(s):
        s = replace(s, "const RESIDENT_LINKS: usize = 64;", f"const RESIDENT_LINKS: usize = {residents};")
        s = replace(s, "const RESIDENT_INDEX_BYTES: usize = RESIDENT_BUCKETS + RESIDENT_LINKS;",
                    "const RESIDENT_INDEX_CELLS: usize = RESIDENT_BUCKETS + RESIDENT_LINKS;\nconst RESIDENT_INDEX_BYTES: usize = RESIDENT_INDEX_CELLS * size_of::<u16>();")
        for old, new, count in [
            ("index: &'a mut [u8]", "index: &'a mut [u16]", 1),
            ("next: u8", "next: u16", 2), ("node: u8", "node: u16", 1),
            ("seen: u64", "seen: [u64; RESIDENT_LINKS / 64]", 1),
            ("index: &'static [u8]", "index: &'static [u16]", 1),
            ("index: &'static mut [u8]", "index: &'static mut [u16]", 1),
            ("index_reborrow: &'static mut [u8]", "index_reborrow: &'static mut [u16]", 1),
            ("index: &[u8]", "index: &[u16]", 1),
            ("index.len() != RESIDENT_INDEX_BYTES", "index.len() != RESIDENT_INDEX_CELLS", 1),
            ("let mut seen = 0u64;", "let mut seen = [0u64; RESIDENT_LINKS / 64];", 1),
            ("let bit = 1u64 << slot;", "let bit = 1u64 << (slot % 64);", 1),
            ("if seen & bit != 0", "if seen[slot / 64] & bit != 0", 1),
            ("seen |= bit;", "seen[slot / 64] |= bit;", 1),
            ("reserve(&mut partial.index, RESIDENT_INDEX_BYTES", "reserve(&mut partial.index, RESIDENT_INDEX_CELLS", 1),
            ("for _ in 0..RESIDENT_INDEX_BYTES", "for _ in 0..RESIDENT_INDEX_CELLS", 1),
            ("(slot + 1) as u8", "(slot + 1) as u16", 1),
            ("resident_index(cache: &SwiftFunctionCache) -> &[u8]", "resident_index(cache: &SwiftFunctionCache) -> &[u16]", 1),
            ("cell: usize, value: u8", "cell: usize, value: u16", 1),
        ]:
            s = replace(s, old, new, count)
        s = s.replace("Vec<u8>", "Vec<u16>") # All Vec<u8> occurrences here are index owner/transfer inventories.
        s = s.replace("[bool; 64]", "[bool; RESIDENT_LINKS]")
        s = s.replace("An exactly64-node chain", "An exactly-capacity-node chain")
        return s
    edit("src/experimental_swift_reactor/cache.rs", cache)
    edit("src/experimental_swift_reactor/control.rs", lambda s: replace(replace(replace(s,
         "MAX_RESERVATION_TICKETS: usize = 86;", f"MAX_RESERVATION_TICKETS: usize = {residents + 22};"),
         "cache_entries: 64,", f"cache_entries: {residents},"), "cache_work: 64_000_000,", f"cache_work: {work},"))
    edit("src/experimental/cache/mod.rs", lambda s: replace(s, "const MAX_ENTRIES: usize = 64;", f"const MAX_ENTRIES: usize = {residents};"))
    # Shared planning array/recount uses MAX_ENTRIES; each real slot is still
    # visited and charged. This isolated closure is never a published library.
    def tests(s):
        s = replace(s, "assert_eq!(index.len(), 192);", f"assert_eq!(index.len(), {128 + residents});")
        s = replace(s, "let mut seen = [false; 64];", f"let mut seen = [false; {residents}];")
        s = replace(s, 'assert!(count < 64, "unbounded or cyclic chain");', f'assert!(count < {residents}, "unbounded or cyclic chain");')
        start = s.index("fn plan_reuse_profile_envelopes_without_guest_execution()")
        end = s.index("\n#[test]", start)
        old = s[start:end]
        new = old.replace("fixture(0,&[0,0x0b],100)", f"fixture(0,&[0,0x0b],{residents + 40})")
        new = new.replace("34..98", f"34..{34 + residents}")
        new = new.replace("resident.live.cache_entries.current,64", f"resident.live.cache_entries.current,{residents}")
        new = new.replace("resident.reservations.live_tickets,85", f"resident.reservations.live_tickets,{residents + 21}")
        new = new.replace("report.usage.reservations.peak_tickets<=86", "report.usage.reservations.peak_tickets<=MAX_RESERVATION_TICKETS")
        s = replace(s, old, new)
        return s + "\n" + (INPUTS / "adapter.rs").read_text() + "\n" + (HERE / "campaign-controls.rs").read_text()
    edit("src/experimental_swift_reactor/cache_tests.rs", tests)
    # Keep original target/observation decoder and ownership path byte for byte.
    # Copy to a fixed relative source path so the source digest is portable.
    out["src/experimental_swift_reactor/campaign_harness.rs"] = (INPUTS / "harness.rs").read_bytes()
    out["src/experimental_swift_reactor/lifecycle_tests.rs"] += b'\ninclude!("campaign_harness.rs");\n'
    return out


def materialize(source, destination):
    for name, data in source.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def source_record(original, candidate):
    manifest = {n: sha(b) for n, b in sorted(candidate.items())}
    changed = [n for n in manifest if candidate[n] != original.get(n)]
    diff = "".join("".join(difflib.unified_diff(original.get(n, b"").decode().splitlines(True),
         candidate[n].decode().splitlines(True), fromfile="accepted/" + n, tofile="campaign/" + n)) for n in changed)
    return {"sha256": sha((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()), "files": manifest, "changed": changed}, diff


def check(output):
    original, artifact, bindings = inputs()
    result = {"schema": 1, "model": "gpt-6-astra", "reasoningEffort": "xhigh", "sourcePolicyRevision": "b6410e917fab899731dece2678fe2ade2e854464",
              "baselineClosureBeforeAcceptedObserver": BASELINE_CLOSURE, "inputBindings": bindings,
              "artifact": {"bytes": len(artifact), "sha256": sha(artifact)}, "profiles": [],
              "execution": "pure source/data checks only; compiler, finite controls and full corpus pending"}
    for name, residents, work in PRIMARY:
        record, diff = source_record(original, parameterize(original, residents, work))
        save(output / name / "source.json", record)
        (output / name / "changes.patch").write_text(diff)
        result["profiles"].append({"name": name, "residents": residents, "cacheWork": work, "sourceSHA256": record["sha256"]})
    save(output / "check.json", result)
    return result


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def request_cancel(signum, _frame):
    global CANCEL_REQUESTED
    CANCEL_REQUESTED = signal.Signals(signum).name


def ensure_command_budget(seconds):
    require(CANCEL_REQUESTED is None, "campaign cancelled: " + str(CANCEL_REQUESTED))
    # Reserve both five-second cleanup windows plus ten seconds for receipts.
    require(COMMAND_DEADLINE is not None and time.monotonic() + seconds + 20 < COMMAND_DEADLINE,
            "aggregate campaign deadline: next bounded command cannot fit")


def command(argv, cwd, env, directory, seconds):
    """Own one new process group; wait4 gives that child's CPU/RSS, not prior compiles."""
    ensure_command_budget(seconds)
    directory.mkdir(parents=True, exist_ok=False)
    row = {"argv": argv, "cwd": str(cwd), "environment": env, "timeoutSeconds": seconds,
           "cleanupSeconds": 10, "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save(directory / "started.json", row)
    started = time.monotonic()
    timed_out = False
    cancelled = None
    signals = []
    with (directory / "stdout").open("wb") as stdout, (directory / "stderr").open("wb") as stderr:
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        row["pid"] = child.pid
        save(directory / "started.json", row)
        status = usage = None
        while status is None:
            pid, observed, ru = os.wait4(child.pid, os.WNOHANG)
            if pid:
                status, usage = observed, ru
                break
            if CANCEL_REQUESTED is not None:
                cancelled = CANCEL_REQUESTED
                break
            if time.monotonic() - started >= seconds:
                timed_out = True
                break
            time.sleep(.05)
        # No global process inventory: only the newly owned remote process group.
        if timed_out or cancelled or group_alive(child.pid):
            for sig in (signal.SIGTERM, signal.SIGKILL):
                if not group_alive(child.pid):
                    break
                os.killpg(child.pid, sig)
                signals.append(sig.name)
                end = time.monotonic() + 5
                while time.monotonic() < end:
                    if status is None:
                        pid, observed, ru = os.wait4(child.pid, os.WNOHANG)
                        if pid:
                            status, usage = observed, ru
                    if not group_alive(child.pid):
                        break
                    time.sleep(.05)
        empty = not group_alive(child.pid)
        child.returncode = os.waitstatus_to_exitcode(status) if status is not None else -999
    row.update(exitCode=child.returncode, timedOut=timed_out, cancelled=cancelled, signals=signals, processGroupEmpty=empty,
               wallSeconds=time.monotonic() - started, userSeconds=usage.ru_utime if usage else None,
               systemSeconds=usage.ru_stime if usage else None, peakRSSBytes=usage.ru_maxrss * 1024 if usage else None,
               peakRSSScope="wait4 actual child; Linux ru_maxrss KiB; includes that command's descendants",
               stdoutSHA256=sha((directory / "stdout").read_bytes()), stderrSHA256=sha((directory / "stderr").read_bytes()))
    save(directory / "receipt.json", row)
    require(empty, "owned remote process group unresolved; stop resource reuse")
    require(cancelled is None, "campaign cancelled: " + str(cancelled))
    return row


def classify(path, row):
    spec = importlib.util.spec_from_file_location("campaign_telemetry", INPUTS / "telemetry.py")
    telemetry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(telemetry)
    events = []
    for line in path.read_text().splitlines():
        at = line.find("MIXER_EXACT ")
        if at >= 0:
            events.append(telemetry.strict_json(line[at + len("MIXER_EXACT "):]))
    def one(event):
        values = [e["payload"] for e in events if e["event"] == event]
        require(len(values) <= 1, "duplicate lifecycle event: " + event)
        return values[0] if values else None
    clean = one("final_cleanup_usage")
    consuming = bool(clean and clean["cleanup_invariant"] is None and
        all(v["current"] == 0 for v in clean["reservations"].values() if type(v) is dict) and
        clean["reservations"]["live_tickets"] == 0 and all(v["current"] == 0 for v in clean["live"].values()))
    failures = [e for e in events if e["event"] in ("validation_failure", "adoption_failure", "construction_failure", "runtime_failure")]
    native = [e["payload"] for e in events if e["event"] == "guest_output_native_equal"]
    expected = telemetry.strict_json((INPUTS / "native-observation.json").read_text())
    initialized = one("initialize")
    previous = initialized["stdout"] if initialized is not None else ""
    observations = []
    for phase in ("corpus_1", "corpus_2"):
        snapshot = one(phase)
        if phase not in native:
            continue
        require(snapshot is not None and type(previous) is str and type(snapshot["stdout"]) is str and snapshot["stdout"].startswith(previous), "cumulative guest stdout mismatch")
        suffix = snapshot["stdout"][len(previous):]
        observation = telemetry.strict_json(suffix)
        require(type(observation) is dict and set(observation) == set(expected) and all(type(observation[k]) is type(v) and observation[k] == v for k, v in expected.items()), "complete native oracle mismatch")
        observations.append({"phase": phase, "rawSuffix": suffix, "observation": observation})
        previous = snapshot["stdout"]
    phases = []
    prior = {"instructions": 0, "cache_work": 0, "execution_work": 0, "host_calls": 0}
    for phase in ("constructed", "initialize", "corpus_1", "corpus_2", "before_cleanup"):
        snapshot = one(phase)
        if snapshot is None:
            continue
        usage = snapshot["usage"]
        counters = {k: usage[k] for k in prior}
        phases.append({"phase": phase, "cumulative": counters,
                       "delta": {k: counters[k] - prior[k] for k in prior},
                       "cache": snapshot["cache"], "live": usage["live"],
                       "logicalReservations": usage["reservations"], "elapsedMicros": usage["elapsed_micros"],
                       "nativeEqual": phase in native})
        prior = counters
    summary = {"events": events, "telemetry": telemetry.classify(path, events),
               "firstFailure": failures[0] if failures else None, "nativeEqualPhases": native,
               "completeGuestObservations": observations,
               "phaseMetrics": phases,
               "consumingCleanup": consuming, "complete": one("diagnostic_execution_complete") is True,
               "phaseOrder": [e["payload"] for e in events if e["event"] == "phase_begin"]}
    summary["hostFeasibility"] = (summary["complete"] and consuming and native == ["corpus_1", "corpus_2"] and summary["telemetry"]["status"] == "valid" and
        row["exitCode"] == 0 and not row["timedOut"] and row["processGroupEmpty"] and not failures)
    return summary


def run(output, combined):
    global COMMAND_DEADLINE
    require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted" and platform.system() == "Linux", "full campaign requires selected GitHub-hosted Linux CI; local execution remains held")
    require(not output.exists(), "fresh campaign output required; no retries/resume")
    COMMAND_DEADLINE = time.monotonic() + CAMPAIGN_SECONDS
    signal.signal(signal.SIGTERM, request_cancel)
    signal.signal(signal.SIGINT, request_cancel)
    output.mkdir(parents=True)
    original, artifact, bindings = inputs()
    check(output / "preflight")
    # Input/output are diagnostic harness memory, separately reported from VM ledger.
    scratch = output / "scratch"
    scratch.mkdir()
    target_input = scratch / "fieldlog-reactor.wasm"
    target_input.write_bytes(artifact)
    del artifact
    env = {k: os.environ[k] for k in ("HOME", "PATH", "RUSTUP_HOME", "CARGO_HOME", "LANG") if k in os.environ}
    env.update(CARGO_INCREMENTAL="0", CARGO_NET_OFFLINE="true", CARGO_BUILD_JOBS="2", RUSTUP_TOOLCHAIN="1.99.0",
               MIXER_EXACT_REACTOR_INPUT=str(target_input), TMPDIR=str(scratch))
    campaign = {"schema": 1, "model": "gpt-6-astra", "reasoningEffort": "xhigh", "githubSHA": os.environ.get("GITHUB_SHA"),
                "githubRunId": os.environ.get("GITHUB_RUN_ID"), "githubRunAttempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                "environment": platform.platform(), "machine": platform.machine(), "profiles": [], "maxFullAttempts": 5,
                "inputBindings": bindings, "fullAttempts": 0, "historicalTimingsComparable": False,
                "aggregateDeadlineSeconds": CAMPAIGN_SECONDS,
                "scope": "diagnostic host feasibility only; native/public/signed OTA/FieldLog publication/GA pending"}
    save(output / "campaign.json", campaign)
    safe_to_remove = True
    try:
        for tool, argv in (("rustc", ["rustc", "-vV"]), ("cargo", ["cargo", "-V"]), ("python", [sys.executable, "--version"])):
            r = command(argv, HERE, env, output / "tools" / tool, 15)
            require(r["exitCode"] == 0, "tool identity failed")
        profiles = list(PRIMARY)
        if combined:
            # Explicit root-selected fifth run needs a previous four-run result,
            # not a new invocation that silently reruns the primaries.
            raise RuntimeError("combined run is not preselected; choose it only from this campaign's actual primary results")
        for name, residents, work in profiles:
            phase = output / name
            phase.mkdir()
            source = parameterize(original, residents, work)
            record, diff = source_record(original, source)
            save(phase / "source.json", record)
            (phase / "changes.patch").write_text(diff)
            crate = scratch / name / "vm"
            materialize(source, crate)
            target = scratch / name / "target"
            child_env = env | {"CARGO_TARGET_DIR": str(target)}
            build = command(["cargo", "test", "--lib", "--no-run", "--release", "--locked", "--offline", "--no-default-features", "--features", "experimental-swift-reactor", "--message-format=json"], crate, child_env, phase / "build", 180)
            require(build["exitCode"] == 0 and not build["timedOut"], "compile failed: " + name)
            candidates = [json.loads(line)["executable"] for line in (phase / "build" / "stdout").read_text().splitlines()
                          if line.startswith("{") and json.loads(line).get("reason") == "compiler-artifact" and json.loads(line).get("executable")]
            require(len(candidates) == 1, "one test executable required")
            binary = Path(candidates[0])
            executable = {"bytes": binary.stat().st_size, "sha256": sha(binary.read_bytes())}
            for label, test in (("finite", "::campaign_"), ("harness-control", PREFIX + "exact_reactor_harness_control")):
                control = command([str(binary), test, "--nocapture", "--test-threads=1"], crate, child_env, phase / label, 90)
                require(control["exitCode"] == 0 and not control["timedOut"], "finite control failed: " + name + "/" + label)
                stdout = (phase / label / "stdout").read_text()
                require(("4 passed" if label == "finite" else "1 passed") in stdout, "missing selected control execution")
            require(campaign["fullAttempts"] < 5, "full attempt cap")
            ensure_command_budget(170)
            campaign["fullAttempts"] += 1
            save(output / "campaign.json", campaign) # Count before spawning; failures consume an attempt.
            full = command([str(binary), PREFIX + "exact_reactor_target_once", "--exact", "--nocapture", "--test-threads=1"], crate, child_env, phase / "full", 170)
            result = classify(phase / "full" / "stdout", full)
            save(phase / "result.json", result)
            budget = next((e["payload"] for e in result["events"] if e["event"] == "run_budget"), None)
            require(budget is not None and (budget["cache_entries"], budget["cache_work"], budget["active_pins"]) == (residents, work, 64), "executed profile differs from selected profile")
            unchanged = all((crate / n).read_bytes() == b for n, b in source.items()) and sha(target_input.read_bytes()) == ARTIFACT_HASH
            row = {"name": name, "residents": residents, "cacheWork": work, "sourceSHA256": record["sha256"], "binary": executable,
                   "result": str((phase / "result.json").relative_to(output)), "hostFeasibility": result["hostFeasibility"],
                   "consumingCleanup": result["consumingCleanup"], "sourceAndInputUnchanged": unchanged,
                   "firstFailure": result["firstFailure"], "timing": {k: full[k] for k in ("wallSeconds", "userSeconds", "systemSeconds", "peakRSSBytes")}}
            campaign["profiles"].append(row)
            save(output / "campaign.json", campaign)
            require(unchanged, "source/input changed during experiment")
            require(result["consumingCleanup"], "consuming cleanup unresolved; stop resource reuse")
            require(result["telemetry"]["status"] == "valid", "supplementary attribution invalid; stop comparison")
            # All owned groups are absent before removing only this run's scratch.
            shutil.rmtree(scratch / name)
        campaign["status"] = "primary-comparison-complete"
        campaign["nextDecision"] = "root selects smallest demonstrated adequate profile with headroom, optional fifth combined candidate if justified, or different hypothesis; no production default change"
    except Exception as error:
        campaign["status"] = "stopped"
        campaign["error"] = str(error)
        safe_to_remove = "process group unresolved" not in str(error)
        raise
    finally:
        if safe_to_remove:
            shutil.rmtree(scratch)
        campaign["cleanup"] = {"ownedScratchRemoved": not scratch.exists(), "nativeOrLocalCustodyProcessesStarted": False}
        save(output / "campaign.json", campaign)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "run"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "check":
        check(args.output.resolve())
    else:
        run(args.output.resolve(), False)


if __name__ == "__main__":
    main()

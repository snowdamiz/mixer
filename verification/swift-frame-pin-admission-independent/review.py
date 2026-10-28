#!/usr/bin/env python3
"""Independent pure source and runner review; no compiler/runtime/process probes."""
import ast
import contextlib
import copy
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import random
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRODUCER = HERE.parent / "swift-frame-pin-admission-candidate"
SEAL_SHA = "c5d0e8b29625e09bc5bc6ef73094edc4aebdc03ee5d4e27cafa34b5eda05bd6a"
READS = set()
CHECKS = []
DENIED = []
FD_PATHS = {}
START = time.monotonic()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def record(data):
    return {"bytes": len(data), "sha256": sha(data)}

def confined(name, dir_fd=None):
    if not isinstance(name, (str, bytes, os.PathLike)):
        raise AssertionError("unbound descriptor mutation")
    path = Path(os.fsdecode(name))
    if not path.is_absolute() and dir_fd not in (None, -1):
        if dir_fd not in FD_PATHS:
            raise AssertionError("unbound mutation directory descriptor")
        path = FD_PATHS[dir_fd] / path
    path = path.resolve()
    if not path.is_relative_to(HERE):
        raise AssertionError("mutation outside independent review: " + str(path))

def blocked(*args, **kwargs):
    DENIED.append("process/network/signal/wait")
    raise AssertionError("pure independent review forbids process/network/signal/wait")

def audit(event, args):
    if event.startswith(("subprocess.", "socket.", "pty.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.kill", "os.killpg", "os.chdir",
    }:
        raise AssertionError("pure audit denied " + event)
    if event == "open":
        name, mode, flags = args
        writing = isinstance(mode, str) and any(c in mode for c in "wax+")
        writing |= isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing:
            confined(name)
        elif isinstance(name, (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(name)).resolve()
            if path.is_relative_to(ROOT) and not path.is_relative_to(HERE):
                READS.add(path)
    if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.utime", "os.truncate"}:
        fd = args[1] if event in {"os.remove", "os.rmdir"} and len(args) > 1 else None
        confined(args[0], fd)
    if event in {"os.rename", "os.link", "os.symlink"}:
        confined(args[0]); confined(args[1])

sys.addaudithook(audit)
# Track only descriptors opened by this pure reviewer. This supports Python's
# safe relative-dirfd rmtree audit without OS/process/descriptor probes.
raw_os_open, raw_os_close = os.open, os.close
def tracked_os_open(path, flags, mode=0o777, *, dir_fd=None):
    resolved = Path(os.fsdecode(path))
    if not resolved.is_absolute() and dir_fd is not None:
        if dir_fd not in FD_PATHS:
            raise AssertionError("unbound read directory descriptor")
        resolved = FD_PATHS[dir_fd] / resolved
    resolved = resolved.resolve()
    fd = raw_os_open(path, flags, mode, dir_fd=dir_fd)
    FD_PATHS[fd] = resolved
    return fd
def tracked_os_close(fd):
    result = raw_os_close(fd)
    FD_PATHS.pop(fd, None)
    return result
os.open, os.close = tracked_os_open, tracked_os_close
socket.socket = blocked
socket.create_connection = blocked
subprocess.Popen = blocked
for name in ("system", "fork", "forkpty", "posix_spawn", "posix_spawnp", "kill", "killpg", "wait", "waitpid", "wait3", "wait4", "popen"):
    if hasattr(os, name):
        setattr(os, name, blocked)
signal.signal = blocked
time.sleep = blocked

def save(name, value):
    dest = HERE / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def check(name, value):
    assert time.monotonic() - START < 60, "independent pure check exceeded 60 seconds"
    CHECKS.append({"check": name, "passed": bool(value)})
    assert value, name

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def bind_seal():
    raw = (PRODUCER / "seal.json").read_bytes()
    check("frozen producer seal SHA", sha(raw) == SEAL_SHA)
    seal = json.loads(raw)
    check("frozen producer exact 32-member 439453-byte closure", seal["fileCount"] == len(seal["files"]) == 32 and seal["totalBytes"] == 439453)
    total = 0
    for name, expected in seal["files"].items():
        actual = (PRODUCER / name).read_bytes()
        check("producer sealed member " + name, record(actual) == expected)
        total += len(actual)
    check("producer total bytes recomputed", total == seal["totalBytes"])
    return seal

def source_review(campaign):
    original, artifact, _ = campaign.inputs()
    candidate = campaign.candidate_module()
    actual = json.loads((ROOT / "verification/github-delivery-architecture-comparison/ci-review/review.json").read_text())
    actual_seal = json.loads((ROOT / "verification/github-delivery-architecture-comparison/ci-review/seal.json").read_text())
    check("actual review member binding", record((ROOT / "verification/github-delivery-architecture-comparison/ci-review/review.json").read_bytes()) == actual_seal["files"]["review.json"])
    closure_expected = ["92e2f54a8b31116d1ba3a0ae77f3b8b7abf901ab0ec07b40feef2ecd49c1dcd1", "e3a4a90378a90d8cc5d22244c5ae345d30e57670cc396098c4370872a9a2284b"]
    sources = []
    for name, algorithm, finite_filter, count in campaign.PROFILES:
        previous = candidate.prior.parameterize(original, algorithm)
        source = campaign.prepare_source(original, algorithm)
        manifest, delta = campaign.base.source_record(original, source)
        prior_manifest, _ = campaign.base.source_record(original, previous)
        check(name + " closure matches freeze", manifest["sha256"] == closure_expected[int(algorithm)])
        check(name + " exact actual prior source", prior_manifest["sha256"] == actual["arms"][int(algorithm)]["sourceClosureSHA256"])
        save(name + "/source.json", manifest)
        (HERE / name / "changes.patch").write_text(delta)
        changed = {key for key in source if previous.get(key) != source[key]}
        expected = {"control.rs", "frame_operations.rs", "cache_tests.rs", "frame_operations_tests.rs", "execution_tests.rs"}
        if algorithm: expected.add("cache.rs")
        check(name + " exact change set", changed == {"src/experimental_swift_reactor/" + f for f in expected})
        check(name + " original harness identical", source["src/experimental_swift_reactor/campaign_harness.rs"] == previous["src/experimental_swift_reactor/campaign_harness.rs"])
        check(name + " pin ownership publication and release core identical", source["src/experimental/cache/borrowed.rs"] == previous["src/experimental/cache/borrowed.rs"])
        check(name + " frame production delta is single hard clamp", previous["src/experimental_swift_reactor/frame_operations.rs"].replace(b"budget().frames.min(64)", b"budget().frames.min(128)") == source["src/experimental_swift_reactor/frame_operations.rs"])
        check(name + " control production delta only frame and pin profiles", previous["src/experimental_swift_reactor/control.rs"].replace(b"active_pins: 64,", b"active_pins: 128,").replace(b"frames: 64,", b"frames: 128,") == source["src/experimental_swift_reactor/control.rs"])
        check(name + " selected function count", sum(b.count(b"fn framepin_campaign_") for b in source.values()) == count)
        cache = source["src/experimental_swift_reactor/cache.rs"].decode()
        old_cache = previous["src/experimental_swift_reactor/cache.rs"].decode()
        accounting = lambda s: s[s.index("macro_rules! sum_named"):s.index("const CACHE_CLEANUP_TEMPORARY_BYTES")]
        check(name + " original positive size accounting formulas identical", accounting(cache) == accounting(old_cache))
        check(name + " pin allocation checked and exact, initialization charged", all(s in cache for s in (
            ".checked_mul(size_of::<PinRecord>())", "reserve(&mut partial.pins, budget.active_pins, &mut self.control)?;", "for _ in 0..budget.active_pins {\n            self.control.work(1)?;")))
        if algorithm:
            check("dense fixed two-word owner and partial with thin fixed-array borrow", cache.count("free_pins: [u64; 2]") == 2 and "free_pins: &'a mut [u64; 2]" in cache)
            check("dense widened helper types counted in all three existing inventories", cache.count("(3, size_of::<DensePinInventory>())") == 3 and "mask: [u64; 2], permitted: [u64; 2], word: usize" in cache)
            check("dense two-word initialization and successful admission work increased", "self.control.work(2)?;\n        partial.free_pins" in cache and "meter.work(6)?;" in cache and "meter.work(4)?; // word choice" in cache)
        excerpts = {}
        ranges = {
            "src/experimental/cache/borrowed.rs": [(643, 770), (895, 917)],
            "src/experimental_swift_reactor/frame_operations.rs": [(420, 460), (900, 990)],
            "src/experimental_swift_reactor/control.rs": [(40, 62), (674, 720)],
            "src/experimental_swift_reactor/cache.rs": [(100, 130), (1055, 1065), (1124, 1160), (1830, 1910)],
            "src/experimental_swift_reactor/frame_operations_tests.rs": [(95, 122), (335, 450)],
            "src/experimental_swift_reactor/execution_tests.rs": [(700, 752)],
        }
        if algorithm:
            ranges["src/experimental_swift_reactor/cache.rs"].append((2140, 2185))
            ranges["src/experimental_swift_reactor/cache_tests.rs"] = [(3466, 3540), (3796, 3838)]
        for path, regions in ranges.items():
            lines = source[path].decode().splitlines()
            excerpts[path] = {"source": record(source[path]), "regions": [{"start": first, "end": last, "text": "\n".join(lines[first-1:last]) + "\n"} for first, last in regions]}
        save(name + "/source-excerpts.json", excerpts)
        # Full reconstructed inspection copies were temporary, not a new source
        # of authority. Exact manifests plus original/candidate generators remain.
        inspection = HERE / name / "inspection"
        if inspection.exists():
            shutil.rmtree(inspection)
        sources.append(source)
    return sources

def independent_controls(campaign, sources):
    """Independent set-oracle arithmetic and real runner validation controls."""
    scope = {"bitmapCases": 0, "bitmapMutationWitnesses": 0, "runnerCases": 0}
    full = (1 << 64) - 1
    def mask(length):
        # Direct transcription of the reviewed branch expression, not Rust execution.
        if length <= 64:
            return [full if length == 64 else (1 << length) - 1, 0]
        if length <= 128:
            return [full, full if length == 128 else (1 << (length - 64)) - 1]
        return [0, 0]
    def select(length, free, occupied):
        permitted = mask(length)
        if length > 128 or any(free[w] & ~permitted[w] for w in range(2)) or sum(w.bit_count() for w in free) + len(occupied) != length:
            return "mask"
        if free == [0, 0]:
            return "exhausted" if len(occupied) == length else "orphan"
        word = int(free[0] == 0)
        slot = word * 64 + (free[word] & -free[word]).bit_length() - 1
        if slot >= length or slot in occupied:
            return "occupied"
        return slot
    # A set of actual occupied slots supplies an independent representation.
    # Exhaustively test each possible sole vacancy, including both word edges.
    for length in range(129):
        allowed = {i for i in range(128) if mask(length)[i // 64] & (1 << (i % 64))}
        assert allowed == set(range(length))
        for vacancy in range(length):
            free = [0, 0]
            free[vacancy // 64] = 1 << (vacancy % 64)
            occupied = set(range(length)) - {vacancy}
            assert select(length, free, occupied) == min(set(range(length)) - occupied)
            scope["bitmapCases"] += 1
        assert select(length, [0, 0], set(range(length))) == "exhausted"
        scope["bitmapCases"] += 1
    rng = random.Random(12864063)
    for length in (1, 63, 64, 65, 127, 128):
        free, occupied = mask(length), set()
        for step in range(512):
            if occupied and (len(occupied) == length or rng.randrange(3) == 0):
                slot = rng.choice(sorted(occupied))
                occupied.remove(slot)
                free[slot // 64] |= 1 << (slot % 64)
            else:
                slot = select(length, free, occupied)
                assert slot == min(set(range(length)) - occupied)
                occupied.add(slot)
                free[slot // 64] &= ~(1 << (slot % 64))
            assert {i for i in range(length) if free[i // 64] & (1 << (i % 64))} == set(range(length)) - occupied
            scope["bitmapCases"] += 1
    for length in range(129):
        if length < 128:
            free = mask(length)
            free[length // 64] |= 1 << (length % 64)
            assert select(length, free, set()) == "mask"
            scope["bitmapCases"] += 1
        if length:
            assert select(length, mask(length), {0}) == "mask"
            scope["bitmapCases"] += 1
    for selected in (63, 64, 127):
        occupied = set(range(128)) - {(selected + 1) % 128}
        free = [0, 0]
        free[selected // 64] = 1 << (selected % 64)
        assert select(128, free, occupied) == "occupied"
        scope["bitmapCases"] += 1
    assert mask(129) == [0, 0] and select(129, [0, 0], set(range(129))) == "mask"
    # Kill three plausible old-boundary mutations with concrete witnesses.
    for mutation in (lambda f: (f[0] & -f[0]).bit_length() - 1,
                     lambda f: (f[int(f[0] == 0)] & -f[int(f[0] == 0)]).bit_length() - 1,
                     lambda f: 64 + ((f[1] & -f[1]).bit_length() - 1) if f[0] == 0 and f[1] else None):
        witnesses = [(64, [0, 1]), (127, [0, 1 << 63]), (0, [1, 0])]
        assert any(mutation(bits) != expected for expected, bits in witnesses)
        scope["bitmapMutationWitnesses"] += 1
    check("independent set oracle covers every length and vacancy, churn, corruption and three mutations", True)

    def rejects(label, fn):
        try:
            fn()
        except (RuntimeError, ValueError, AssertionError, KeyError):
            scope["runnerCases"] += 1
            return
        raise AssertionError("negative accepted: " + label)
    def failure_fixture():
        result = campaign.historical()
        for event in result["events"]:
            if event["event"] in campaign.expected_bounds():
                event["payload"] = campaign.expected_bounds()[event["event"]]
        return result
    row = {"pid": 11, "exitCode": 101, "timedOut": False, "processGroupEmpty": True, "cancelled": None}
    result = failure_fixture()
    campaign.validate_result(result, row)
    scope["runnerCases"] += 1
    for kind in sorted(campaign.RESOURCE_FAILURE_KINDS):
        for fields in ({"code": "swift_run_unexpected_capacity"}, {"resource": "ExactCapacity"}, {"observed_capacity": 0}, {"resource": "OwnerIdentity"}, {"resource": "TicketInventory"}, {"code": "swift_run_owner_exhausted"}, {"code": "swift_run_ticket_inventory"}):
            changed = failure_fixture()
            for failure in (changed["firstFailure"]["payload"], campaign.event(changed, "final_failure")):
                failure.update(kind=kind, **fields)
            rejects("structural marker must stop every resource-like kind", lambda: campaign.validate_result(changed, row))
    check("independent R1 marker by resource-kind cross product rejects", True)
    for instructions, fuel, next_instructions, next_fuel in ((0, 0, 1, 0), (64, 128, 65, 128), (127, 256, 128, 256), (25_000_000, 30_000_000, 50_000_000, 54_999_999), (0, 0, 1 << 64, 1 << 64), (0, 0, True, 1)):
        rejects("R2 interval or type defect", lambda: campaign.validate_instruction_fuel({"instructions": instructions, "instruction_fuel": fuel}, {"instructions": next_instructions, "instruction_fuel": next_fuel}))
    for value in range(64):
        prior = {"instructions": value * 101, "instruction_fuel": value * 111}
        current = {"instructions": prior["instructions"] + 64, "instruction_fuel": prior["instruction_fuel"] + 65}
        campaign.validate_instruction_fuel(prior, current)
        scope["runnerCases"] += 1
        current["instruction_fuel"] -= 2
        rejects("R2 one-short interval", lambda: campaign.validate_instruction_fuel(prior, current))
    check("independent R2 positive bulk fuel and one-short interval matrix", True)
    for field in ("instruction_fuel", "execution_work", "cache_work", "frames", "active_pins", "combined_bytes"):
        changed = failure_fixture()
        campaign.event(changed, "run_budget")[field] += 1
        rejects("budget promotion " + field, lambda: campaign.validate_result(changed, row))
    for group in ("reservations", "live"):
        final = campaign.event(result, "final_cleanup_usage")[group]
        for name, cell in final.items():
            if type(cell) is dict:
                for bad in (1, -1, False, 0.0):
                    changed = failure_fixture()
                    campaign.event(changed, "final_cleanup_usage")[group][name]["current"] = bad
                    rejects("unclosed owner ledger " + group + name, lambda: campaign.validate_result(changed, row))
    check("independent no budget promotion or nonzero/coerced cleanup acceptance", True)
    # These are the actual source validator's boundary contracts, with a mutated
    # original harness and lifecycle target. They do not authorize OTA behavior.
    original, _, _ = campaign.inputs()
    for key in ("src/experimental_swift_reactor/campaign_harness.rs", "src/experimental_swift_reactor/lifecycle_tests.rs"):
        changed = dict(sources[0]); changed[key] += b"\n// mutation\n"
        rejects("original target/source mutation", lambda: campaign.validate_source(original, changed))
    for value in (None, 0, 1, "false", [], {}):
        rejects("implicit arm selection", lambda: campaign.prepare_source(original, value))
    env = {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_RUN_ATTEMPT": "1"}
    for selected in (None, "paired-64-v1", "paired-128-v1 ", "PAIRED-128-V1"):
        with patch.dict(os.environ, env | ({} if selected is None else {"MIXER_FRAME_PIN_SELECTION": selected}), clear=True), patch.object(campaign.platform, "system", return_value="Linux"):
            output = HERE / "must-not-create"
            rejects("root selection missing or wrong", lambda: campaign.run(output))
            assert not output.exists()
    check("independent original harness mutation and explicit profile negatives", True)
    return scope

def producer_replay():
    scratch = HERE / "pure-scratch"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(exist_ok=False)
    old, tempfile.tempdir = tempfile.tempdir, str(scratch)
    try:
        module = load("independent_replayed_producer_controls", PRODUCER / "test_campaign.py")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = unittest.TextTestRunner(stream=stderr, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
        (HERE / "producer-replay.stdout").write_text(stdout.getvalue())
        (HERE / "producer-replay.stderr").write_text(stderr.getvalue())
        check("fresh replay of all 39 producer pure runner methods", result.wasSuccessful() and result.testsRun == 39)
        return result.testsRun
    finally:
        tempfile.tempdir = old
        scratch.rmdir()

def workflow_review(campaign):
    workflow = (PRODUCER / "workflow.yml").read_text()
    for name in ("candidate.py", "campaign.py", "test_campaign.py"):
        ast.parse((PRODUCER / name).read_text(), filename=name)
    check("all Python entrypoints parse without compiler execution", True)
    checks = {
        "workflow requires explicit reviewed input": "required: true\n        options: [paired-128-v1]" in workflow and "MIXER_FRAME_PIN_SELECTION: ${{ inputs.profile }}" in workflow,
        "workflow fixed Linux runner and compiler": "runs-on: ubuntu-24.04" in workflow and "rustup toolchain install 1.99.0 --profile minimal" in workflow,
        "workflow serialized against prior architecture campaign": "group: swift-execution-architecture-comparison\n  cancel-in-progress: false" in workflow,
        "workflow read-only permissions": "permissions:\n  contents: read" in workflow and "contents: write" not in workflow,
        "workflow preserves failure evidence": "if: always()" in workflow and "if-no-files-found: error" in workflow and "!${{ runner.temp }}/swift-frame-pin-admission-candidate/scratch/" in workflow,
        "workflow calls only proposed pure controls and driver": "python3 -B verification/swift-frame-pin-admission-candidate/test_campaign.py" in workflow and "python3 -B verification/swift-frame-pin-admission-candidate/campaign.py run" in workflow,
        "eleven-command budget and aggregate margin remain bounded": campaign.MAX_COMMANDS == 11 and campaign.MAX_FULL_ATTEMPTS == 2 and campaign.CAMPAIGN_SECONDS == 2700 and 3*15 + 2*(180+90+90+750) + 11*20 == 2485,
    }
    for name, value in checks.items(): check(name, value)
    # Verify the sparse checkout includes each static basis and every dynamic
    # generator/input directory read by the future pure checks and campaign.
    for path in ("/verification/swift-cache-capacity-campaign-v1/", "/verification/swift-execution-architecture-correction/", "/verification/swift-frame-pin-admission-candidate/", *["/" + p for p in campaign.CORRECTION_BASIS if "swift-execution-architecture-correction" not in p], "/verification/github-delivery-binary-export-and-ui/cache-deadline-review/seal.json", "/verification/github-delivery-binary-export-and-ui/cache-deadline-review/receipt.json", "/verification/github-delivery-binary-export-and-ui/cache-deadline-review/REVIEW.md"):
        check("workflow sparse dependency " + path, path in workflow)
    save("workflow-review.json", {"checks": checks, "workflow": record((PRODUCER / "workflow.yml").read_bytes()), "workflowInstalledOrDispatched": False, "selection": "Root decision remains required", "compilationAndGeometryPending": True})

def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (ROOT / "AGENTS.md").read_bytes()
    (ROOT / "mixer-product-plan.md").read_bytes()
    bind_seal()
    campaign = load("independent_framepin_campaign", PRODUCER / "campaign.py")
    sources = source_review(campaign)
    independent = independent_controls(campaign, sources)
    replayed = producer_replay()
    workflow_review(campaign)
    bind_seal()
    save("checks.json", CHECKS)
    save("readset.json", {str(p.relative_to(ROOT)): record(p.read_bytes()) for p in sorted(READS) if p.is_file()})
    save("receipt.json", {"schema": 1, "startedAtUTC": started, "finishedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "command": "python3 -B verification/swift-frame-pin-admission-independent/review.py", "python": platform.python_version(), "pythonExecutable": sys.executable, "producerSealSHA256": SEAL_SHA, "checks": len(CHECKS), "independentControls": independent, "replayedProducerMethods": replayed, "sourceTreeDigest": sha((HERE / "readset.json").read_bytes()), "sourceTreeDigestScope": "audited repository readset including immutable input archive and generator closure; not a live Git revision", "actualCompilations": 0, "actualFiniteRuns": 0, "actualFullRuns": 0, "scope": "Independent pure source, arithmetic and runner controls only; compiled geometry, finite Rust controls and full behavior pending", "deniedOperations": DENIED, "processSocketSignalWaitGuards": True, "allWritesConfinedToIndependentFolder": True, "ownedScratchRemoved": not (HERE / "pure-scratch").exists() and all(not (HERE / p[0] / "inspection").exists() for p in campaign.PROFILES), "holdsUnchanged": [20745,20770,20780,20817,20842,20851,20866,"Unit A","broad hosted","local FieldLog compiler custody","native/UI/capture"], "blockingFindings": [], "recommendation": "source candidate acceptable for explicit root selection and one bounded remote campaign; no runtime or product acceptance"})
    print(str(len(CHECKS)) + " independent source binding checks passed; no child/process probes")

if __name__ == "__main__":
    main()

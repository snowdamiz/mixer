#!/usr/bin/env python3
"""One dense512 completion hypothesis inside a cumulative 1200s window.

check is pure source/data work. run requires first-attempt GitHub-hosted Linux.
Resource exhaustion is diagnostic evidence, never campaign or product success.
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
REVIEW = HERE.parent / "github-delivery-binary-export-and-ui/cache-deadline-review"
V1_DRIVER_SHA = "5266e70df6e79054ffdc1abfc64b300d9f6252f11e55eb340716ab346bc4c556"
V1_BINDINGS_SHA = "e445894e7eb0971846635026e7219614965018c5339e146b97895bc45eb53827"
V1_CONTROLS_SHA = "41f3e465706101b9f8c50bf0246296bc0b88ad3a3d2202a74580d4a5dc64896e"
REVIEW_SEAL_SHA = "c6bde1201697149bfa84d2f31b112d14d8c1e35ac005fc908a16433941f23df8"
CORRECTION_BASIS = {
    "verification/swift-cachework-128-experiment/seal.json":
        "dce182dba6c4e4bf38738b486276596c7b0cbc17c798e8780ebd19287bced0d0",
    "verification/swift-frame-pin-admission-candidate/seal.json":
        "c5d0e8b29625e09bc5bc6ef73094edc4aebdc03ee5d4e27cafa34b5eda05bd6a",
    "verification/swift-cachework-128-experiment/baseline-summary.json":
        "49daa97d05b25a1d74496ea97d0f9d1e14f75501545b7d4d1083808e13a58d8d",
    "verification/swift-execution-architecture-correction/seal.json":
        "4efa21ab9e7bf43cec647c760bdacf6c3e5b2be944976240ec186c738370a6d2",
    "verification/github-delivery-architecture-comparison/ci-review/seal.json":
        "6965fd62339bedddc735068068fead314abd79dea56ee466b06cccb565b0cea4",
    "verification/swift-execution-architecture-comparison/seal.json":
        "b20440be09778e3209de5c1e6dae941e0580b8737fe28ed35be53777e3292f70",
    "verification/swift-execution-architecture-independent/seal.json":
        "c1ecb422803c2e43dc69206b28e6f51e2b023b9b8fab13054e20ecc7976a7486",
}
if hashlib.sha256((V1 / "campaign.py").read_bytes()).hexdigest() != V1_DRIVER_SHA:
    raise RuntimeError("frozen v1 helper changed")
spec = importlib.util.spec_from_file_location("architecture_capacity_v1", V1 / "campaign.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
require, save, sha = base.require, base.save, base.sha

PROFILES = (("dense512-completion", True, "::framepin_campaign_", 12),)
CANDIDATE_FILES = ("candidate.py", "scalar-guards.rs", "baseline-summary.json", "phase-evidence.json")
CAMPAIGN_SECONDS = 2_100
BUILD_SECONDS, FINITE_SECONDS, HARNESS_SECONDS, FULL_SECONDS = 180, 90, 90, 1_350
MAX_FULL_ATTEMPTS = 1
MAX_COMMANDS = 6
PREFIX_THRESHOLDS = (25_000_000, 50_000_000, 100_000_000, 250_000_000, 500_000_000,
    750_000_000, 1_000_000_000, 1_250_000_000, 1_500_000_000, 1_750_000_000)
PREFIX_MAX_BYTES = 8_192
PREFIX_FIELDS = frozenset(("threshold", "instructions", "instruction_fuel", "cache_work", "execution_work",
    "host_calls", "elapsed_micros", "function", "offset"))
RESOURCE_FAILURE_KINDS = frozenset(("Deadline", "Allocation", "CategoryExhausted", "CombinedExhausted",
    "ResourceExhausted", "FuelExhausted", "WorkExhausted", "HostCallLimit", "PinLimit", "FrameLimit",
    "ValueLimit", "ControlLimit"))
STRUCTURAL_FAILURE_RESOURCES = frozenset(("TicketInventory", "OwnerIdentity"))
STRUCTURAL_FAILURE_CODES = frozenset(("swift_run_ticket_inventory", "swift_run_owner_exhausted"))
RSS_LIMITATION = "Raw wait4 value retained; prior campaign showed a launcher high-water floor. VM-attributable RSS unavailable; no per-arm RSS comparison."


def candidate_module():
    spec = importlib.util.spec_from_file_location("architecture_candidate", HERE / "candidate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def candidate_bindings():
    result = {}
    for name in CANDIDATE_FILES:
        data = (HERE / name).read_bytes()
        result[name] = {"bytes": len(data), "sha256": sha(data)}
    return result


def typed_equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(typed_equal(actual[k], v) for k, v in expected.items())
    if type(expected) is list:
        return len(actual) == len(expected) and all(typed_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def guarded_command(custody, argv, cwd, env, directory, seconds):
    require(custody["pendingCommand"] is None, "previous command custody unresolved; no further command")
    require(type(custody["provenClosedCommands"]) is int and 0 <= custody["provenClosedCommands"] < MAX_COMMANDS,
        "command count cap")
    custody["pendingCommand"] = {"argv": argv, "directory": str(directory), "timeoutSeconds": seconds}
    save(Path(custody["recordPath"]), custody)
    # Exceptions cannot establish closure, including a helper failure after Popen.
    row = base.command(argv, cwd, env, directory, seconds)
    require(type(row) is dict and type(row.get("pid")) is int and row["pid"] > 0
        and type(row.get("exitCode")) is int and -signal.NSIG < row["exitCode"] <= 255
        and row.get("processGroupEmpty") is True,
        "terminal child-reap/group-absence proof missing; custody unresolved")
    custody["pendingCommand"] = None
    custody["provenClosedCommands"] += 1
    save(Path(custody["recordPath"]), custody)
    return row


def inputs():
    require(sha((HERE / "baseline-summary.json").read_bytes()) == "37efcd8e160e486c8a0dc3a4cbbb0812f9c19d0843c20b763203f60b8c8148cf", "actual closed capacity summary changed")
    closed = json.loads((HERE / "baseline-summary.json").read_text())
    require(closed["fullAttemptsRemaining"] == 0 and closed["fullAttemptsClosed"] == 2
        and closed["allElevenRemoteCommandsReapedAndOwnedGroupsAbsent"] is True
        and closed["ownedScratchRemoved"] is True, "previous pair campaign is not closed")
    require(sha((HERE / "phase-evidence.json").read_bytes()) == "1e2d875adff2a35795fa19137c8444558d02efacd519f591758646397a6749c5", "actual phase evidence changed")
    for path, expected in CORRECTION_BASIS.items():
        require(sha((ROOT / path).read_bytes()) == expected, "architecture correction basis changed: " + path)
    require(sha((base.INPUTS / "bindings.json").read_bytes()) == V1_BINDINGS_SHA, "frozen v1 input bindings changed")
    require(sha((V1 / "campaign-controls.rs").read_bytes()) == V1_CONTROLS_SHA, "frozen v1 finite controls changed")
    require(sha((REVIEW / "seal.json").read_bytes()) == REVIEW_SEAL_SHA, "prior review seal changed")
    seal = json.loads((REVIEW / "seal.json").read_text())
    for name in ("REVIEW.md", "receipt.json"):
        data = (REVIEW / name).read_bytes()
        require(len(data) == seal["files"][name]["bytes"] and sha(data) == seal["files"][name]["sha256"],
                "prior review binding changed: " + name)
    reviewed = json.loads((REVIEW / "receipt.json").read_text())
    require(reviewed["fullAttempts"] == 2 and reviewed["fullAttemptsRemaining"] == 0
        and reviewed["allOriginalFailuresPreserved"] is True
        and reviewed["allFinalLogicalReservationsAndLiveCountersZero"] is True
        and reviewed["all11CommandCustodyClosed"] is True and reviewed["hostFeasibilityAccepted"] is False,
        "prior campaign decision changed")
    original, artifact, bindings = base.inputs()
    require(len(json.loads((base.INPUTS / "native-observation.json").read_text())) == 11, "original 11-field oracle changed")
    return original, artifact, bindings


def event(result, name):
    values = [e["payload"] for e in result["events"] if e["event"] == name]
    require(len(values) == 1, "missing or duplicate event: " + name)
    return values[0]


def historical():
    return base.classify(base.INPUTS / "historical-attribution.stdout",
        {"exitCode": 101, "timedOut": False, "processGroupEmpty": True})


def expected_bounds(capacity512=True):
    require(capacity512 is True, "only the dense512 completion profile is admitted")
    old = historical()
    bounds = {n: event(old, n) for n in ("validation_budget", "run_budget", "wasi_budget", "wasi_grants")}
    bounds["run_budget"] |= {"cache_entries": 512, "cache_work": 4_000_000_000,
        "frames": 128, "active_pins": 128, "instruction_fuel": 4_000_000_000,
        "execution_work": 16_000_000_000, "deadline_ms": 1_200_000}
    bounds["wasi_budget"]["deadline_ms"] = 1_200_000
    return bounds


def validate_source(original, source):
    require(type(source) is dict and set(original) <= set(source), "source inventory changed")
    require(all(type(n) is str and type(b) is bytes and not Path(n).is_absolute() and ".." not in Path(n).parts
                for n, b in source.items()), "invalid source path or bytes")
    require(source.get("src/experimental_swift_reactor/campaign_harness.rs") == (base.INPUTS / "harness.rs").read_bytes(),
        "original harness/oracle changed")
    original_lifecycle = base.parameterize(original, 256, 128_000_000)["src/experimental_swift_reactor/lifecycle_tests.rs"]
    require(source["src/experimental_swift_reactor/lifecycle_tests.rs"] == original_lifecycle,
        "original full target/harness inclusion changed")


def prepare_source(original, capacity512):
    require(type(capacity512) is bool, "capacity512 must be selected explicitly")
    module = candidate_module()
    require(typed_equal(module.expected_bounds(capacity512), expected_bounds(capacity512)), "candidate selected bounds differ from complete profile")
    source = module.parameterize(original, capacity512)
    validate_source(original, source)
    return source


def zero_resources(result):
    final = event(result, "final_cleanup_usage")
    template = event(historical(), "final_cleanup_usage")
    if type(final) is not dict or final.get("cleanup_invariant") is not None:
        return False
    for group in ("reservations", "live"):
        actual, expected = final.get(group), template[group]
        if type(actual) is not dict or set(actual) != set(expected):
            return False
        for key, value in expected.items():
            if type(value) is dict:
                row = actual[key]
                if type(row) is not dict or set(row) != {"current", "peak"}:
                    return False
                if type(row["current"]) is not int or row["current"] != 0 or type(row["peak"]) is not int or row["peak"] < 0:
                    return False
        if group == "reservations":
            if type(actual["live_tickets"]) is not int or actual["live_tickets"] != 0:
                return False
            if type(actual["peak_tickets"]) is not int or actual["peak_tickets"] < 0:
                return False
    return True


def validate_result(result, full, capacity512=True):
    expected = expected_bounds(capacity512)
    actual = {name: event(result, name) for name in expected}
    require(typed_equal(actual, expected), "actual budgets/grants differ from selected complete bounds")
    result["actualBounds"] = actual
    first, final = result["firstFailure"], event(result, "final_failure")
    preserved = (final is None if first is None else
        type(final) is dict and typed_equal(final | {"after_cleanup": None}, first["payload"]))
    result["originalFinalFailurePreserved"] = preserved
    require(preserved, "original first failure not preserved through consuming cleanup")
    require(result["consumingCleanup"] is True and zero_resources(result)
        and event(result, "cleanup_reservations_and_live_empty") is True,
        "consuming cleanup unresolved; stop resource reuse")
    require(event(result, "cleanup_empty") is (first is None), "cleanup success/failure semantics changed")
    require(result["telemetry"]["status"] == "valid", "invalid attribution; stop comparison")
    require(full.get("processGroupEmpty") is True and full.get("timedOut") is False and full.get("cancelled") is None,
        "external timeout/cancellation or unresolved owned group")
    require(type(full.get("exitCode")) is int and full["exitCode"] == (0 if result["hostFeasibility"] else 101),
        "unexpected full target exit")
    if first is None:
        require(result["hostFeasibility"] is True and result["complete"] is True
            and result["nativeEqualPhases"] == ["corpus_1", "corpus_2"]
            and len(result["completeGuestObservations"]) == 2, "incomplete original two-corpus oracle")
        oracle = json.loads((base.INPUTS / "native-observation.json").read_text())
        require([o.get("phase") for o in result["completeGuestObservations"]] == ["corpus_1", "corpus_2"]
            and all(typed_equal(o.get("observation"), oracle) for o in result["completeGuestObservations"]),
            "complete original 11-field oracle mismatch")
    else:
        failure = first.get("payload")
        require(type(failure) is dict, "invalid first failure; stop comparison")
        # Allocation is also the producer's kind for an exact-capacity defect.
        # Any one of its identifying fields stops comparison, even if another
        # field has been lost or misclassified. Cleanup is still checked above.
        require(failure.get("code") != "swift_run_unexpected_capacity"
            and failure.get("resource") != "ExactCapacity"
            and failure.get("observed_capacity") is None,
            "unexpected allocation capacity; stop comparison")
        # Ticket/identity inventory failures concern structural accounting,
        # not one of the selected experimental resource ceilings.
        require(failure.get("resource") not in STRUCTURAL_FAILURE_RESOURCES
            and failure.get("code") not in STRUCTURAL_FAILURE_CODES,
            "structural ticket/identity failure; stop comparison")
        require(result["hostFeasibility"] is False and result["complete"] is False
            and failure.get("kind") in RESOURCE_FAILURE_KINDS,
            "unexpected invariant, unsupported behavior or non-resource failure; stop comparison")
    result["outcome"] = "host-feasibility-observed" if result["hostFeasibility"] else "resource-limit-diagnostic"


def validate_instruction_fuel(previous, current):
    """One fuel precedes each original instruction; bulk fuel is nonnegative."""
    require(all(type(current.get(key)) is int and 0 <= current[key] < (1 << 64)
        for key in ("instructions", "instruction_fuel")), "invalid instruction/fuel counter")
    instructions, fuel = current["instructions"], current["instruction_fuel"]
    require(fuel >= instructions, "instruction fuel below cumulative original instructions")
    require(instructions >= previous["instructions"] and fuel >= previous["instruction_fuel"],
        "instruction/fuel cumulative counter regression")
    require(fuel - previous["instruction_fuel"] >= instructions - previous["instructions"],
        "instruction fuel below interval original instructions")


def prefix_records(path):
    """Bounded diagnostic records only; never infer a reached threshold or pass."""
    spec = importlib.util.spec_from_file_location("architecture_prefix_json", base.INPUTS / "telemetry.py")
    telemetry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(telemetry)
    rows, encoded = [], bytearray()
    for line in path.read_bytes().splitlines(keepends=True):
        at = line.find(b"MIXER_PREFIX ")
        if at < 0:
            continue
        payload = line[at:]
        encoded.extend(payload)
        require(len(encoded) <= PREFIX_MAX_BYTES and len(rows) < len(PREFIX_THRESHOLDS), "prefix output bound exceeded")
        require(payload.endswith(b"\n"), "truncated prefix record")
        row = telemetry.strict_json(payload[len(b"MIXER_PREFIX "):])
        require(type(row) is dict and set(row) == PREFIX_FIELDS
            and all(type(value) is int and 0 <= value < (1 << 64) for value in row.values()), "invalid prefix record")
        require(row["threshold"] == PREFIX_THRESHOLDS[len(rows)] and row["instructions"] == row["threshold"],
            "missing, duplicate or out-of-order prefix threshold")
        require(row["function"] <= (1 << 32) - 1 and row["offset"] != (1 << 64) - 1,
            "prefix cursor missing or invalid")
        bounds = expected_bounds()["run_budget"]
        require(all(row[key] <= bounds[key] for key in ("instruction_fuel", "cache_work", "execution_work", "host_calls")),
            "prefix counters exceed selected bounds")
        if rows:
            require(all(row[key] >= rows[-1][key] for key in PREFIX_FIELDS - {"function", "offset"}),
                "prefix cumulative counter regression")
        validate_instruction_fuel(rows[-1] if rows else {"instructions": 0, "instruction_fuel": 0}, row)
        rows.append(row)
    return {"schema": 1, "records": rows, "outputBytes": len(encoded), "maximumBytes": PREFIX_MAX_BYTES,
        "maximumRecords": len(PREFIX_THRESHOLDS), "authority": "read-only diagnostic observations; no success or completion inference"}, bytes(encoded)


def validate_prefix(result, prefix):
    final = event(result, "final_cleanup_usage")
    require(type(final.get("instructions")) is int and final["instructions"] >= 0, "invalid final instruction counter")
    require([row["threshold"] for row in prefix["records"]] == [n for n in PREFIX_THRESHOLDS if n <= final["instructions"]],
        "prefix observations do not match reached final instruction count")
    if prefix["records"]:
        require(all(prefix["records"][-1][key] <= final[key]
            for key in ("instructions", "instruction_fuel", "cache_work", "execution_work", "host_calls", "elapsed_micros")),
            "prefix counters exceed final owner usage")
    # Recheck every interval here as well: callers cannot bypass the parser's
    # fuel contract with a preconstructed prefix object. Include the final join
    # and the empty-prefix case, both measured from the original owner start.
    previous = {"instructions": 0, "instruction_fuel": 0}
    for current in [*prefix["records"], final]:
        validate_instruction_fuel(previous, current)
        previous = current


def check(output):
    original, artifact, bindings = inputs()
    rows = []
    for name, capacity512, finite_filter, count in PROFILES:
        source = prepare_source(original, capacity512)
        record, delta = base.source_record(original, source)
        save(output / name / "source.json", record)
        (output / name / "changes.patch").write_text(delta)
        rows.append({"name": name, "capacity512": capacity512, "sourceSHA256": record["sha256"],
            "finiteFilter": finite_filter, "finiteCount": count, "bounds": expected_bounds(capacity512)})
    result = {"schema": 3, "profiles": rows, "inputBindings": bindings, "priorReviewSealSHA256": REVIEW_SEAL_SHA,
        "correctionBasis": CORRECTION_BASIS,
        "candidateGeneratorSHA256": sha((HERE / "candidate.py").read_bytes()),
        "candidateSourceBindings": candidate_bindings(),
        "artifact": {"bytes": len(artifact), "sha256": sha(artifact)}, "maxFullAttempts": MAX_FULL_ATTEMPTS,
        "aggregateDriverSeconds": CAMPAIGN_SECONDS, "commandSeconds": {"build": BUILD_SECONDS,
            "finite": FINITE_SECONDS, "harness": HARNESS_SECONDS, "full": FULL_SECONDS, "cleanup": 10, "receiptMargin": 10},
        "maxCommands": MAX_COMMANDS, "worstCaseCommandsCleanupAndReceiptSeconds": 1_810,
        "execution": "pure source/data checks only; compilation, finite/harness controls and full attempts pending"}
    save(output / "check.json", result)
    return result


def unchanged(crate, source, target_input):
    return ({str(p.relative_to(crate)) for p in crate.rglob("*") if p.is_file()} == set(source)
        and all((crate / n).read_bytes() == b for n, b in source.items())
        and target_input.stat().st_size == base.ARTIFACT_BYTES and sha(target_input.read_bytes()) == base.ARTIFACT_HASH)


def reserve_full_attempt(campaign, output):
    require(type(campaign["fullAttempts"]) is int and 0 <= campaign["fullAttempts"] < MAX_FULL_ATTEMPTS, "full attempt cap")
    base.ensure_command_budget(FULL_SECONDS)
    campaign["fullAttempts"] += 1
    save(output / "campaign.json", campaign)  # Persist before spawn; no refund/retry.


def geometry_record(path, capacity512):
    text = path.read_text()
    def one(marker, fields, selector=None):
        lines = [line[line.find(marker) + len(marker):] for line in text.splitlines() if (selector or marker) in line]
        require(len(lines) == 1, "missing or duplicate finite geometry marker: " + marker)
        parts = [token.split("=") for token in lines[0].split()]
        require(all(len(part) == 2 for part in parts) and len({part[0] for part in parts}) == len(parts),
            "malformed finite geometry fields")
        values = dict(parts)
        require(set(values) == set(fields), "changed finite geometry schema: " + marker)
        result = {}
        for key, value in values.items():
            if marker == "PLAN_PROFILE " and key == "tickets":
                tickets = value.split("/")
                require(len(tickets) == 2 and all(n.isascii() and n.isdecimal() for n in tickets), "invalid geometry tickets")
                result[key] = [int(n) for n in tickets]
            else:
                require(value.isascii() and value.isdecimal(), "invalid geometry number: " + key)
                result[key] = int(value)
        return result
    plan_fields = ("floor", "execution_header", "execution_construction", "frame_operation", "category_ceiling_sum",
        "wasi_max", "shared", "conservative_combined", "combined_limit", "constructed_current", "constructed_peak",
        "resident_current", "resident_peak", "frame_peak", "tickets")
    plan = one("PLAN_PROFILE ", plan_fields, "PLAN_PROFILE floor=")
    cleanup = "PLAN_PROFILE cleanup_zero=true guest_instructions=0 initializes=0 invokes=0"
    require(sum(cleanup in line for line in text.splitlines()) == 1, "missing or duplicate finite zero-resource cleanup marker")
    bounds = expected_bounds(capacity512)["run_budget"]
    require(plan["combined_limit"] == bounds["combined_bytes"] == 268_435_456
        and 0 < plan["conservative_combined"] <= bounds["combined_bytes"], "conservative geometry exceeds unchanged combined envelope")
    require(plan["category_ceiling_sum"] == sum(bounds[key] for key in ("source_bytes", "metadata_bytes", "cache_bytes", "state_bytes")),
        "geometry category ceilings differ from selected complete profile")
    require(plan["execution_header"] <= bounds["state_bytes"] and 0 <= plan["tickets"][0] <= plan["tickets"][1] <= bounds["cache_entries"] + 22,
        "geometry header/tickets exceed selected bounds")
    require(all(plan[key] <= bounds["combined_bytes"] for key in
        ("constructed_current", "constructed_peak", "resident_current", "resident_peak", "frame_peak")), "geometry logical reservation peak exceeds combined bound")
    cache = one("DENSE geometry ", ("index_bytes", "pin_bitmap_bytes", "header", "operation", "logical_peak"))
    require(cache["index_bytes"] == 160_000 and cache["pin_bitmap_bytes"] == 16,
        "dense index/pin geometry does not match admitted representation")
    require(cache["logical_peak"] <= bounds["combined_bytes"], "dense geometry exceeds combined bound")
    n = bounds["cache_entries"]
    require(sum("CACHEWINDOW capacity " in line for line in text.splitlines()) == 1, "missing or duplicate capacity marker")
    require(sum("CACHEWINDOW scalar_limits=" in line for line in text.splitlines()) == 1, "missing or duplicate scalar marker")
    capacity_marker = f"CACHEWINDOW capacity residents={n} highest_encoded={n} tickets={n + 22} dense_index_bytes=160000 pin_bitmap_bytes=16 above_capacity_rejected=true cleanup_zero=true"
    require(sum(capacity_marker in line for line in text.splitlines()) == 1, "missing exact capacity geometry/control marker")
    scalar_marker = "CACHEWINDOW scalar_limits=4000000000,4000000000,16000000000 cumulative=true above_max_rejected=true overflow_rejected=true cleanup_zero=true"
    require(sum(scalar_marker in line for line in text.splitlines()) == 1, "missing exact scalar guard marker")
    deadline_marker = "COMPLETION deadline_ms=1200000 wasi_deadline_ms=1200000 earliest_absolute=true sticky_expiry=true cleanup_zero=true"
    require(sum("COMPLETION deadline_ms=" in line for line in text.splitlines()) == 1
        and sum(deadline_marker in line for line in text.splitlines()) == 1, "missing exact deadline guard marker")
    operation = cache["operation"]
    recomputed = plan["category_ceiling_sum"] + plan["wasi_max"] + plan["shared"] + plan["floor"] + max(
        plan["execution_construction"], plan["frame_operation"] + operation)
    require(recomputed == plan["conservative_combined"], "finite conservative geometry formula mismatch")
    return {"schema": 1, "plan": plan, "cache": cache, "recomputedConservativeCombined": recomputed,
        "combinedLimit": bounds["combined_bytes"], "cleanupZero": True, "guestInstructions": 0,
        "finiteStdoutSHA256": sha(path.read_bytes()), "scope": "compiled finite owner geometry and consuming cleanup; full workload still pending"}


def verify_prepared(prepared, target_input, output, campaign):
    name, source, record = prepared["name"], prepared["source"], prepared["record"]
    require(typed_equal(candidate_bindings(), campaign["candidateSourceBindings"]), "candidate inputs changed after preflight")
    require(unchanged(prepared["crate"], source, target_input), "source/input changed before full attempt")
    require(typed_equal(json.loads((output / "preflight" / name / "source.json").read_text()), record)
        and typed_equal(json.loads((prepared["phase"] / "source.json").read_text()), record), "prepared source manifest changed")
    binary = prepared["binary"]
    require(binary.stat().st_size == prepared["executable"]["bytes"] and sha(binary.read_bytes()) == prepared["executable"]["sha256"],
        "prepared binary changed before full attempt")
    require(sha((prepared["phase"] / "geometry.json").read_bytes()) == prepared["geometrySHA256"], "prepared geometry receipt changed")
    require(sha((prepared["phase"] / "finite/stdout").read_bytes()) == prepared["geometry"]["finiteStdoutSHA256"],
        "prepared finite geometry output changed")


def prepare_profile(name, capacity512, finite_filter, count, original, target_input, scratch, env, output, campaign, custody):
    require(campaign["fullAttempts"] == 0, "finite preparation must precede the single full attempt")
    phase = output / name
    phase.mkdir()
    require(typed_equal(candidate_bindings(), campaign["candidateSourceBindings"]), "candidate inputs changed after preflight")
    source = prepare_source(original, capacity512)
    record, diff = base.source_record(original, source)
    selected = json.loads((output / "preflight" / name / "source.json").read_text())
    require(typed_equal(record, selected), "source differs from preflight selection")
    save(phase / "source.json", record)
    (phase / "changes.patch").write_text(diff)
    save(phase / "selected-bounds.json", expected_bounds(capacity512))
    crate = scratch / name / "vm"
    base.materialize(source, crate)
    child_env = env | {"CARGO_TARGET_DIR": str(scratch / name / "target")}
    build = guarded_command(custody, ["cargo", "test", "--lib", "--no-run", "--release", "--locked", "--offline",
        "--no-default-features", "--features", "experimental-swift-reactor", "--message-format=json"],
        crate, child_env, phase / "build", BUILD_SECONDS)
    require(build["exitCode"] == 0 and not build["timedOut"], "compile failed: " + name)
    artifacts = [json.loads(line) for line in (phase / "build/stdout").read_text().splitlines() if line.startswith("{")]
    candidates = [row["executable"] for row in artifacts if row.get("reason") == "compiler-artifact" and row.get("executable")]
    require(len(candidates) == 1, "one test executable required")
    binary = Path(candidates[0])
    require(binary.resolve().is_relative_to((scratch / name / "target").resolve()), "test executable outside owned target directory")
    executable = {"path": str(binary), "bytes": binary.stat().st_size, "sha256": sha(binary.read_bytes())}
    save(phase / "binary.json", executable)
    for label, test, expected_count, seconds in (("finite", finite_filter, count, FINITE_SECONDS),
            ("harness-control", base.PREFIX + "exact_reactor_harness_control", 1, HARNESS_SECONDS)):
        control = guarded_command(custody, [str(binary), test, "--nocapture", "--test-threads=1"],
            crate, child_env, phase / label, seconds)
        require(control["exitCode"] == 0 and control["timedOut"] is False, "finite control failed: " + label)
        require(f"test result: ok. {expected_count} passed; 0 failed; 0 ignored" in (phase / label / "stdout").read_text(),
            "missing selected finite/harness controls")
    geometry = geometry_record(phase / "finite/stdout", capacity512)
    save(phase / "geometry.json", geometry)
    prepared = {"name": name, "capacity512": capacity512, "source": source, "record": record, "crate": crate,
        "childEnv": child_env, "phase": phase, "binary": binary, "executable": executable,
        "geometry": geometry,
        "geometrySHA256": sha((phase / "geometry.json").read_bytes())}
    verify_prepared(prepared, target_input, output, campaign)
    campaign["preparedProfiles"].append({"name": name, "capacity512": capacity512, "sourceSHA256": record["sha256"],
        "binary": executable, "geometry": str((phase / "geometry.json").relative_to(output)),
        "geometrySHA256": prepared["geometrySHA256"], "finiteCount": count, "harnessCount": 1, "fullAttemptsAtPreparation": 0})
    save(output / "campaign.json", campaign)
    return prepared


def execute_profile(prepared, target_input, scratch, output, campaign, custody):
    require(campaign.get("preparationGate") == {"singleArmPrepared": True, "fullAttemptsAtAdmission": 0, "closedPreparationCommands": 5}
        and [row["name"] for row in campaign["preparedProfiles"]] == [p[0] for p in PROFILES],
        "compiled finite geometry preparation required before full admission")
    verify_prepared(prepared, target_input, output, campaign)
    name, capacity512, source, record = (prepared[key] for key in ("name", "capacity512", "source", "record"))
    phase, crate, child_env, binary, executable = (prepared[key] for key in ("phase", "crate", "childEnv", "binary", "executable"))
    reserve_full_attempt(campaign, output)
    full = guarded_command(custody, [str(binary), base.PREFIX + "exact_reactor_target_once", "--exact", "--nocapture", "--test-threads=1"],
        crate, child_env, phase / "full", FULL_SECONDS)
    result = base.classify(phase / "full/stdout", full)
    save(phase / "result.json", result)  # Preserve the first cause before rejecting any comparison.
    prefix, raw = prefix_records(phase / "full/stderr")
    save(phase / "prefix.json", prefix)
    (phase / "prefix.records").write_bytes(raw)
    require(unchanged(crate, source, target_input), "source/input changed during experiment")
    validate_result(result, full, capacity512)
    validate_prefix(result, prefix)
    save(phase / "result.json", result)
    campaign["profiles"].append({"name": name, "capacity512": capacity512, "sourceSHA256": record["sha256"],
        "binary": executable, "actualBounds": result["actualBounds"], "result": str((phase / "result.json").relative_to(output)),
        "prefix": str((phase / "prefix.json").relative_to(output)), "outcome": result["outcome"],
        "hostFeasibility": result["hostFeasibility"], "consumingCleanup": result["consumingCleanup"],
        "originalFinalFailurePreserved": result["originalFinalFailurePreserved"], "sourceAndInputUnchanged": True,
        "firstFailure": result["firstFailure"], "timing": {k: full[k] for k in ("wallSeconds", "userSeconds", "systemSeconds", "peakRSSBytes")},
        "peakRSSAvailableForVMComparison": False, "rssLimitation": RSS_LIMITATION})
    save(output / "campaign.json", campaign)
    require(custody["pendingCommand"] is None, "command custody unresolved; retain profile scratch")
    shutil.rmtree(scratch / name)
    return result


def run(output):
    require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1" and platform.system() == "Linux",
        "requires first-attempt GitHub-hosted Linux CI; local execution and rerun remain held")
    require(os.environ.get("MIXER_DENSE512_COMPLETION_SELECTION") == "dense512-completion-v1",
        "root must explicitly select reviewed dense512-completion-v1 bounds before remote execution")
    require(not output.exists(), "fresh campaign output required; no retries/resume")
    base.COMMAND_DEADLINE = time.monotonic() + CAMPAIGN_SECONDS
    base.CANCEL_REQUESTED = None
    signal.signal(signal.SIGTERM, base.request_cancel)
    signal.signal(signal.SIGINT, base.request_cancel)
    output.mkdir(parents=True)
    scratch = output / "scratch"
    campaign = {"schema": 3, "model": "gpt-6-astra", "reasoningEffort": "xhigh", "githubSHA": os.environ.get("GITHUB_SHA"),
        "githubRunId": os.environ.get("GITHUB_RUN_ID"), "githubRunAttempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "environment": " ".join(os.uname()), "python": {"version": platform.python_version(), "executable": sys.executable}, "profiles": [], "preparedProfiles": [], "maxFullAttempts": MAX_FULL_ATTEMPTS, "fullAttempts": 0,
        "maxCommands": MAX_COMMANDS,
        "aggregateDeadlineSeconds": CAMPAIGN_SECONDS, "priorReviewSealSHA256": REVIEW_SEAL_SHA,
        "actualBaselineRun": 40788458735, "closedBaselineFullAttempts": 2,
        "candidateKind": "single previously executed dense512 implementation; cumulative 1200s completion hypothesis",
        "correctionBasis": CORRECTION_BASIS,
        "milestone": "Both corpus calls on one initialized owner match all 11 original native fields, followed by consuming zero-resource cleanup.",
        "scope": "diagnostic host feasibility; native/public/signed OTA/FieldLog publication/GA pending", "rssLimitation": RSS_LIMITATION}
    custody = {"recordPath": str(output / "custody.json"), "pendingCommand": None, "provenClosedCommands": 0}
    try:
        original, artifact, bindings = inputs()
        campaign["inputBindings"] = bindings
        preflight = check(output / "preflight")
        campaign["candidateGeneratorSHA256"] = preflight["candidateGeneratorSHA256"]
        campaign["candidateSourceBindings"] = preflight["candidateSourceBindings"]
        scratch.mkdir()
        target_input = scratch / "fieldlog-reactor.wasm"
        target_input.write_bytes(artifact)
        del artifact
        env = {k: os.environ[k] for k in ("HOME", "PATH", "RUSTUP_HOME", "CARGO_HOME", "LANG") if k in os.environ}
        env.update(CARGO_INCREMENTAL="0", CARGO_NET_OFFLINE="true", CARGO_BUILD_JOBS="2", RUSTUP_TOOLCHAIN="1.99.0",
            MIXER_EXACT_REACTOR_INPUT=str(target_input), TMPDIR=str(scratch))
        for tool, argv in (("rustc", ["rustc", "-vV"]), ("cargo", ["cargo", "-V"])):
            row = guarded_command(custody, argv, HERE, env, output / "tools" / tool, 15)
            require(row["exitCode"] == 0 and row["timedOut"] is False, "tool identity failed")
        prepared = [prepare_profile(*profile, original, target_input, scratch, env, output, campaign, custody) for profile in PROFILES]
        require(campaign["fullAttempts"] == 0 and custody["pendingCommand"] is None and custody["provenClosedCommands"] == 5
            and len(campaign["preparedProfiles"]) == len(prepared) == 1, "single finite preparation receipt required before admission")
        campaign["preparationGate"] = {"singleArmPrepared": True, "fullAttemptsAtAdmission": 0, "closedPreparationCommands": 5}
        save(output / "campaign.json", campaign)
        for profile in prepared:
            execute_profile(profile, target_input, scratch, output, campaign, custody)
        require(campaign["fullAttempts"] == MAX_FULL_ATTEMPTS and len(campaign["profiles"]) == 1,
            "exactly one full attempt required for a closed experiment")
        require(custody["provenClosedCommands"] == MAX_COMMANDS, "all six command closures required")
        campaign["status"] = "completion-experiment-closed"
        campaign["milestoneObservedArms"] = [row["name"] for row in campaign["profiles"] if row["hostFeasibility"]]
        campaign["nextDecision"] = "Root decides from complete original observations or the preserved limiting failure; no automatic retry, budget increase or production default promotion."
    except Exception as error:
        campaign["status"] = "stopped"
        campaign["error"] = str(error)
        raise
    finally:
        unresolved = custody["pendingCommand"] is not None
        if not unresolved and scratch.exists():
            shutil.rmtree(scratch)
        campaign["cleanup"] = {"ownedScratchRemoved": not scratch.exists(), "nativeOrLocalCustodyProcessesStarted": False,
            "commandCustodyUnresolved": unresolved, "commandCustody": custody}
        if unresolved:
            campaign["status"] = "stopped-unresolved-command-custody"
            campaign["nextDecision"] = "Retain owned scratch; no further commands or attempts; unresolved remote custody requires root disposition."
        save(output / "campaign.json", campaign)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "run"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    (check if args.action == "check" else run)(args.output.resolve())

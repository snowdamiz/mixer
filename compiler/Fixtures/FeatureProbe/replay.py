#!/usr/bin/env python3
"""Replay the public Swift language controls on arm64 macOS without a device."""

import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import resource
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXPERIMENTS = ROOT / "compiler/experiments"
BENCHMARK = EXPERIMENTS / "fieldlog-guest-benchmark"
INSTALLED = EXPERIMENTS / "fieldlog-installed-guest"
sys.path[:0] = [str(INSTALLED), str(BENCHMARK)]

from matched_task import Run, SCRATCH_LIMIT, identity, require, sha
from run import build_compact_guest, replay_abi
from analyze import Reader
from qualification_support import strict_json


def shared_memory_control(module):
    """Change only the shared flag of the admitted module's bounded memory."""
    reader = Reader(module)
    reader.take(8)
    while reader.position < len(module):
        kind = reader.byte()
        length = reader.uint()
        start = reader.position
        payload = reader.take(length)
        if kind == 5:
            require(payload == b"\x01\x01\x01\x01", "expected one bounded 1/1-page memory")
            return module[:start + 1] + b"\x03" + module[start + 2:], start + 1
    raise ValueError("missing memory section")


def campaign(run):
    call = run.command
    out = run.scratch
    revision = call("revision", "/usr/bin/git", "rev-parse", "HEAD")[0].strip()
    tree = call("tree", "/usr/bin/git", "rev-parse", "HEAD^{tree}")[0].strip()
    runtime = ROOT / "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime"
    runtime_sources = [runtime / f"{name}.swift" for name in ("Types", "Failure", "GuestDebugLines")]
    model = INSTALLED / "TaskCompletion.swift"
    adapter = INSTALLED / "InstalledGuest.swift"
    prior = ROOT / "verification/receipts/l03-d3-task-review-event-trap-7b61fe1c.json"
    host = [HERE / "CompactHost.swift", BENCHMARK / "MatchedTask.swift", model, *runtime_sources]
    native = HERE / "Sources/FeatureProbe/main.swift"
    version_commands = {
        "macOS": ("/usr/bin/sw_vers",),
        "nativeSwift": ("/usr/bin/swiftc", "--version"),
        "guestSwift": (run.swift / "swiftc", "--version"),
        "linker": (run.swift / "wasm-ld", "--version"),
        "rustc": (run.rust / "rustc", "--version"),
        "cargo": (run.rust / "cargo", "--version"),
    }
    versions = {key: call(key, *command)[0].strip() for key, command in version_commands.items()}
    vm = ROOT / "vm"
    vm_files = call("vm-sources", "/usr/bin/git", "ls-files", "-z", "--",
                    "vm/Cargo.toml", "vm/Cargo.lock", "vm/src", "vm/include", "vm/tests")[0].split("\0")
    inputs = [HERE / "replay.py", BENCHMARK / "matched_task.py", INSTALLED / "run.py",
              INSTALLED / "replay_abi.py", EXPERIMENTS / "fieldlog-reactor/support.py",
              EXPERIMENTS / "profile-budget/analyze.py", ROOT / "compiler/qualification_support.py",
              native, adapter, prior, *host, *(ROOT / path for path in vm_files if path)]
    before = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in inputs}

    call("native-feature-build", "/usr/bin/swiftc", "-O", "-swift-version", "6", "-module-cache-path",
         out / "native-modules", native, "-o", out / "feature-probe", bound=35)
    feature = strict_json(call("native-feature", out / "feature-probe")[0])
    require(feature == dict(status="passed", completionBasisPoints=5000, codableRoundTrip=True,
                            unicodePreserved=True, emptyTitleRejected=True, wrongFieldTypeRejected=True,
                            nonfiniteRejected=True),
            f"native feature observations differ: {feature}")

    wasm = build_compact_guest(lambda *args: call(*args, bound=35), run.swift, out, "task-review",
                               [model, adapter], flags=("-D", "REQUIRE_REVIEW", "-module-cache-path",
                                                        out / "guest-modules"))
    module = wasm.read_bytes()
    descriptor = replay_abi.check_descriptors(module)
    refusals = replay_abi.negative_controls(module, descriptor)
    mutated, flag_offset = shared_memory_control(module)
    rejected_wasm = out / "task-shared-memory.wasm"
    rejected_wasm.write_bytes(mutated)

    cargo = [run.rust / "cargo"]
    cargo_flags = ["--offline", "--locked", "--release", "--jobs", "1", "--features",
                   "experimental-capability-native", "--manifest-path", vm / "Cargo.toml",
                   "--target-dir", out / "rust"]
    call("vm-build", *cargo, "build", "--lib", *cargo_flags, bound=100)
    archive = out / "rust/release/libmixer_vm.a"
    (out / "module.modulemap").write_text(
        f'module CMixerVMCapability {{ header "{vm}/include/mixer_vm_guest_ui.h" export * }}\n'
    )
    call("host-build", "/usr/bin/swiftc", "-O", "-whole-module-optimization", "-swift-version", "6",
         "-D", "SWIFT_SUPPORT_MATRIX", "-parse-as-library", "-module-cache-path", out / "native-modules",
         "-I", out, *host, archive, "-o", out / "compact-host", bound=35)

    observations = {}
    frames = {}
    expected = [frame["sha256"] for frame in json.loads(prior.read_text())["frames"]]
    for mode in ("native", "guest"):
        row = strict_json(call(f"compact-{mode}", out / "compact-host", mode, wasm)[0])
        frames[mode] = [base64.b64decode(frame, validate=True) for frame in row.pop("frames")]
        require([sha(frame) for frame in frames[mode]] == expected, f"{mode}: wrong FieldLog frame bytes")
        require(row == dict(truncatedRefusals=3, mismatchedRefusals=3, closed=mode == "guest"),
                f"{mode}: unexpected event or close counts")
        observations[mode] = row
    require(frames["guest"] == frames["native"], "FieldLog paths returned different bytes")

    boundary = strict_json(call("shared-memory", out / "compact-host", "shared-memory", rejected_wasm)[0])
    expected_refusal = dict(status=1, code="unsupported",
                            message="shared/memory64 memory is unsupported", offset=flag_offset + 1)
    require(boundary == dict(validation=expected_refusal, construction=expected_refusal),
            f"wrong shared-memory refusal: {boundary}")

    controls = {}
    for suite in ("experimental_guest_ui_validation", "experimental_capability_guest"):
        output = call(suite, *cargo, "test", "--test", suite, *cargo_flags, bound=75)[0]
        [summary] = [line for line in output.splitlines() if line.startswith("test result: ok.")]
        require(re.match(r"test result: ok\. [1-9]\d* passed; 0 failed;", summary),
                f"missing executed controls for {suite}: {summary}")
        controls[suite] = summary

    require(all(sha((ROOT / path).read_bytes()) == digest for path, digest in before.items()),
            "replay inputs changed")
    return dict(
        observedUTC=datetime.now(timezone.utc).isoformat(), revision=revision, tree=tree,
        sourceManifestSHA256=sha(json.dumps(before, sort_keys=True).encode()),
        replaySources={str(path.relative_to(ROOT)): before[str(path.relative_to(ROOT))]
                       for path in [Path(__file__), native, adapter, *host]},
        toolVersions={**versions, "python": sys.version.split()[0], "architecture": os.uname().machine},
        nativeFeatureProbe=feature, taskCompletion=dict(**observations, frameSHA256=expected),
        compactWasm=identity(wasm), vmArchive=identity(archive),
        descriptorGuardRefusals=sorted(refusals),
        sharedMemoryControl=dict(**identity(rejected_wasm), changedByteOffset=flag_offset,
                                 sessionHandlePublished=False, **boundary),
        vmTestResults=controls, commands=run.commands,
    )


def main():
    require((os.uname().sysname, os.uname().machine) == ("Darwin", "arm64"), "requires arm64 macOS")
    require(Path.cwd() == ROOT, "run from the Mixer checkout root")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    local = ROOT / "verification/local"
    local.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="l03-swift-profile-", dir=local))
    run = Run(scratch)
    try:
        result = campaign(run)
    finally:
        if run.active is not None:
            raise RuntimeError(f"UNKNOWN custody for {run.active}; preserve {scratch}")
        shutil.rmtree(scratch)
    result["custody"] = dict(directReapedAndGroupsObservedAbsent=len(run.commands), unknown=0,
                             observedPeakScratchBytes=run.peak_scratch, scratchLimitBytes=SCRATCH_LIMIT,
                             scratchRemoved=not scratch.exists())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

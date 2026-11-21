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
import struct
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


def floating_point_control(run, host, wasm):
    def same(name, operands, results):
        return name, (operands, results), (operands, results)

    # Expected results are exact literals. The two precision-boundary cases
    # straddle the last consecutive integer in the respective formats.
    cases = [
        same("fractional", (1.5, 0.5), (2, 1, 0.75, 3, 0)),
        same("ordered", (0.5, 2), (2.5, -1.5, 1, 0.25, 1)),
        ("below-precision-boundary",
         ((16_777_215, 1), (16_777_216, 16_777_214, 16_777_215, 16_777_215, 0)),
         ((9_007_199_254_740_991, 1), (9_007_199_254_740_992, 9_007_199_254_740_990,
                                     9_007_199_254_740_991, 9_007_199_254_740_991, 0))),
        ("at-precision-boundary",
         ((16_777_216, 1), (16_777_216, 16_777_215, 16_777_216, 16_777_216, 0)),
         ((9_007_199_254_740_992, 1), (9_007_199_254_740_992, 9_007_199_254_740_991,
                                     9_007_199_254_740_992, 9_007_199_254_740_992, 0))),
        ("smallest-normal",
         ((2.0**-126, 0.5), (0.5, -0.5, 2.0**-127, 2.0**-125, 1)),
         ((2.0**-1022, 0.5), (0.5, -0.5, 2.0**-1023, 2.0**-1021, 1))),
        same("positive-zero", (0.0, 2), (2, -2, 0.0, 0.0, 3)),
        same("negative-zero", (-0.0, 2), (2, -2, -0.0, -0.0, 3)),
    ]
    expected = [bytes(56)]
    operands = {}
    for name, (f32_input, f32_output), (f64_input, f64_output) in cases:
        operands[name] = struct.pack("<2f2d", *f32_input, *f64_input)
        expected.append(struct.pack("<4f4d2I", *f32_output[:4], *f64_output[:4],
                                    f32_output[4], f64_output[4]))
    return dict(
        inputLayout="little-endian Float pair, then Double pair",
        frameLayout="four Float results, four Double results (+, -, *, /), then two UInt32 flags (< bit 0, == zero bit 1)",
        **replay_preview(run, host, wasm, "floating", operands, expected),
    )


def associated_types_control(run, host, wasm):
    # Compare the same raw readings under both formats, then cross each format's boundary.
    cases = [
        ("signed-decrease", 0, 4, 1, -3),
        ("counter-wrap", 1, 4, 1, 65_533),
        ("signed-boundary", 0, 0x7fff, 0x8000, -65_535),
        ("counter-increase", 1, 100, 105, 5),
    ]
    operands = {name: struct.pack("<BHH", format_tag, baseline, current)
                for name, format_tag, baseline, current, _ in cases}
    expected = [bytes(4), *(struct.pack("<i", result) for *_, result in cases)]
    return dict(
        inputLayout="format byte (0 signed, 1 counter), then baseline and current little-endian UInt16 bits",
        frameLayout="little-endian Int32 change",
        truncatedInputHex=next(iter(operands.values()))[:-1].hex(),
        **replay_preview(run, host, wasm, "associated", operands, expected),
    )


def replay_preview(run, host, wasm, name, operands, expected):
    input_file = run.scratch / f"{name}-inputs"
    input_file.write_bytes(b"".join(operands.values()))
    observations = {}
    names = ["initial", *operands]
    for mode in ("native", "guest"):
        label = f"{name}-{mode}"
        row = strict_json(run.command(label, host, label, wasm, input_file)[0])
        frames = [base64.b64decode(frame, validate=True) for frame in row.pop("frames")]
        require(len(frames) == len(expected), f"{label}: missing frames")
        for case, actual, target in zip(names, frames, expected, strict=True):
            require(actual == target, f"{label}: {case} expected {target.hex()}, got {actual.hex()}")
        fuel = row.pop("guestFuel")
        require(row == dict(truncatedRefusedWithoutPublication=True, closed=mode == "guest"),
                f"{label}: unexpected refusal or close: {row}")
        require((len(fuel) == len(operands) and all(0 < turn <= 1_000_000 for turn in fuel))
                if mode == "guest" else not fuel, f"{label}: unexpected fuel: {fuel}")
        observations[mode] = dict(**row, guestFuel=fuel,
                                 framesHex=dict(zip(names, (frame.hex() for frame in frames), strict=True)))
    require(observations["native"]["framesHex"] == observations["guest"]["framesHex"],
            f"{name}: frame bytes differ between native Swift and the owned VM")
    return dict(
        inputFile=identity(input_file),
        inputsHex={case: value.hex() for case, value in operands.items()},
        truncatedInputBytes=len(next(iter(operands.values()))) - 1,
        **observations,
    )


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
    floating = HERE / "FloatingPoint.swift"
    associated = HERE / "AssociatedTypes.swift"
    preview_guest = HERE / "CompactPreviewGuest.swift"
    host = [HERE / "CompactHost.swift", floating, associated, BENCHMARK / "MatchedTask.swift", model, *runtime_sources]
    native = HERE / "Sources/FeatureProbe/main.swift"
    version_commands = {
        "macOS": ("/usr/bin/sw_vers",),
        "nativeSwift": ("/usr/bin/swiftc", "--version"),
        "guestSwift": (run.swift / "swiftc", "--version"),
        "linker": (run.swift / "wasm-ld", "--version"),
        "objdump": (run.swift / "llvm-objdump", "--version"),
        "rustc": (run.rust / "rustc", "--version"),
        "cargo": (run.rust / "cargo", "--version"),
    }
    versions = {key: call(key, *command)[0].strip() for key, command in version_commands.items()}
    versions["objdump"] = versions["objdump"].split("\n\n", 1)[0]
    vm = ROOT / "vm"
    vm_files = call("vm-sources", "/usr/bin/git", "ls-files", "-z", "--",
                    "vm/Cargo.toml", "vm/Cargo.lock", "vm/src", "vm/include", "vm/tests", "vm/examples")[0].split("\0")
    inputs = [HERE / "replay.py", BENCHMARK / "matched_task.py", INSTALLED / "run.py",
              INSTALLED / "replay_abi.py", EXPERIMENTS / "fieldlog-reactor/support.py",
              EXPERIMENTS / "profile-budget/analyze.py", ROOT / "compiler/qualification_support.py",
              native, adapter, prior, preview_guest, *host, *(ROOT / path for path in vm_files if path)]
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
    floating_wasm = build_compact_guest(
        lambda *args: call(*args, bound=35), run.swift, out, "floating", [floating, preview_guest],
        flags=("-module-cache-path", out / "guest-modules"))
    associated_wasm = build_compact_guest(
        lambda *args: call(*args, bound=35), run.swift, out, "associated", [associated, preview_guest],
        flags=("-D", "ASSOCIATED_TYPES_GUEST", "-module-cache-path", out / "guest-modules"))
    for preview_wasm in (floating_wasm, associated_wasm):
        replay_abi.check_descriptors(preview_wasm.read_bytes())
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

    floating_point = floating_point_control(run, out / "compact-host", floating_wasm)
    associated_types = associated_types_control(run, out / "compact-host", associated_wasm)
    disassembly = call("floating-disassembly", run.swift / "llvm-objdump", "--disassemble", floating_wasm)[0]
    instructions = sorted(set(re.findall(r"\bf(?:32|64)\.(?:add|sub|mul|div|lt|eq)\b", disassembly)))
    require(len(instructions) == 12, f"missing floating-point instructions in the executed module: {instructions}")

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
                       for path in [Path(__file__), native, adapter, preview_guest, *host]},
        toolVersions={**versions, "python": sys.version.split()[0], "architecture": os.uname().machine},
        nativeFeatureProbe=feature, taskCompletion=dict(**observations, frameSHA256=expected),
        floatingPointPreview=dict(
            installedABI="Guest UI v1", vmProfile="table-memory-v3",
            memoryPages=1, fuelPerTurn=1_000_000, hostCallsPerTurn=0,
            wasm=identity(floating_wasm), hostExecutable=identity(out / "compact-host"),
            instructions=instructions, **floating_point),
        associatedTypesPreview=dict(
            installedABI="Guest UI v1", vmProfile="table-memory-v3",
            memoryPages=1, fuelPerTurn=1_000_000, hostCallsPerTurn=0,
            wasm=identity(associated_wasm), **associated_types),
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

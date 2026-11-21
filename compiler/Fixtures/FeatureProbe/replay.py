#!/usr/bin/env python3
"""Replay the public Swift language controls on arm64 macOS without a device."""

import argparse
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
from run import SDK_NAME, build_compact_guest, replay_abi
from analyze import Reader
from qualification_support import strict_json

STOCK_WASI_LIBC_BYTES = 1_040_606
STOCK_WASI_LIBC_SHA256 = "42d929e52aaeac6c4ed56946cd3e92e40574322bc43af529c19cfbf67893b352"


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


def property_wrapper_control(run, host, wasm):
    cases = {
        "set": (240, 240, 1),
        "clamp": (1_250, 1_000, 2),
        "same-bounded-value": (1_200, 1_000, 2),
        "update-after-refusal": (480, 480, 3),
    }
    operands = {name: struct.pack("<H", reading) for name, (reading, *_) in cases.items()}
    expected = [bytes(8), *(struct.pack("<2I", value, changes) for _, value, changes in cases.values())]
    return dict(
        inputLayout="little-endian UInt16 reading; 65535 reserved",
        frameLayout="little-endian UInt32 bounded reading followed by UInt32 count of changes",
        **replay_preview(run, host, wasm, "wrapper", operands, expected, refused_input=b"\xff\xff"),
    )


def replay_preview(run, host, wasm, name, operands, expected, *, refused_input=None):
    input_file = run.scratch / f"{name}-inputs"
    events = list(operands.values())
    if refused_input is None:
        invalid = events[0][:-1]
        refusal_frame = expected[-1]
    else:
        invalid = refused_input
        refusal_frame = expected[-2]
        events.insert(-1, invalid)
    input_file.write_bytes(b"".join(events))
    names = ["initial", *operands]
    observations = {
        mode: observe_preview(run, host, wasm, input_file, f"{name}-{mode}", names, expected, refusal_frame)
        for mode in ("native", "guest")
    }
    return dict(
        inputFile=identity(input_file),
        inputOrderHex=[event.hex() for event in events],
        inputsHex={case: value.hex() for case, value in operands.items()},
        refusedInputHex=invalid.hex(),
        **observations,
    )


def observe_preview(run, host, wasm, input_file, label, names, expected, refusal_frame):
    row = strict_json(run.command(label, host, label, wasm, input_file)[0])
    frames = [base64.b64decode(frame, validate=True) for frame in row.pop("frames")]
    require(len(frames) == len(expected), f"{label}: missing frames")
    for case, actual, target in zip(names, frames, expected, strict=True):
        require(actual == target, f"{label}: {case} expected {target.hex()}, got {actual.hex()}")
    refused = base64.b64decode(row.pop("refusedFrame"), validate=True)
    require(refused == refusal_frame, f"{label}: refusal changed the previous frame")
    fuel = row.pop("guestFuel")
    guest = label.endswith("-guest")
    retirement = dict(closed=guest)
    if label in ("builder-guest", "fixed-builder-guest", "enum-throws-guest", "closure-guest"):
        retirement["reclaimedRegistrySlot"] = True
    require(row == retirement, f"{label}: unexpected close: {row}")
    require((len(fuel) == len(expected) - 1 and all(0 < turn <= 1_000_000 for turn in fuel))
            if guest else not fuel, f"{label}: unexpected fuel: {fuel}")
    return dict(**row, guestFuel=fuel, refusedFrameHex=refused.hex(),
                framesHex=dict(zip(names, (frame.hex() for frame in frames), strict=True)))


def compact_host_sources():
    runtime = ROOT / "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime"
    return [
        *(HERE / f"{name}.swift" for name in
          ("CompactHost", "FloatingPoint", "AssociatedTypes", "PropertyWrapper", "ResultBuilder",
           "FixedSlotResultBuilder", "EnumTypedThrows", "EscapingClosure")),
        BENCHMARK / "MatchedTask.swift",
        INSTALLED / "TaskCompletion.swift",
        *(runtime / f"{name}.swift" for name in ("Types", "Failure", "GuestDebugLines")),
    ]


def vm_release_flags(run):
    return ["--offline", "--locked", "--release", "--jobs", "1", "--features",
            "experimental-capability-native", "--manifest-path", ROOT / "vm/Cargo.toml",
            "--target-dir", run.scratch / "rust"]


def build_compact_host(run, sources, *, fixture_flags=()):
    out = run.scratch
    run.command("vm-build", run.rust / "cargo", "build", "--lib", *vm_release_flags(run), bound=100)
    archive = out / "rust/release/libmixer_vm.a"
    header = ROOT / "vm/include/mixer_vm_guest_ui.h"
    (out / "module.modulemap").write_text(f'module CMixerVMCapability {{ header "{header}" export * }}\n')
    run.command("host-build", "/usr/bin/swiftc", "-O", "-whole-module-optimization", "-swift-version", "6",
                "-D", "SWIFT_SUPPORT_MATRIX", *fixture_flags, "-parse-as-library", "-module-cache-path",
                out / "native-modules", "-I", out, *sources, archive, "-o", out / "compact-host", bound=35)
    return archive


def result_builder_campaign(run, result, *, fixed, stock_wasi_allocator=False):
    cases = [
        ("ordinary-two", b"\x00\x01\x02", b".12\x00"),
        ("priority-three", b"\x01\x04\x03", b"!456"),
        ("refused-four", b"\x01\x04\x04", None),
        ("ordinary-empty-after-refusal", b"\x00\x09\x00", b".\x00\x00\x00"),
    ]
    if fixed:
        cases.insert(0, ("priority-one", b"\x01\x09\x01", b"!9\x00\x00"))
    focused_preview_campaign(
        run, result, cases,
        mode="fixed-builder" if fixed else "builder",
        source="FixedSlotResultBuilder" if fixed else "ResultBuilder",
        define="FIXED_SLOT_RESULT_BUILDER_GUEST" if fixed else "RESULT_BUILDER_GUEST",
        scope=("Synthetic Foundation-free fixed-slot menu builder on arm64 macOS" if fixed else
               "Synthetic Foundation-free menu builder on arm64 macOS"),
        module_name="MixerResultBuilderProbe" if stock_wasi_allocator else None,
        guest_command=stock_allocator_guest_command(run, result) if stock_wasi_allocator else None,
    )


def enum_typed_throws_campaign(run, result):
    cases = [
        ("flat-fee", bytes((1, 12, 0)), struct.pack("<2I", 12, 0)),
        ("item-at-limit", bytes((0, 10, 100)), struct.pack("<2I", 1_000, 0)),
        ("refused-over-limit", bytes((0, 11, 100)), None),
        ("item-after-refusal", bytes((0, 3, 19)), struct.pack("<2I", 57, 1_100)),
    ]
    focused_preview_campaign(
        run, result, cases, mode="enum-throws", source="EnumTypedThrows", define="ENUM_TYPED_THROWS_GUEST",
        scope="One Foundation-free action enum and a concrete typed throw/catch on arm64 macOS",
        module_name="MixerEnumTypedThrowProbe",
    )


def stock_allocator_guest_command(run, result):
    relative = (Path(".swiftpm/swift-sdks") / f"{SDK_NAME}.artifactbundle" / SDK_NAME /
                "wasm32-unknown-wasip1/WASI.sdk/lib/wasm32-wasip1/libc.a")
    installed = Path.home() / relative
    try:
        require(installed.is_file(), f"missing Swift 6.3.3 WASI archive at ~/{relative}")
        with installed.open("rb") as stream:
            data = stream.read(STOCK_WASI_LIBC_BYTES + 1)
    except OSError as error:
        raise ValueError(f"cannot read Swift 6.3.3 WASI archive at ~/{relative}: {error.strerror}") from error
    require(len(data) == STOCK_WASI_LIBC_BYTES and sha(data) == STOCK_WASI_LIBC_SHA256,
            f"Swift 6.3.3 WASI archive SHA-256 mismatch at ~/{relative}")
    archive = run.scratch / "libc.a"
    archive.write_bytes(data)
    evidence = result["stockWasiAllocator"] = {
        "sdkArchive": dict(path=f"~/{relative}", bytes=len(data), sha256=STOCK_WASI_LIBC_SHA256),
    }

    def command(label, *args):
        if not label.endswith("-link"):
            return run.command(label, *args, bound=35)

        # The compact builder ends its link invocation with the object and -o output.
        *link_args, guest_object, output_flag, output = args
        evidence["guestObject"] = identity(guest_object)
        _, diagnostic, _ = run.command(f"{label}-without-libc", *args, bound=35, expected=1)
        symbols = re.findall(r"undefined symbol: (\S+)", diagnostic)
        require(set(symbols) == {"free", "posix_memalign"} and not output.exists(),
                f"unexpected no-library link diagnostic\n{diagnostic}")
        evidence["baselineRefusal"] = diagnostic.replace(str(run.scratch), "$RUN").strip()
        extraction = run.scratch / "libc-extraction.tsv"
        link_map = output.with_suffix(".map")
        run.command(label, *link_args, guest_object, archive, f"--why-extract={extraction}", f"--Map={link_map}",
                    output_flag, output, bound=35)
        evidence["archiveExtraction"] = extraction.read_text().replace(f"{run.scratch}/", "").splitlines()
        evidence["retainedArchiveMembers"] = sorted(set(re.findall(r"\blibc\.a\(([^)]+)\)", link_map.read_text())))

    return command


def escaping_closure_campaign(run, result, *, value_only, stock_wasi_allocator=False):
    cases = [
        # Frame bytes: selected kind, invocation value, deinit count, last released kind.
        ("store-title", bytes((1, 42)), bytes((1, 0, 0, 0))),
        ("invoke-title", bytes((3, 3)), bytes((1, 45, 0, 0))),
        ("invoke-title-again", bytes((3, 5)), bytes((1, 47, 0, 0))),
        ("replace-with-inspection", bytes((2, 70)), bytes((2, 0, 1, 1))),
        ("invoke-inspection", bytes((3, 4)), bytes((2, 66, 1, 1))),
        ("release-inspection", bytes((4, 0)), bytes((0, 0, 2, 2))),
        ("refuse-invocation-after-release", bytes((3, 1)), None),
        ("release-empty-slot", bytes((4, 0)), bytes((0, 0, 2, 2))),
    ]
    fixture_flags = ()
    capture = "capturing a selected value in an object"
    if value_only:
        cases = [(name, event, frame[:2] + bytes(2) if frame is not None else None)
                 for name, event, frame in cases]
        fixture_flags = ("-D", "ESCAPING_CLOSURE_VALUE_ONLY")
        capture = "capturing a selected value directly"
    guest_command = stock_allocator_guest_command(run, result) if stock_wasi_allocator else None
    focused_preview_campaign(
        run, result, cases, mode="closure", source="EscapingClosure", define="ESCAPING_CLOSURE_GUEST",
        scope=f"One escaping inspection closure {capture} on arm64 macOS",
        module_name="MixerEscapingClosureProbe", fixture_flags=fixture_flags,
        guest_command=guest_command,
    )


def focused_preview_campaign(run, result, cases, *, mode, source, define, scope,
                             module_name=None, fixture_flags=(), guest_command=None):
    names = ["initial", *(name for name, _, frame in cases if frame is not None)]
    frames = [frame for _, _, frame in cases if frame is not None]
    expected = [bytes(len(frames[0])), *frames]
    refusal_frame = frames[-2]
    input_file = run.scratch / f"{mode}-inputs"
    input_file.write_bytes(b"".join(event for _, event, _ in cases))
    host = run.scratch / "compact-host"
    fixture = HERE / f"{source}.swift"
    adapter = HERE / "CompactPreviewGuest.swift"
    sources = compact_host_sources()
    result.update(
        observedUTC=datetime.now(timezone.utc).isoformat(),
        revision=run.command("revision", "/usr/bin/git", "rev-parse", "HEAD")[0].strip(),
        tree=run.command("tree", "/usr/bin/git", "rev-parse", "HEAD^{tree}")[0].strip(),
        vmTree=run.command("vm-tree", "/usr/bin/git", "rev-parse", "HEAD:vm")[0].strip(),
        scope=scope,
        guestTarget=dict(abi="Guest UI V1", profile="table-memory-v3", memoryPages=1,
                         fuelPerTurn=1_000_000, hostCallsPerTurn=0),
        sources={str(path.relative_to(ROOT)): identity(path) for path in [Path(__file__), adapter, *sources]},
        events=[dict(case=name, inputHex=event.hex(), accepts=frame is not None)
                for name, event, frame in cases],
    )
    result["tools"] = {label: run.command(label, *argv)[0].strip() for label, argv in {
        "macOS": ("/usr/bin/sw_vers",),
        "nativeSwift": ("/usr/bin/swiftc", "--version"),
        "guestSwift": (run.swift / "swiftc", "--version"),
        "linker": (run.swift / "wasm-ld", "--version"),
        "rustc": (run.rust / "rustc", "--version"),
        "cargo": (run.rust / "cargo", "--version"),
    }.items()}
    archive = build_compact_host(run, sources, fixture_flags=fixture_flags)
    result["vmArchive"] = identity(archive)
    result["hostExecutable"] = identity(host)
    result["native"] = observe_preview(
        run, host, run.scratch / f"{mode}.wasm", input_file, f"{mode}-native", names, expected, refusal_frame)
    module_flags = ("-module-name", module_name) if module_name else ()
    wasm = build_compact_guest(
        guest_command or (lambda *args: run.command(*args, bound=35)),
        run.swift, run.scratch, mode, [fixture, adapter],
        flags=("-D", define, *fixture_flags, "-module-cache-path", run.scratch / "guest-modules", *module_flags),
        object_via_stdout=module_name is not None)
    result["wasm"] = identity(wasm)
    descriptors = replay_abi.check_descriptors(wasm.read_bytes())
    result["guestDescriptors"] = {key: descriptors[key] for key in ("imports", "memories", "startFunction")}
    if guest_command is not None:
        result["guestDescriptors"]["exports"] = descriptors["exports"]
    result["guest"] = observe_preview(run, host, wasm, input_file, f"{mode}-guest", names, expected, refusal_frame)
    for key in ("framesHex", "refusedFrameHex"):
        require(result["native"][key] == result["guest"][key], f"{mode}: native and guest differ in {key}")


def actor_isolation_campaign(run, result):
    run.env["DEVELOPER_DIR"] = "/Applications/Xcode_26.6.app/Contents/Developer"
    call = run.command
    source = HERE / "ActorIsolation.swift"
    refusal = HERE / "ActorIsolationRefusal.swift"
    swift = run.swift / "swiftc"
    sdk = call("host-sdk", "/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path")[0].strip()
    result.update(
        observedUTC=datetime.now(timezone.utc).isoformat(),
        revision=call("revision", "/usr/bin/git", "rev-parse", "HEAD")[0].strip(),
        tree=call("tree", "/usr/bin/git", "rev-parse", "HEAD^{tree}")[0].strip(),
        tools={
            "swift": call("swift-version", swift, "--version")[0].strip(),
            "xcode": call("xcode-version", "/usr/bin/xcodebuild", "-version")[0].strip(),
        },
        scope="Native actor isolation and the pinned Embedded Swift Wasm compiler boundary",
        sources={str(path.relative_to(ROOT)): identity(path) for path in (Path(__file__), source, refusal)},
    )
    binary = run.scratch / "actor-native"
    native = (swift, "-sdk", sdk, "-target", "arm64-apple-macosx15.0", "-swift-version", "6",
              "-module-cache-path", run.scratch / "native-cache")
    call("actor-native-build", *native, "-parse-as-library", "-O", source, "-o", binary, bound=35)
    observation = call("actor-native-observation", binary)[0]
    require(observation == "0\n1\n1\n", f"unexpected checklist states: {observation!r}")
    _, native_diagnostic, _ = call("actor-native-refusal", *native, "-typecheck", refusal, expected=1)
    require("actor-isolated instance method 'count()' in a synchronous nonisolated context" in native_diagnostic,
            f"unexpected native isolation diagnostic:\n{native_diagnostic}")
    result["native"] = dict(states=[0, 1, 1], executable=identity(binary),
                            isolationRefusal=native_diagnostic.replace(str(ROOT), "$REPO").strip())

    guest = (swift, "-target", "wasm32-unknown-none-wasm", "-enable-experimental-feature", "Embedded",
             "-swift-version", "6", "-parse-as-library", "-whole-module-optimization", "-Osize",
             "-emit-object", "-module-cache-path", run.scratch / "guest-cache")
    refusals = {}
    for name, flags, expected in (
        ("implicit-concurrency", (), ("unknown attribute 'MainActor'", "required for async main")),
        ("explicit-concurrency", ("-D", "EXPLICIT_CONCURRENCY_IMPORT"),
         ("could not find module '_Concurrency' for target 'wasm32-unknown-none-wasm'",)),
    ):
        output = run.scratch / f"{name}.o"
        _, diagnostic, _ = call(name, *guest, *flags, source, "-o", output, expected=1, bound=35)
        require(all(fragment in diagnostic for fragment in expected) and not output.exists(),
                f"unexpected Embedded Swift outcome:\n{diagnostic}")
        refusals[name] = diagnostic.replace(str(ROOT), "$REPO").replace(str(Path.home()), "$USER_HOME").strip()
    result["embedded"] = dict(target="wasm32-unknown-none-wasm", objectProduced=False, refusals=refusals)


def task_cancellation_campaign(run, result):
    run.env["DEVELOPER_DIR"] = "/Applications/Xcode_26.6.app/Contents/Developer"
    call = run.command
    swift = run.swift / "swiftc"
    source = HERE / "TaskCancellation.swift"
    sdk = call("host-sdk", "/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path")[0].strip()
    result.update(
        observedUTC=datetime.now(timezone.utc).isoformat(),
        revision=call("revision", "/usr/bin/git", "rev-parse", "HEAD")[0].strip(),
        tree=call("tree", "/usr/bin/git", "rev-parse", "HEAD^{tree}")[0].strip(),
        tools={
            "swift": call("swift-version", swift, "--version")[0].strip(),
            "xcode": call("xcode-version", "/usr/bin/xcodebuild", "-version")[0].strip(),
        },
        scope="Swift Task.isCancelled and Task.checkCancellation with an explicitly cancelled task",
        sources={str(path.relative_to(ROOT)): identity(path) for path in (Path(__file__), source)},
    )
    binary = run.scratch / "task-cancellation-native"
    call("task-cancellation-native-build", swift, "-sdk", sdk, "-target", "arm64-apple-macosx15.0",
         "-swift-version", "6", "-module-cache-path", run.scratch / "native-cache",
         "-parse-as-library", "-O", "-D", "EXPLICIT_CONCURRENCY_IMPORT", source, "-o", binary, bound=35)
    observation = call("task-cancellation-native-observation", binary)[0]
    require(observation == "0 0\n0 3\n0 0\n", f"unexpected cancellation states: {observation!r}")
    result["native"] = dict(executable=identity(binary), flagsMeaning="1 = cancelled, 2 = CancellationError",
                            control=[0, 0], cancelled=[0, 3], nextControl=[0, 0])

    target = "wasm32-unknown-none-wasm"
    guest = (swift, "-target", target, "-enable-experimental-feature", "Embedded", "-swift-version", "6",
             "-parse-as-library", "-whole-module-optimization", "-Osize", "-emit-object",
             "-module-cache-path", run.scratch / "guest-cache")
    refusals = {}
    for name, flags, expected in (
        ("implicit-concurrency", (), "cannot find 'Task' in scope"),
        ("explicit-concurrency", ("-D", "EXPLICIT_CONCURRENCY_IMPORT"),
         "could not find module '_Concurrency' for target 'wasm32-unknown-none-wasm'"),
    ):
        output = run.scratch / f"{name}.o"
        _, diagnostic, _ = call(name, *guest, *flags, source, "-o", output, expected=1, bound=35)
        require(expected in diagnostic and not output.exists(), f"unexpected Embedded Swift outcome:\n{diagnostic}")
        refusals[name] = diagnostic.replace(str(ROOT), "$REPO").replace(str(Path.home()), "$USER_HOME").strip()
    control = run.scratch / "scalar-control.o"
    call("scalar-control", *guest, "-D", "EMBEDDED_SCALAR_CONTROL", source, "-o", control, bound=35)
    require(control.read_bytes().startswith(b"\x00asm\x01\x00\x00\x00"), "missing Wasm control object")
    result["embedded"] = dict(target=target, objectProduced=False, refusals=refusals,
                              scalarControl=identity(control), vmInvoked=False)


def campaign(run):
    call = run.command
    out = run.scratch
    revision = call("revision", "/usr/bin/git", "rev-parse", "HEAD")[0].strip()
    tree = call("tree", "/usr/bin/git", "rev-parse", "HEAD^{tree}")[0].strip()
    model = INSTALLED / "TaskCompletion.swift"
    adapter = INSTALLED / "InstalledGuest.swift"
    prior = ROOT / "verification/receipts/l03-d3-task-review-event-trap-7b61fe1c.json"
    floating = HERE / "FloatingPoint.swift"
    associated = HERE / "AssociatedTypes.swift"
    wrapper = HERE / "PropertyWrapper.swift"
    preview_guest = HERE / "CompactPreviewGuest.swift"
    host = compact_host_sources()
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
    wrapper_wasm = build_compact_guest(
        lambda *args: call(*args, bound=35), run.swift, out, "wrapper", [wrapper, preview_guest],
        flags=("-D", "PROPERTY_WRAPPER_GUEST", "-module-cache-path", out / "guest-modules"))
    for preview_wasm in (floating_wasm, associated_wasm, wrapper_wasm):
        replay_abi.check_descriptors(preview_wasm.read_bytes())
    refusals = replay_abi.negative_controls(module, descriptor)
    mutated, flag_offset = shared_memory_control(module)
    rejected_wasm = out / "task-shared-memory.wasm"
    rejected_wasm.write_bytes(mutated)

    cargo = [run.rust / "cargo"]
    cargo_flags = vm_release_flags(run)
    archive = build_compact_host(run, host)

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
    property_wrapper = property_wrapper_control(run, out / "compact-host", wrapper_wasm)
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
        propertyWrapperPreview=dict(
            installedABI="Guest UI v1", vmProfile="table-memory-v3",
            memoryPages=1, fuelPerTurn=1_000_000, hostCallsPerTurn=0,
            wasm=identity(wrapper_wasm), **property_wrapper),
        compactWasm=identity(wasm), vmArchive=identity(archive),
        descriptorGuardRefusals=sorted(refusals),
        sharedMemoryControl=dict(**identity(rejected_wasm), changedByteOffset=flag_offset,
                                 sessionHandlePublished=False, **boundary),
        vmTestResults=controls, commands=run.commands,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    focused = parser.add_mutually_exclusive_group()
    focused.add_argument("--actor-isolation", action="store_true", help="check native and Embedded actor isolation")
    focused.add_argument("--task-cancellation", action="store_true",
                         help="check native Swift task cancellation and the Embedded boundary")
    focused.add_argument("--result-builder", action="store_true", help="run the dynamic-loop builder replay")
    focused.add_argument("--fixed-slot-result-builder", action="store_true", help="run the fixed-slot builder replay")
    focused.add_argument("--enum-typed-throws", action="store_true", help="run the enum payload and typed throws replay")
    focused.add_argument("--escaping-closure", action="store_true", help="run the escaping closure capture replay")
    focused.add_argument("--escaping-closure-value-only", action="store_true",
                         help="run the escaping closure without a captured object")
    parser.add_argument("--stock-wasi-allocator", action="store_true",
                        help="link the pinned Swift 6.3.3 WASI libc.a for a dynamic builder or closure replay")
    args = parser.parse_args()
    closure = args.escaping_closure or args.escaping_closure_value_only
    if args.stock_wasi_allocator and not (args.result_builder or closure):
        parser.error("--stock-wasi-allocator requires --result-builder, --escaping-closure, or --escaping-closure-value-only")
    require((os.uname().sysname, os.uname().machine) == ("Darwin", "arm64"), "requires arm64 macOS")
    require(Path.cwd() == ROOT, "run from the Mixer checkout root")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    local = ROOT / "verification/local"
    local.mkdir(exist_ok=True)
    prefix = "w07-enum-throws-" if args.enum_typed_throws else "l03-swift-profile-"
    if closure:
        prefix = "w07-escaping-closure-"
    scratch = Path(tempfile.mkdtemp(prefix=prefix, dir=local))
    run = Run(scratch)
    failed = False
    try:
        if (args.actor_isolation or args.task_cancellation or args.result_builder or args.fixed_slot_result_builder
                or args.enum_typed_throws or closure):
            result = {}
            try:
                if args.actor_isolation:
                    actor_isolation_campaign(run, result)
                elif args.task_cancellation:
                    task_cancellation_campaign(run, result)
                elif args.enum_typed_throws:
                    enum_typed_throws_campaign(run, result)
                elif closure:
                    escaping_closure_campaign(run, result, value_only=args.escaping_closure_value_only,
                                              stock_wasi_allocator=args.stock_wasi_allocator)
                else:
                    result_builder_campaign(run, result, fixed=args.fixed_slot_result_builder,
                                            stock_wasi_allocator=args.stock_wasi_allocator)
            except ValueError as error:
                result["failure"] = str(error)
                failed = True
            result["commands"] = run.commands
        else:
            result = campaign(run)
    finally:
        if run.active is not None:
            raise RuntimeError(f"UNKNOWN custody for {run.active}; preserve {scratch}")
        shutil.rmtree(scratch)
    result["custody"] = dict(directReapedAndGroupsObservedAbsent=len(run.commands), unknown=0,
                             observedPeakScratchBytes=run.peak_scratch, scratchLimitBytes=SCRATCH_LIMIT,
                             scratchRemoved=not scratch.exists())
    print(json.dumps(result, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

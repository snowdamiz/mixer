#!/usr/bin/env python3
"""Replay the ordinary guest-local allocation and release diagnostic."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
PIN = {
    "commit": "abadfffa100c61b724e4f021d294b0e1377fb00b",
    "tree": "6d78a4c5d1abb6c301f8621e702c6224b279ccdf",
    "vmTree": "ec1ddb74b7c6c2eabd91d1f60ed243ffc69ce6f4",
}
LIBC_SHA = "42d929e52aaeac6c4ed56946cd3e92e40574322bc43af529c19cfbf67893b352"
REVIEWED_VM_ARCHIVE_SHA = "6a9ef08edafb9a3f9c35d3a98197584987a3b70cb429fddba6e1c562a927b822"
CEILING = 256 * 1024**2
FUEL_LIMIT = 1_000_000
WASI_ENOMEM = 48
NOT_ATTEMPTED = 2**32 - 1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_vm_archive(archive_identity, independent_sha):
    require(archive_identity["sha256"] == independent_sha == REVIEWED_VM_ARCHIVE_SHA,
            f"reviewed VM archive SHA-256 mismatch: measured {archive_identity['sha256']}, "
            f"independent {independent_sha}, expected {REVIEWED_VM_ARCHIVE_SHA}")


def checked_observations(stdout):
    rows = [json.loads(line) for line in stdout.splitlines()]
    base = dict(pages=1, hostCalls=0, enomem=WASI_ENOMEM, fillAttempts=0,
                fillResult=NOT_ATTEMPTED, retryResult=NOT_ATTEMPTED, live=0,
                checkedBeforeRelease=0, survivorsChecked=0, replacementChecked=0,
                sameAddress=0, freed=0)
    filled = dict(base, fillAttempts=10, fillResult=WASI_ENOMEM, live=9)
    retried = dict(filled, retryResult=0, checkedBeforeRelease=9, survivorsChecked=8,
                   replacementChecked=1, sameAddress=1, freed=1)
    drained = dict(retried, live=0, freed=10)
    retired = dict(closeStatus=0, retiredStartupStatus=3)
    reopened = dict(sameRegistrySlot=True, newGeneration=True, retiredAfterReopenStatus=3,
                    identicalFreshFrame=True)
    session = [dict(frame, phase=phase) for phase, frame in enumerate((base, filled, retried, drained))]
    expected = [dict(guestUiV1ValidationStatus=0), *session, retired, reopened, *session, retired]
    require(len(rows) == len(expected), "unexpected observation count")
    for index, (row, want) in enumerate(zip(rows, expected, strict=True)):
        require(type(row) is dict, f"observation {index} must be an object")
        frame = dict(row)
        if "phase" in want:
            fuel = frame.pop("fuel", None)
            require(type(fuel) is int and 0 < fuel <= FUEL_LIMIT, f"observation {index} fuel out of range")
        require(frame == want and all(type(frame[key]) is type(value) for key, value in want.items()),
                f"observation {index} differs from the exact allocation and retirement scenario")
    require(rows[1:6] == rows[7:12], "fresh-session replay differed")
    return rows


def new_path(path, role):
    path = Path(os.path.abspath(path))
    resolved = path.parent.resolve(strict=True) / path.name
    require(not os.path.lexists(resolved), f"{role} already exists: {resolved}")
    return resolved


def publish_completed(receipt, output, scratch):
    custody = receipt["custody"]
    require(custody["unknown"] is None and
            0 < custody["reapedWithGroupAbsent"] == len(receipt["commands"]),
            "publication requires complete terminal command observations")
    payload = (json.dumps(receipt, indent=2) + "\n").encode()
    (scratch / "completed-receipt.json").write_bytes(payload)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".guest-allocation-") as staging:
        temporary = Path(staging) / "receipt.json"
        with temporary.open("xb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.link(temporary, output, follow_symlinks=False)
        directory = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    shutil.rmtree(scratch)


def campaign(run, receipt, pinned, output, identity, check_descriptors):
    call = run.command
    scratch = run.scratch
    paths = ("vm", "compiler/experiments/fieldlog-guest-benchmark/matched_task.py",
             "compiler/experiments/fieldlog-reactor/support.py",
             "compiler/experiments/profile-budget/analyze.py",
             "compiler/experiments/fieldlog-installed-guest/replay_abi.py")
    for key, ref in zip(PIN, ("HEAD", "HEAD^{tree}", "HEAD:vm"), strict=True):
        got = call(key, "/usr/bin/git", "rev-parse", ref)[0].strip()
        require(got == PIN[key], f"{key} differs from pin")
    call("source-before", "/usr/bin/git", "diff", "--exit-code", "HEAD", "--", *paths)
    require(not call("untracked-before", "/usr/bin/git", "ls-files", "--others", "--", *paths)[0],
            "unexpected input in pinned source")
    receipt["source"] = PIN

    clang = ["/usr/bin/clang", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror"]
    host_controls = scratch / "host-controls"
    call("host-controls-build", *clang, HERE / "host_controls.c", "-o", host_controls, bound=20)
    host_stdout = call("host-controls", host_controls, bound=5)[0]
    python_stdout, python_stderr, _ = call("runner-controls", sys.executable, HERE / "test_controls.py",
                                         "--verbose", bound=20)
    receipt["controls"] = {"host": host_stdout.strip(), "runner": (python_stdout + python_stderr).strip()}

    host_object = scratch / "host.o"
    call("host-compile", *clang,
         "-fmodules-cache-path=" + str(scratch / "clang-modules"), "-I", pinned / "vm/include",
         "-c", HERE / "host.c", "-o", host_object, bound=35)
    receipt["outputs"] = {host_object.name: identity(host_object)}

    sdk = (Path.home() / ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_wasm.artifactbundle"
           / "swift-6.3.3-RELEASE_wasm/wasm32-unknown-wasip1/WASI.sdk")
    libc = sdk / "lib/wasm32-wasip1/libc.a"
    require(identity(libc)["sha256"] == LIBC_SHA, "WASI libc differs from reviewed pin")
    headers = sdk / "include/wasm32-wasip1"
    receipt["dependencies"] = {
        "WASI.sdk/lib/wasm32-wasip1/libc.a": identity(libc),
        "WASI.sdk/include/wasm32-wasip1/__errno_values.h": identity(headers / "__errno_values.h"),
        "WASI.sdk/include/wasm32-wasip1/wasi/api.h": identity(headers / "wasi/api.h"),
        **{path: identity(pinned / path) for path in paths[1:]},
    }
    receipt["tools"] = {"python": platform.python_version(), "architecture": platform.machine()}
    for key, argv in {
        "macOS": ("/usr/bin/sw_vers",),
        "guestClang": (run.swift / "clang", "--version"),
        "guestSwift": (run.swift / "swiftc", "--version"),
        "guestLinker": (run.swift / "wasm-ld", "--version"),
        "hostClang": ("/usr/bin/clang", "--version"),
        "cargo": (run.rust / "cargo", "--version"),
        "rustc": (run.rust / "rustc", "--version"),
    }.items():
        receipt["tools"][key] = call(key, *argv)[0].strip()

    obj, wasm = scratch / "guest.o", scratch / "guest.wasm"
    why, link_map = scratch / "guest.why", scratch / "guest.map"
    call("guest-compile", run.swift / "clang", "--target=wasm32-unknown-wasip1", f"--sysroot={sdk}",
         "-isystem", headers,
         "-std=c11", "-Oz", "-Wall", "-Wextra", "-Werror", "-fno-stack-protector",
         "-mno-bulk-memory", "-ffunction-sections", "-fdata-sections", "-c", HERE / "guest.c",
         "-o", obj, bound=20)
    call("guest-link", run.swift / "wasm-ld", "--no-entry", "--gc-sections", "--strip-all",
         "-z", "stack-size=16384", "--initial-memory=65536", "--max-memory=65536",
         "--export=mixer_guest_ui_start_v1", "--export=mixer_guest_ui_event_v1",
         "--export=mixer_guest_capability_ready_v1", obj, libc,
         f"--why-extract={why}", f"--Map={link_map}", "-o", wasm, bound=20)
    receipt["descriptor"] = check_descriptors(wasm.read_bytes())
    disassembly = call("guest-disassembly", run.swift / "llvm-objdump", "-d", wasm)[0]
    receipt["memoryInstructionSites"] = [row.strip() for row in disassembly.splitlines()
                                         if "memory.size" in row or "memory.grow" in row]
    map_rows = [row.strip() for row in link_map.read_text().splitlines()
                if "(posix_memalign)" in row or "(free)" in row or "(sbrk)" in row]
    require(any("libc.a(dlmalloc.o):(posix_memalign)" in row for row in map_rows) and
            any("libc.a(dlmalloc.o):(free)" in row for row in map_rows) and
            any("libc.a(sbrk.o):(sbrk)" in row for row in map_rows), "allocator attribution")
    receipt["linkedAllocator"] = map_rows
    receipt["outputs"].update({path.name: identity(path) for path in (obj, wasm, link_map, why)})

    target = scratch / "rust"
    call("vm-build", run.rust / "cargo", "build", "--lib", "--offline", "--locked", "--release",
         "--jobs", "1", "--features", "experimental-capability-native",
         "--manifest-path", pinned / "vm/Cargo.toml", "--target-dir", target, bound=100)
    archive = target / "release/libmixer_vm.a"
    archive_identity = identity(archive)
    receipt["outputs"][archive.name] = archive_identity
    observed_sha = call("vm-sha256", "/usr/bin/shasum", "-a", "256", archive)[0].split()[0]
    verify_vm_archive(archive_identity, observed_sha)
    receipt["vmArchiveVerification"] = {
        "verifiedSHA256": observed_sha,
        "requiredReviewedSHA256": REVIEWED_VM_ARCHIVE_SHA,
    }
    executable = scratch / "host"
    call("host-link", "/usr/bin/clang", host_object, archive, "-o", executable, bound=35)
    receipt["outputs"][executable.name] = identity(executable)
    verify_vm_archive(identity(archive), observed_sha)
    require(not os.path.lexists(output), f"output already exists: {output}")

    stdout = call("owned-ui-run", executable, wasm, bound=8)[0]
    receipt["observations"] = checked_observations(stdout)
    receipt["outputs"]["owned-ui-run.out"] = identity(scratch / "owned-ui-run.out")
    call("source-after", "/usr/bin/git", "diff", "--exit-code", "HEAD", "--", *paths)
    require(not call("untracked-after", "/usr/bin/git", "ls-files", "--others", "--", *paths)[0],
            "unexpected output in pinned source")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True, help="clean checkout of the pinned Mixer commit")
    parser.add_argument("--scratch", type=Path, required=True, help="new directory for owned command scratch")
    parser.add_argument("--output", type=Path, required=True, help="new receipt path outside scratch")
    args = parser.parse_args()
    try:
        output = new_path(args.output, "output")
        scratch = new_path(args.scratch, "scratch")
        pinned = args.checkout.resolve(strict=True)
        require(not output.is_relative_to(scratch), "output must be outside scratch")
        require(not output.is_relative_to(pinned) and not scratch.is_relative_to(pinned),
                "scratch and output must be outside the pinned checkout")
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    sys.dont_write_bytecode = True
    experiments = pinned / "compiler/experiments"
    sys.path[:0] = [str(experiments / name) for name in (
        "fieldlog-guest-benchmark", "fieldlog-installed-guest", "fieldlog-reactor", "profile-budget")]
    sys.path.insert(0, str(pinned / "compiler"))
    import matched_task
    from matched_task import Run, identity
    from replay_abi import check_descriptors
    matched_task.SCRATCH_LIMIT = CEILING

    os.chdir(pinned)
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024**2, 128 * 1024**2))
    scratch.mkdir()
    run = None
    receipt = {
        "scope": "W07/L03 §7.3 ordinary guest-local allocation/release diagnostic",
        "observedUTC": datetime.now(timezone.utc).isoformat(),
        "inputs": {path: identity(HERE / path) for path in
                   ("allocator_control.h", "guest.c", "host.c", "host_expectation.h",
                    "run.py", "host_controls.c", "test_controls.py")},
        "profile": {"abi": "Guest UI V1", "vm": "table-memory-v3", "memoryPages": 1,
                    "hostCallsPerTurn": 0, "fuelPerTurn": FUEL_LIMIT, "stackBytes": 16384},
        "request": {"sizeBytes": 4096, "alignmentBytes": 64, "fillAttemptCeiling": 24,
                    "released": "middle block", "canaryOffsets": [0, 2048, 4095],
                    "eventBytes": [1, 2, 3]},
    }
    try:
        run = Run(scratch)
        require(not os.path.lexists(output), f"output already exists: {output}")
        campaign(run, receipt, pinned, output, identity, check_descriptors)
        receipt["status"] = "observed"
        experiment_alias = str(HERE).replace(str(Path.home()), "$USER_HOME")
        receipt["commands"] = [
            {**command, "argv": [arg.replace(experiment_alias, "$EXPERIMENT") for arg in command["argv"]]}
            for command in run.commands
        ]
        receipt["linkedAllocator"] = [row.replace(str(Path.home()), "$USER_HOME")
                                      for row in receipt["linkedAllocator"]]
        receipt["custody"] = {
            "reapedWithGroupAbsent": len(run.commands), "unknown": run.active,
            "peakScratchBytes": run.peak_scratch, "scratchByteCeiling": CEILING,
            "perFileByteCeiling": 128 * 1024**2, "campaignDeadlineSeconds": 240,
            "scratchPolicy": "Remove only after the receipt is published and synced.",
        }
        publish_completed(receipt, output, scratch)
    except (Exception, KeyboardInterrupt) as exc:
        active = run.active if run is not None else None
        closed = len(run.commands) if run is not None else 0
        failure = {"firstFailure": str(exc), "reapedWithGroupAbsent": closed,
                   "unknown": active, "scratch": str(scratch)}
        print(json.dumps(failure), file=sys.stderr)
        return 74 if active is not None else 1
    print(f"Observed exact allocation and retirement. Receipt: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Replay the maintained 1/1 allocator, then exercise an isolated 1/2 guest."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import sys
import time
from types import ModuleType

HERE = Path(__file__).resolve().parent
PIN = {
    "commit": "4f9eb3449cb7671b2e83222a28c85696c1741a59",
    "tree": "0fa4d9532bd879c555a82b66121dce8959d6b685",
    "vmTree": "ec1ddb74b7c6c2eabd91d1f60ed243ffc69ce6f4",
}
REVIEW = "verification/receipts/l03-guest-allocator-release-strict-abadfffa10.json"
BASELINE = "compiler/experiments/guest-local-allocation-control"
REVIEW_SHA = "9e48d90b3fb47b3411afdf5acaa6708811130dd4fb5be3c30a41c564228275a5"
QUALIFICATION_SUPPORT = "compiler/qualification_support.py"
QUALIFICATION_SHA = "af6a4ea7e22bd67a4b60f14058e834ca1442eb37414f03b71796434b8a98d16b"
HELPERS = {
    "qualification_support": QUALIFICATION_SUPPORT,
    "analyze": "compiler/experiments/profile-budget/analyze.py",
    "support": "compiler/experiments/fieldlog-reactor/support.py",
    "replay_abi": "compiler/experiments/fieldlog-installed-guest/replay_abi.py",
    "matched_task": "compiler/experiments/fieldlog-guest-benchmark/matched_task.py",
    "allocator_baseline": f"{BASELINE}/run.py",
}
SUCCESS = "observed_growth_at_cap_with_recovery"
VARIANT_SOURCES = ("allocator_control.h", "guest.c", "host.c")
MAXIMUM_PAGES = 2
PAGE_BYTES = 65536
BLOCK_BYTES = 4096
BLOCK_LIMIT = 32
FUEL_LIMIT = 1_000_000
NOT_ATTEMPTED = 2**32 - 1
ENOMEM = 48


def require(condition, message):
    if not condition:
        raise ValueError(message)


def new_path(path, role):
    path = Path(os.path.abspath(path))
    resolved = path.parent.resolve(strict=True) / path.name
    require(not os.path.lexists(resolved), f"{role} already exists: {resolved}")
    return resolved


def checkout_pin(pinned, scratch, custody):
    # Establish Git custody before any code from the checkout can run.
    argv = ["/usr/bin/git", "-C", str(pinned), "rev-parse", "--show-toplevel",
            "HEAD", "HEAD^{tree}", "HEAD:vm"]
    out = scratch / "checkout-pin.out"
    err = scratch / "checkout-pin.err"
    actions = [
        (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
        (os.POSIX_SPAWN_OPEN, 1, str(out), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
        (os.POSIX_SPAWN_OPEN, 2, str(err), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
    ]
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "GIT_NO_REPLACE_OBJECTS": "1"}
    custody["unknown"] = {"label": "checkout-pin", "pid": None}
    active_record = scratch / "active.json"
    active_record.write_text(json.dumps(custody["unknown"]) + "\n")
    pid = os.posix_spawn(argv[0], argv, env, setpgroup=0, file_actions=actions)
    custody["unknown"]["pid"] = pid
    active_record.write_text(json.dumps(custody["unknown"]) + "\n")
    deadline = time.monotonic() + 5
    while True:
        child, status = os.waitpid(pid, os.WNOHANG)
        if child:
            break
        require(time.monotonic() < deadline, "checkout pin lookup timed out")
        time.sleep(0.01)
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        custody["unknown"] = None
    require(custody["unknown"] is None, "checkout pin lookup group absence unproven")
    code = os.waitstatus_to_exitcode(status)
    custody["commands"].append({"label": "checkout-pin", "argv": [*argv[:2], "$REPO", *argv[3:]], "exit": code})
    require(code == 0, f"checkout pin lookup exit {code}: {err.read_text(errors='replace').strip()}")
    observed = out.read_text().splitlines()
    require(len(observed) == 4 and observed[0] == str(pinned), "checkout is not the repository root")
    for key, value in zip(PIN, observed[1:], strict=True):
        require(value == PIN[key], f"{key} differs from pin: expected {PIN[key]}, observed {value}")


def checked_source(pinned, relative, expected):
    path = pinned / relative
    require(path.resolve(strict=True) == path and path.is_file(), f"expected a regular source file: {relative}")
    data = path.read_bytes()
    observed = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    require(observed == expected, f"source bytes differ: {relative}: expected {expected}, observed {observed}")
    return data


def verified_inputs(pinned):
    reviewed = json.loads(checked_source(pinned, REVIEW, {"bytes": 19399, "sha256": REVIEW_SHA}))
    require(reviewed["source"]["vmTree"] == PIN["vmTree"], "reviewed VM tree differs")
    expected = {
        **{f"{BASELINE}/{name}": info for name, info in reviewed["inputs"].items()},
        **{name: info for name, info in reviewed["dependencies"].items() if name.startswith("compiler/")},
        QUALIFICATION_SUPPORT: {"bytes": 9458, "sha256": QUALIFICATION_SHA},
    }
    sources = {name: checked_source(pinned, name, info) for name, info in expected.items()}
    return reviewed, expected, sources


def load_helpers(pinned, sources):
    # Execute the checked bytes directly so module search and cached bytecode cannot replace them.
    loaded = {}
    for name, relative in HELPERS.items():
        filename = str(pinned / relative)
        module = ModuleType(name)
        module.__file__ = filename
        sys.modules[name] = module
        original_path = sys.path[:]
        try:
            exec(compile(sources[relative], filename, "exec"), module.__dict__)
        finally:
            sys.path[:] = original_path
        loaded[name] = module
    return loaded["allocator_baseline"], loaded["matched_task"], loaded["replay_abi"]


def growth_observations(stdout):
    rows = [json.loads(line) for line in stdout.splitlines()]
    require(len(rows) == 12, "expected 12 growth and lifecycle observations")
    require(all(type(row) is dict for row in rows), "growth observations must be objects")
    require(rows[1:6] == rows[7:12], "fresh-session replay differed")
    highest_end = rows[2].get("highestBlockEnd")
    require(type(highest_end) is int and PAGE_BYTES < highest_end <= MAXIMUM_PAGES * PAGE_BYTES
            and highest_end % 64 == 0, "no aligned allocation ending in page 2 within the cap")

    initial = dict(phase=0, pages=1, hostCalls=0, enomem=ENOMEM, fillAttempts=0, fillResult=NOT_ATTEMPTED,
                   retryResult=NOT_ATTEMPTED, live=0, checkedBeforeRelease=0, survivorsChecked=0,
                   replacementChecked=0, sameAddress=0, freed=0, growthAttempt=0, growthCanaries=0,
                   highestBlockEnd=0)
    filled = dict(initial, phase=1, pages=MAXIMUM_PAGES, fillAttempts=26, fillResult=ENOMEM, live=25,
                  growthAttempt=10, growthCanaries=9, highestBlockEnd=highest_end)
    retried = dict(filled, phase=2, checkedBeforeRelease=25, survivorsChecked=24, replacementChecked=1,
                   sameAddress=1, retryResult=0, freed=1)
    drained = dict(retried, phase=3, live=0, freed=26)
    closed = dict(closeStatus=0, retiredStartupStatus=3)
    reopened = dict(sameRegistrySlot=True, newGeneration=True, retiredAfterReopenStatus=3,
                    identicalFreshFrame=True)
    session = [initial, filled, retried, drained, closed]
    expected = [dict(guestUiV1ValidationStatus=0), *session, reopened, *session]
    for index, (row, want) in enumerate(zip(rows, expected, strict=True)):
        frame = dict(row)
        if "phase" in want:
            fuel = frame.pop("fuel", None)
            require(type(fuel) is int and 0 < fuel <= FUEL_LIMIT, f"observation {index} fuel out of range")
        require(frame == want and all(type(frame[key]) is type(value) for key, value in want.items()),
                f"observation {index} differs from the exact growth and retirement scenario")
    return rows


def observe_growth(run, host, wasm, receipt):
    try:
        stdout, _, _ = run.command("growth-ui-run", host, wasm, bound=8)
    except ValueError as error:
        if run.active is not None or not run.commands or run.commands[-1]["label"] != "growth-ui-run":
            raise
        stdout = (run.scratch / "growth-ui-run.out").read_text()
        stderr = (run.scratch / "growth-ui-run.err").read_text()
        receipt["growthFailureOutput"] = {"stdout": stdout, "stderr": stderr}
        if run.commands[-1]["exit"] != 1 or stdout or not stderr.startswith("Guest UI V1 validation:"):
            raise
        receipt["status"] = "guest_ui_v1_validation_refused"
        receipt["firstFailure"] = str(error)
    else:
        receipt["growthObservedStdout"] = stdout
        try:
            receipt["growthObservations"] = growth_observations(stdout)
        except ValueError as error:
            receipt["status"] = "growth_observation_mismatch"
            receipt["firstFailure"] = str(error)
        else:
            receipt["status"] = SUCCESS


def campaign(pinned, output, run, receipt, baseline, abi, identity, reviewed, checked_inputs):
    source_paths = ("vm", BASELINE, REVIEW, *(name for name in checked_inputs if not name.startswith(BASELINE + "/")))
    call = run.command
    call("all-source-before", "/usr/bin/git", "diff", "--exit-code", "HEAD", "--", *source_paths)
    require(not call("all-untracked-before", "/usr/bin/git", "ls-files", "--others", "--", *source_paths)[0],
            "unexpected input in pinned source")
    baseline.PIN = PIN
    control = {}
    baseline.campaign(run, control, pinned, output, identity, abi.check_descriptors)
    require(control["observations"] == reviewed["observations"], "1/1 control changed from review")
    require(control["outputs"]["guest.wasm"] == reviewed["outputs"]["guest.wasm"],
            "1/1 guest binary changed from review")
    require(control["descriptor"] == reviewed["descriptor"], "1/1 descriptor changed from review")
    receipt["onePageControl"] = {
        "review": REVIEW,
        "reviewIdentity": identity(pinned / REVIEW),
        "source": reviewed["inputs"],
        "module": control["outputs"]["guest.wasm"],
        "descriptor": control["descriptor"],
        "observations": control["observations"],
        "inertControls": control["controls"],
    }
    receipt["tools"] = control["tools"]
    receipt["dependencies"] = {
        **control["dependencies"],
        QUALIFICATION_SUPPORT: checked_inputs[QUALIFICATION_SUPPORT],
    }
    receipt["vmArchiveVerification"] = control["vmArchiveVerification"]

    work = run.scratch
    variant = work / "growth-sources"
    variant.mkdir()
    for name in VARIANT_SOURCES:
        shutil.copyfile(pinned / BASELINE / name, variant / name)
    call("growth-apply-source-diff", "/usr/bin/patch", "-s", "-F", "0", "-p1",
         "-d", variant, "-i", HERE / "allocator-growth.diff")
    receipt["growthSources"] = {name: identity(variant / name) for name in VARIANT_SOURCES}

    sdk = (Path.home() / ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_wasm.artifactbundle"
           / "swift-6.3.3-RELEASE_wasm/wasm32-unknown-wasip1/WASI.sdk")
    libc = sdk / "lib/wasm32-wasip1/libc.a"
    require(identity(libc)["sha256"] == baseline.LIBC_SHA, "growth libc differs from reviewed pin")
    obj, wasm, link_map = (work / name for name in ("growth.o", "growth.wasm", "growth.map"))
    call("growth-guest-compile", run.swift / "clang", "--target=wasm32-unknown-wasip1", f"--sysroot={sdk}",
         "-isystem", sdk / "include/wasm32-wasip1",
         "-std=c11", "-Oz", "-Wall", "-Wextra", "-Werror", "-fno-stack-protector",
         "-mno-bulk-memory", "-ffunction-sections", "-fdata-sections",
         "-c", variant / "guest.c", "-o", obj, bound=20)
    call("growth-guest-link", run.swift / "wasm-ld", "--no-entry", "--gc-sections", "--strip-all",
         "-z", "stack-size=16384", "--initial-memory=65536", f"--max-memory={MAXIMUM_PAGES * PAGE_BYTES}",
         *(f"--export={name}" for name in abi.SIGNATURES), obj, libc, f"--Map={link_map}", "-o", wasm, bound=20)
    raw = wasm.read_bytes()
    descriptor = abi.descriptors(raw)
    memories = abi.wasm(raw)["memories"]
    require(len(raw) <= abi.CAP and memories == [{"minimum": 1, "maximum": MAXIMUM_PAGES}],
            "growth fixture must declare exactly one memory with 1/2 limits")
    memory_exports = [row for row in descriptor["exports"] if row["kind"] != "function"]
    functions = {row["name"]: row["signature"] for row in descriptor["exports"] if row["kind"] == "function"}
    require(descriptor["imports"] == [] and descriptor["startFunction"] is None and
            memory_exports == [{"name": "memory", "kind": "memory", "index": 0}] and functions == abi.SIGNATURES,
            "growth fixture changed the import/export ABI")
    receipt["growthDescriptor"] = dict(descriptor, memories=memories)
    linked = [line.strip().replace(str(Path.home()), "$USER_HOME") for line in link_map.read_text().splitlines()
              if any(symbol in line for symbol in ("(posix_memalign)", "(free)", "(sbrk)"))]
    for symbol in ("libc.a(dlmalloc.o):(posix_memalign)", "libc.a(dlmalloc.o):(free)", "libc.a(sbrk.o):(sbrk)"):
        require(any(symbol in line for line in linked), f"growth allocator attribution missing {symbol}")
    receipt["growthLinkedAllocator"] = linked

    archive = work / "rust/release/libmixer_vm.a"
    host = work / "growth-host"
    call("growth-host-link", "/usr/bin/clang", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
         "-fmodules-cache-path=" + str(work / "clang-modules"), "-I", pinned / "vm/include",
         variant / "host.c", archive, "-o", host, bound=35)
    receipt["growthArtifacts"] = {file.name: identity(file) for file in (obj, wasm, link_map, host)}
    digest = call("growth-preinvoke-vm-sha256", "/usr/bin/shasum", "-a", "256", archive)[0].split()[0]
    baseline.verify_vm_archive(identity(archive), digest)
    receipt["growthPreinvokeVmSHA256"] = digest
    require(not os.path.lexists(output), f"output already exists: {output}")
    observe_growth(run, host, wasm, receipt)

    call("all-source-after", "/usr/bin/git", "diff", "--exit-code", "HEAD", "--", *source_paths)
    require(not call("all-untracked-after", "/usr/bin/git", "ls-files", "--others", "--", *source_paths)[0],
            "unexpected output in pinned source")



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    preflight = {"unknown": None, "commands": []}
    scratch = None
    owns_scratch = False
    file_ceiling = 128 * 1024**2
    try:
        scratch = new_path(args.scratch, "scratch")
        output = new_path(args.output, "output")
        pinned = args.checkout.resolve(strict=True)
        require(not output.is_relative_to(scratch), "output must be outside scratch")
        require(not scratch.is_relative_to(pinned) and not output.is_relative_to(pinned),
                "scratch and output must be outside the pinned checkout")
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_ceiling, file_ceiling))
        scratch.mkdir()
        owns_scratch = True
        checkout_pin(pinned, scratch, preflight)
        reviewed, checked_inputs, sources = verified_inputs(pinned)
        baseline, matched_task, replay_abi = load_helpers(pinned, sources)
        require(not os.path.lexists(output), f"output already exists: {output}")
        os.chdir(pinned)
        matched_task.SCRATCH_LIMIT = baseline.CEILING
        runner = matched_task.Run(scratch)
        runner.commands.extend(preflight["commands"])
    except (Exception, KeyboardInterrupt) as error:
        unknown = preflight["unknown"]
        print(json.dumps({"status": "preflight_refused", "firstFailure": str(error),
                          "unknown": unknown, "reapedWithGroupAbsent": len(preflight["commands"]),
                          "scratch": str(scratch) if unknown else None}), file=sys.stderr)
        if owns_scratch and unknown is None:
            shutil.rmtree(scratch)
        return 74 if unknown else 1
    identity = matched_task.identity
    receipt = {
        "scope": "L03/W07 §7.3 arm64 macOS host diagnostic through the installed Guest UI V1 C ABI",
        "observedUTC": datetime.now(timezone.utc).isoformat(),
        "source": PIN,
        "hostPolicy": {"vmProfile": "table-memory-v3", "initialPages": 1, "maximumPages": MAXIMUM_PAGES,
                       "fuelPerTurn": FUEL_LIMIT, "hostCallsPerTurn": 0, "turnCeilingMilliseconds": 50,
                       "operandStack": 4096, "callDepth": 64, "guestStackBytes": 16384},
        "allocation": {"sizeBytes": BLOCK_BYTES, "alignmentBytes": 64, "fillAttemptCeiling": BLOCK_LIMIT,
                       "canaryOffsets": [0, BLOCK_BYTES // 2, BLOCK_BYTES - 1], "release": "middle block"},
        "experimentInputs": {name: identity(HERE / name) for name in ("run.py", "allocator-growth.diff")},
    }
    try:
        campaign(pinned, output, runner, receipt, baseline, replay_abi, identity, reviewed, checked_inputs)
    except (Exception, KeyboardInterrupt) as error:
        if runner.active is not None or not runner.commands:
            print(json.dumps({"error": str(error), "scratch": str(scratch), "unknown": runner.active}),
                  file=sys.stderr)
            return 74
        receipt["status"] = "diagnostic_incomplete"
        receipt["firstFailure"] = str(error)

    substitutions = {
        str(HERE).replace(str(Path.home()), "$USER_HOME"): "$EXPERIMENT",
        str(pinned / BASELINE).replace(str(pinned), "$REPO"): "$BASELINE",
    }
    def show(argument):
        for old, new in substitutions.items():
            argument = argument.replace(old, new)
        return argument

    receipt["commands"] = [dict(command, argv=[show(arg) for arg in command["argv"]])
                           for command in runner.commands]
    receipt["custody"] = {
        "reapedWithGroupAbsent": len(runner.commands), "unknown": runner.active,
        "peakScratchBytes": runner.peak_scratch, "scratchByteCeiling": baseline.CEILING,
        "perFileByteCeiling": file_ceiling, "campaignDeadlineSeconds": 240,
        "scratchPolicy": "Remove only after the receipt is published and synced.",
    }
    try:
        baseline.publish_completed(receipt, output, scratch)
    except (OSError, ValueError, KeyboardInterrupt) as error:
        print(json.dumps({"status": "publication_incomplete", "firstFailure": str(error),
                          "scratch": str(scratch), "output": str(output)}), file=sys.stderr)
        return 1
    print(f"{receipt['status']}. Receipt: {output}")
    return int(receipt["status"] != SUCCESS)


if __name__ == "__main__":
    sys.exit(main())

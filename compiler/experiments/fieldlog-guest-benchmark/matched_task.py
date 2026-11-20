#!/usr/bin/env python3
"""Replay the D3 task differential and measure matched macOS host turns."""

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import statistics
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = "4bf1078d46ad80912151b789c27485ff41578d1e"
MODEL = HERE.parent / "fieldlog-installed-guest"
DESCRIPTOR_SOURCES = ("compiler/experiments/fieldlog-reactor/support.py",
                      "compiler/experiments/profile-budget/analyze.py", "compiler/qualification_support.py")
RUNTIME = ROOT / "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime"
RECEIPTS = ROOT / "verification/receipts"
PRIOR = RECEIPTS / "l03-d3-task-review-event-trap-7b61fe1c.json"
ANDROID = RECEIPTS / "l03-d3-task-completion-android-7b61fe1c.json"
HOST = RECEIPTS / "l03-d3-task-completion-host-benchmark-7b61fe1c.json"
SCRATCH_LIMIT = 3 * 1024**3
PAIRS = 5


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(path):
    return {"bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}


def spread(values):
    return {"count": len(values), "median": statistics.median(values),
            "min": min(values), "max": max(values)}


class Run:
    def __init__(self, scratch):
        self.scratch = scratch
        self.rust = Path.home() / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
        self.swift = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
        self.env = {
            "PATH": f"{self.rust}:/usr/bin:/bin:/usr/sbin:/sbin",
            "LANG": "C", "SWIFT_BACKTRACE": "enable=no",
            "HOME": str(scratch / "home"), "TMPDIR": str(scratch / "tmp"),
            "CARGO_HOME": str(scratch / "cargo"), "PYTHONDONTWRITEBYTECODE": "1",
        }
        for key in ("HOME", "TMPDIR", "CARGO_HOME"):
            Path(self.env[key]).mkdir()
        self.commands = []
        self.active = None
        self.peak_scratch = 0
        self.deadline = time.monotonic() + 240

    def check_space(self):
        size = 0
        for path in self.scratch.rglob("*"):
            try:
                if path.is_file():
                    size += path.stat().st_size
            except FileNotFoundError:
                continue  # Compiler temporaries can vanish during the scan.
        self.peak_scratch = max(self.peak_scratch, size)
        return size < SCRATCH_LIMIT

    def command(self, label, *args, bound=15, expected=0):
        argv = list(map(str, args))
        stdout = self.scratch / (label + ".out")
        stderr = self.scratch / (label + ".err")
        actions = [
            (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
            (os.POSIX_SPAWN_OPEN, 1, str(stdout), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
            (os.POSIX_SPAWN_OPEN, 2, str(stderr), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
        ]
        start = time.monotonic()
        end = min(start + bound, self.deadline)
        require(start < end, "campaign deadline expired")
        self.active = {"label": label, "pid": None}
        with (self.scratch / "active.json").open("w") as metadata:
            json.dump(self.active, metadata)
        pid = os.posix_spawn(argv[0], argv, self.env, setpgroup=0, file_actions=actions)
        self.active["pid"] = pid
        with (self.scratch / "active.json").open("w") as metadata:
            json.dump(self.active, metadata)
        stopped = None
        next_scan = start + 0.25
        while True:
            child, status, usage = os.wait4(pid, os.WNOHANG)
            if child:
                break
            now = time.monotonic()
            if stopped is None:
                if now >= end:
                    stopped = "deadline"
                elif now >= next_scan:
                    if not self.check_space():
                        stopped = "scratch limit"
                    next_scan = now + 0.25
                if stopped:
                    try:
                        os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    end = now + 3
            elif now >= end:
                raise TimeoutError(f"{label} could not be reaped")
            time.sleep(0.01)
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            self.active = None
        require(self.active is None, f"{label} group absence unproven")
        require(self.check_space(), "scratch exceeded 3 GiB")
        code = os.waitstatus_to_exitcode(status)
        shown = [arg.replace(str(self.scratch), "$RUN").replace(str(ROOT), "$REPO")
                 .replace(str(Path.home()), "$USER_HOME") for arg in argv]
        self.commands.append({"label": label, "argv": shown, "exit": code})
        detail = stderr.read_text(errors="replace")
        require(stopped is None and code == expected, f"{label} exit {code}, stop={stopped}\n{detail[-5000:]}")
        out = stdout.read_text()
        return out, detail, {
            "peakRSSBytes": usage.ru_maxrss,
            "processCPUNS": round((usage.ru_utime + usage.ru_stime) * 1e9),
        }


def campaign(run):
    call = run.command
    directory = run.scratch
    pin = call("head", "/usr/bin/git", "rev-parse", "HEAD")[0].strip()
    require(pin == PIN, "checkout must be at the exact public pin")
    tree = call("tree", "/usr/bin/git", "rev-parse", "HEAD^{tree}")[0].strip()
    inputs = ("vm/Cargo.lock", "vm/Cargo.toml", "vm/src", "vm/include",
              str(MODEL.relative_to(ROOT)), str(RUNTIME.relative_to(ROOT)), *DESCRIPTOR_SOURCES,
              str(PRIOR.relative_to(ROOT)), str(ANDROID.relative_to(ROOT)),
              str(HOST.relative_to(ROOT)))
    call("pin-before", "/usr/bin/git", "diff", "--exit-code", "--quiet", PIN, "--", *inputs)
    untracked = call("untracked-inputs", "/usr/bin/git", "ls-files", "--others", "--", *inputs)[0]
    require(not untracked, "unexpected untracked file in pinned source")
    # Verify after compilation as well. Restrict the module, toolchain and workspace to this run.
    prior = json.loads(PRIOR.read_text())
    android = json.loads(ANDROID.read_text())
    model = MODEL / "TaskCompletion.swift"
    model_sha = sha(model.read_bytes())
    require(model_sha == prior["inputsSHA256"]["TaskCompletion.swift"] == android["taskSource"]["sha256"],
            "task source differs from D3")
    versions = {label: call(label, executable, *args)[0].strip() for label, executable, args in [
        ("macOS", "/usr/bin/sw_vers", ()),
        ("hardware", "/usr/sbin/sysctl", ("-n", "hw.model")),
        ("swiftNative", "/usr/bin/swiftc", ("--version",)),
        ("swiftGuest", run.swift / "swiftc", ("--version",)),
        ("wasmLD", run.swift / "wasm-ld", ("--version",)),
        ("objcopy", run.swift / "llvm-objcopy", ("--version",)),
        ("rustc", run.rust / "rustc", ("--version",)),
        ("cargo", run.rust / "cargo", ("--version",)),
    ]}
    adapter = (MODEL / "InstalledGuest.swift").read_text()
    needle = "count: documentCapacity)"
    require(adapter.count(needle) == 1, "unexpected pinned adapter shape")
    fixture = directory / "InstalledGuest.swift"
    fixture.write_text(adapter.replace(needle, "count: task.revision == 5 ? 0 : documentCapacity)"))
    obj, linked, wasm = [directory / name for name in ("task.o", "task-linked.wasm", "task.wasm")]
    exports = ["mixer_guest_ui_start_v1", "mixer_guest_ui_event_v1", "mixer_guest_capability_ready_v1"]
    call("guest-build", run.swift / "swiftc", "-target", "wasm32-unknown-none-wasm",
         "-enable-experimental-feature", "Embedded", "-whole-module-optimization", "-Osize",
         "-parse-as-library", "-gline-tables-only", "-debug-prefix-map", f"{ROOT}=.",
         "-debug-prefix-map", f"{directory}=./fixture", "-debug-prefix-map", f"{Path.home()}=/toolchain",
         "-module-cache-path", directory / "modules-guest", "-Xfrontend", "-disable-stack-protector",
         "-D", "REQUIRE_REVIEW", "-emit-object", model, fixture, "-o", obj, bound=35)
    call("guest-link", run.swift / "wasm-ld", "--no-entry", "--gc-sections", "-z", "stack-size=16384",
         "--max-memory=65536", *[f"--export={name}" for name in exports], obj, "-o", linked)
    call("guest-debug-lines", run.swift / "llvm-objcopy", "--wildcard", "--remove-section=.debug_*",
         "--keep-section=.debug_line", "--remove-section=name", "--remove-section=producers", linked, wasm)
    raw = wasm.read_bytes()
    from replay_abi import check_descriptors, negative_controls
    descriptor = check_descriptors(raw)
    rejected = sorted(negative_controls(raw, descriptor))
    target = directory / "rust"
    call("vm-build", run.rust / "cargo", "build", "--offline", "--locked", "--release", "--lib", "--jobs", "1",
         "--features", "experimental-capability-native", "--manifest-path", ROOT / "vm/Cargo.toml",
         "--target-dir", target, bound=100)
    archive = target / "release/libmixer_vm.a"
    modulemap = directory / "module.modulemap"
    include = ROOT / "vm/include"
    modulemap.write_text(f'module CMixerVMCapability {{ header "{include}/mixer_vm_guest_ui.h" export * }}\n')
    sources = [model, HERE / "MatchedTask.swift", *[RUNTIME / f"{name}.swift"
               for name in ("Types", "Failure", "GuestDebugLines")]]
    compiler = ["/usr/bin/swiftc", "-j", "1", "-swift-version", "6", "-parse-as-library",
                "-module-cache-path", directory / "modules-native", "-I", directory]
    binary, debug = directory / "matched", directory / "matched-debug"
    call("host-build", *compiler, "-O", "-whole-module-optimization", *sources, archive, "-o", binary, bound=35)
    call("host-debug-build", *compiler, "-Onone", "-g", *sources, archive, "-o", debug, bound=35)

    expected = [frame["sha256"] for frame in prior["frames"]]

    def sample(label, mode):
        out, _, usage = call(label, binary, mode, wasm, bound=6)
        row = json.loads(out)
        frames = [base64.b64decode(frame, validate=True) for frame in row.pop("frames")]
        require([sha(frame) for frame in frames] == expected, f"{label}: wrong document bytes")
        require(len(row["turnNS"]) == 3 and min(row["turnNS"]) > 0, f"{label}: missing time samples")
        require(usage["peakRSSBytes"] > 0 and row["closed"] == mode.startswith("guest"),
                f"{label}: missing RSS or close")
        return frames, {**row, **usage}

    native, native_control = sample("native-control", "native-control")
    guest, guest_control = sample("guest-control", "guest-control")
    require(native == guest and native_control["refusals"] == guest_control["refusals"] == 2,
            "differential or refusal failed")
    _, native_error, _ = call("native-fault", debug, "native-fault", wasm, bound=6, expected=-signal.SIGTRAP)
    require("TaskCompletion.swift:94: Precondition failed" in native_error, "missing native source diagnostic")
    require(guest_control.get("diagnostic"), "missing guest source diagnostic")

    load_before = os.getloadavg()
    samples = {"native": [], "guest": []}
    order = []
    for index in range(PAIRS):
        sequence = ("native", "guest") if index % 2 == 0 else ("guest", "native")
        frames = {}
        for mode in sequence:
            frames[mode], row = sample(f"pair-{index + 1}-{mode}", mode)
            require(row["refusals"] == 0, "unexpected sample refusal")
            samples[mode].append(row)
        require(frames["native"] == frames["guest"] == native, "pair frame bytes differ")
        order.extend(sequence)
    load_after = os.getloadavg()
    profile_frames, profile = sample("guest-components", "guest-profile")
    require(profile_frames == native and len(profile["componentNS"]) == 3, "component replay differed")
    require(all(0 < write + invoke <= turn for (write, invoke), turn
                in zip(profile["componentNS"], profile["turnNS"])), "component clocks inconsistent")
    call("pin-after", "/usr/bin/git", "diff", "--exit-code", "--quiet", PIN, "--", *inputs)

    return {
        "gate": "L03", "milestone": "D3", "status": "passed_scoped_macos_matched_host_measurement",
        "observedUTC": datetime.now(timezone.utc).isoformat(), "publicRevision": pin, "publicTree": tree,
        "scope": "Host-only D3 review/confirm/reopen. Historical host drivers were untracked. This replay uses the pinned public TaskCompletion, compact guest adapter and owned VM C ABI. No new iOS, Android, signed activation, UI, product latency, target-budget or gate verdict.",
        "references": {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in (PRIOR, ANDROID, HOST)},
        "replay": f"python3 -B {Path(__file__).relative_to(ROOT)}",
        "sourceSHA256": {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in
                         [*sources, Path(__file__), MODEL / "InstalledGuest.swift"]},
        "versions": {**versions, "logicalCPUs": os.cpu_count(), "architecture": os.uname().machine},
        "artifact": {"kind": "raw unsigned Wasm with linked .debug_line", **identity(wasm),
                     "adapter": identity(fixture), "vmArchive": identity(archive),
                     "signedUpdatePayloadBytes": None},
        "differential": {
            "frames": [{**frame, "bytes": len(data)} for frame, data in zip(prior["frames"], native)],
            "exactBytesPerPair": True, "staleAndTrailingLFRefusedWithoutFrameChangePerPath": 2,
            "nativeDiagnostic": "TaskCompletion.swift:94: Precondition failed (SIGTRAP)",
            "guestDiagnostic": guest_control["diagnostic"], "guestStatus": 2,
            "guestOperation": "invocation", "everyGuestOwnerClosedAndStaleHandleRefused": True,
            "descriptorRefusals": rejected, "nativeValidatorUsed": True,
            "fuelPerTurn": 1_000_000, "memoryPages": 1, "hostCalls": 0,
            "fourthActivation": "Separate control only. At revision 5 the one fixture-only adapter substitution and native harness pass zero output capacity to the unchanged renderer. No fifth frame was emitted.",
        },
        "benchmark": {
            "order": order, "loadBefore": load_before, "loadAfter": load_after,
            "timer": "DispatchTime elapsed ns for each prepared canonical event through materialized frame. Swift includes acceptance, state transition and rendering. Guest includes C ABI write/invoke, report and control-header checks, and frame copy. Excludes startup, initial frame, event construction, close, JSON, comparison, refusal and trap controls.",
            "memory": "Whole-process peak resident bytes via Darwin wait4 ru_maxrss. Includes startup and VM validation/construction on the guest path.",
            "design": "Five fresh interleaved matched pairs, alternating pair order, three successful turns per process. All four frames checked in each process. Optimized native Swift and release VM, Embedded guest built -Osize. Descriptive only. A separation smaller than run-to-run spread would be treated as unresolved.",
            "guestComponentReplay": {
                "meaning": "Separate replay with extra timestamps after write verification and before invoke verification. Invoke includes export and argument preparation plus synchronous owning VM C call. Remainder includes report checks and frame reads. Whole-process CPU is available with each sample; no instruction-level profile.",
                "writeInvokeNS": profile["componentNS"], "turnNS": profile["turnNS"],
                "fuel": profile["fuel"],
            },
            "paths": {mode: {
                "processes": len(rows), "timedTurns": sum(len(row["turnNS"]) for row in rows),
                "errors": 0, "framesChecked": len(rows) * 4,
                "matchedSequenceNS": spread([sum(row["turnNS"]) for row in rows]),
                "byTransitionNS": [spread([row["turnNS"][i] for row in rows]) for i in range(3)],
                "peakRSSBytes": spread([row["peakRSSBytes"] for row in rows]),
                "samples": [{"turnNS": row["turnNS"], "peakRSSBytes": row["peakRSSBytes"],
                             "processCPUNS": row["processCPUNS"], **({"fuel": row["fuel"]} if row["fuel"] else {})}
                            for row in rows],
            } for mode, rows in samples.items()},
        },
        "buildCommands": [row for row in run.commands if row["label"] in
                          {"guest-build", "guest-link", "guest-debug-lines", "vm-build", "host-build",
                           "host-debug-build", "native-fault", "guest-control", "pair-1-native", "pair-1-guest"}],
    }


def main():
    require(os.uname().sysname == "Darwin" and os.uname().machine == "arm64", "requires macOS arm64")
    require(Path.cwd() == ROOT, "run from Mixer checkout root")
    sys.path[:0] = [str(MODEL), str(HERE.parent / "fieldlog-reactor")]
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    local = ROOT / "verification/local"
    local.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="l03-taskcompletion-pair-", dir=local))
    run = Run(scratch)
    try:
        result = campaign(run)
    finally:
        if run.active is None:
            shutil.rmtree(scratch)
        else:
            raise RuntimeError(f"UNKNOWN custody for {run.active}; preserve {scratch}")
    result["custody"] = {
        "directReapedAndGroupsObservedAbsent": len(run.commands), "unknown": 0,
        "observedPeakScratchBytes": run.peak_scratch, "scratchLimitBytes": SCRATCH_LIMIT,
        "scratchRemoved": not scratch.exists(),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

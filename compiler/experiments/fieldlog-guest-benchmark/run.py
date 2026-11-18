#!/usr/bin/env python3
"""Measure the first accepted pair of compact FieldLog ABI2 guests on macOS."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINAL = HERE.parent / "fieldlog-installed-guest"
ACCEPTED = ROOT / "verification/receipts/fieldlog-compact-abi2-41a05264.json"
BRIDGE_INPUTS = ("vm/", "sdk/", "experimental-capability-runtime/")
NAMES = ("baseline", "reviewed")
EVENTS = 12
ROUNDS = 5
BOUNDARIES = {
    "launch": "In-process monotonic time from immediately before installed validation of in-memory module bytes to first reconciled document accepted by the exchange. Includes construction, startup and effects admission.",
    "input": "In-process monotonic time from just before the first offer of a reconciled button activation through accepted reconciliation of the next document. Includes busy admission retries and bridge delivery wake; no polling interval.",
    "memory": "Whole fresh host process RSS in bytes via mach_task_basic_info at four boundaries; Darwin getrusage self maximum RSS in bytes through after-drain checkpoint. Includes Swift and VM; no RSS attribution to the guest.",
    "payload": "Raw Wasm and deterministic gzip level 9, zero mtime, measured from the first accepted files. No envelope, signing, manifest, assets, transport or delta packaging.",
    "timerDiagnostic": "Timer ticks come from the bridge's native worker status sampled just outside each timed input interval. The existing Guest UI V1 worker arms a repeating 10 ms pump; the benchmark leaves that setting stock.",
    "excludedFromTiming": "Executable startup, reading Wasm from disk, native window/pixels, differential checks, RSS sampling and retirement.",
    "workload": "One guest/session in each fresh macOS host process, one fixed inspection task and 12 serial button activations. Baseline runs six complete/reopen cycles. Reviewed runs four review/confirm/reopen cycles. Five alternating paired rounds, no discarded warm-up samples.",
}
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "compiler"))
from qualification_support import clean_environment, digest, strict_json


def expect_identity(path, record):
    if path.stat().st_size != record["bytes"] or digest(path) != record["sha256"]:
        raise ValueError(f"Accepted artifact differs: {path}")


def identity(path):
    return {"bytes": path.stat().st_size, "sha256": digest(path)}


def serialized(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def distribution(values):
    ordered = sorted(values)
    return dict(count=len(ordered), min=ordered[0], median=statistics.median(ordered),
                p95=ordered[math.ceil(0.95 * len(ordered)) - 1], max=ordered[-1])


def metrics(rows):
    return {
        "launchNS": distribution([row["launchNS"] for row in rows]),
        "inputNS": distribution([value for row in rows for value in row["inputNS"]]),
        "perProcessInputMedianNS": distribution([statistics.median(row["inputNS"]) for row in rows]),
        "peakRSSBytes": distribution([row["peakRSSBytes"] for row in rows]),
        "rssBytes": {phase: distribution([row["rssBytes"][phase] for row in rows])
                     for phase in rows[0]["rssBytes"]},
        "processCPUMicroseconds": distribution([row["processCPUMicroseconds"] for row in rows]),
        "intervalsWithBridgeTimerTick": sum(value > 0 for row in rows for value in row["inputTimerTicks"]),
        "maxVMBatchNS": max(row["maximumBatchNS"] for row in rows),
        "maxDocumentBytes": max(row["maxDocumentBytes"] for row in rows),
        "maxEventBytes": max(row["maxEventBytes"] for row in rows),
        "acceptedEvents": sum(row["acceptedEvents"] for row in rows),
        "deliveredEvents": sum(row["deliveredEvents"] for row in rows),
        "producedFrames": sum(row["producedFrames"] for row in rows),
        "retiredSessions": sum(row["retired"] for row in rows),
    }


class Commands:
    def __init__(self, out):
        self.out = out
        self.logs = out / "logs"
        self.logs.mkdir()
        tmp = out / "tmp"
        tmp.mkdir()
        self.env = clean_environment()
        self.env["TMPDIR"] = str(tmp)
        self.rows = []

    def run(self, label, *argv, timeout=15):
        argv = list(map(str, argv))
        row = {"command": argv, "timeoutSeconds": timeout}
        self.rows.append(row)
        launch = self.logs / (label + ".json")
        stdout, stderr = (self.logs / (label + "." + suffix) for suffix in ("stdout", "stderr"))
        launch.write_bytes(serialized(row))
        started = time.monotonic()
        with stdout.open("xb") as out, stderr.open("xb") as err:
            process = subprocess.Popen(argv, cwd=ROOT, env=self.env, stdout=out, stderr=err,
                                       start_new_session=True)
            row.update(pid=process.pid, pgid=process.pid, groupGone=False)
            try:
                launch.write_bytes(serialized(row))
                while process.poll() is None:
                    if time.monotonic() - started > timeout or max(
                            os.fstat(out.fileno()).st_size, os.fstat(err.fileno()).st_size) > 4 * 1024 * 1024:
                        raise RuntimeError(f"{label} hit its command or output bound")
                    time.sleep(0.02)
            finally:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=3)
                row["exitCode"] = process.returncode
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    row["groupGone"] = True
                finally:
                    row["elapsedSeconds"] = round(time.monotonic() - started, 6)
                    launch.write_bytes(serialized(row))
        if not row["groupGone"]:
            raise RuntimeError(f"UNKNOWN process group custody for {label}, preserve {self.out}")
        row["stdout"], row["stderr"] = identity(stdout), identity(stderr)
        if row["exitCode"] != 0 or max(row["stdout"]["bytes"], row["stderr"]["bytes"]) > 4 * 1024 * 1024:
            raise RuntimeError(f"{label} failed, see {stderr}")
        return stdout.read_text().strip()


def verify_work(row, name, *, timed):
    if (row["fixture"], row["acceptedEvents"], row["deliveredEvents"], row["producedFrames"],
            row["retired"]) != (name, EVENTS, EVENTS, EVENTS + 1, True):
        raise ValueError(f"Incomplete work for {name}")
    if timed:
        if (len(row["inputNS"]) != EVENTS or len(row["inputTimerTicks"]) != EVENTS
                or min(row["inputNS"]) <= 0 or row["launchNS"] <= 0):
            raise ValueError(f"Incomplete timings for {name}")
        if row["rssBytes"].keys() != {"beforeValidation", "firstDocument", "lastDocument", "afterDrain"}:
            raise ValueError(f"Incomplete RSS snapshots for {name}")
        if min(row["rssBytes"].values()) <= 0 or row["peakRSSBytes"] <= 0:
            raise ValueError(f"Invalid RSS for {name}")
    elif (row["nativeMalformed"], row["staleRefusals"], len(row["workspaceOutbox"])) != (EVENTS * 6, EVENTS, EVENTS + 1):
        raise ValueError(f"Incomplete differential checks for {name}")


def campaign(out, commands, result):
    run = commands.run
    admitted = strict_json(ACCEPTED.read_text())
    retained = ROOT / admitted["details"]["path"]
    expect_identity(retained, admitted["details"])
    build = strict_json(retained.read_text())
    inputs = {path: sha for path, sha in build["mixerInputs"].items() if path.startswith(BRIDGE_INPUTS)}
    input_paths = run("bridge-inputs", "/usr/bin/git", "ls-files", "--cached", "--others",
                      "--exclude-standard", "-z", "--", "vm/src", "vm/include", "vm/Cargo.toml", "vm/Cargo.lock",
                      "sdk/Sources", "sdk/Package.swift", "sdk/Package.resolved",
                      "experimental-capability-runtime/Sources", "experimental-capability-runtime/Package.swift")
    if set(filter(None, input_paths.split("\0"))) != inputs.keys() or any(
            digest(ROOT / path) != sha for path, sha in inputs.items()):
        raise ValueError("Canonical bridge inputs differ from the accepted archive's source")

    src = out / "host/src"
    src.mkdir(parents=True)
    proofs = retained.parent
    library = proofs / "rust/release/libmixer_vm.a"
    workspace = proofs / "host/src/Workspace.swift"
    if digest(library) != build["vmArchiveSHA256"] or digest(workspace) != admitted["workspaceSHA256"]:
        raise ValueError("Accepted VM archive or pinned Workspace differs")
    sources = [ORIGINAL / name for name in ("TaskCompletion.swift", "ProbePackage.swift.in")]
    for path in sources:
        if digest(path) != build["mixerInputs"][str(path.relative_to(ROOT))]:
            raise ValueError(f"Accepted host model source changed: {path}")
    shutil.copyfile(workspace, src / "Workspace.swift")
    shutil.copyfile(sources[0], src / "TaskCompletion.swift")
    shutil.copyfile(sources[1], out / "host/Package.swift")
    shutil.copyfile(HERE / "Benchmark.swift", src / "Benchmark.swift")
    shutil.copyfile(ROOT / "sdk/Package.resolved", out / "host/Package.resolved")
    lib = out / "lib"
    lib.mkdir()
    archive = lib / "libmixer_vm_capability_experimental.a"
    shutil.copyfile(library, archive)
    if digest(archive) != build["vmArchiveSHA256"]:
        raise ValueError("VM copy differs")

    files = {}
    payloads = {}
    payload_dir = out / "payloads"
    payload_dir.mkdir()
    for name, record in {**admitted["modules"], "fullSDK": admitted["fullSDKControl"]}.items():
        source = ROOT / record["path"]
        expect_identity(source, record)
        files[name] = payload_dir / source.name
        shutil.copyfile(source, files[name])
        expect_identity(files[name], record)
        payloads[name] = {**identity(files[name]), "originalPath": record["path"],
                          "gzipBytes": len(gzip.compress(files[name].read_bytes(), compresslevel=9, mtime=0))}
    result["payloads"] = payloads

    scratch = out / "swiftpm"
    scratch.mkdir()
    for directory in ("repositories", "checkouts"):
        shutil.copytree(proofs / "swiftpm" / directory, scratch / directory, symlinks=True)
    shutil.copyfile(proofs / "swiftpm/workspace-state.json", scratch / "workspace-state.json")

    source_inputs = {str(path.relative_to(ROOT)): digest(path)
                     for path in [Path(__file__), HERE / "Benchmark.swift",
                                  ROOT / "compiler/qualification_support.py", *sources]}
    result["inputs"] = {
        "mixerRevision": run("revision", "/usr/bin/git", "rev-parse", "HEAD"),
        "acceptedRevision": admitted["mixerRevision"],
        "bridgeInputSHA256": hashlib.sha256(serialized(inputs)).hexdigest(),
        "benchmarkSources": source_inputs,
        "vmArchiveSHA256": build["vmArchiveSHA256"],
        "fieldlogRevision": admitted["fieldlogRevision"],
        "workspaceSHA256": admitted["workspaceSHA256"],
    }
    (out / "bridge-inputs.json").write_bytes(serialized(inputs))
    result["tools"] = {
        "hostSwift": run("swift-version", "/usr/bin/swift", "--version"),
        "rustArchiveCompiler": admitted["tools"]["rust"],
        "guestCompiler": admitted["tools"]["guestSwift"],
        "linker": admitted["tools"]["linker"],
        "python": sys.version.splitlines()[0],
        "macOS": run("host-version", "/usr/bin/sw_vers"),
        "architecture": platform.machine(),
        "logicalCPUs": os.cpu_count(),
        "hardwareModel": run("hardware", "/usr/sbin/sysctl", "-n", "hw.model"),
        "physicalRAMBytes": int(run("ram", "/usr/sbin/sysctl", "-n", "hw.memsize")),
    }
    flags = ["--package-path", out / "host", "--scratch-path", scratch,
             "--cache-path", out / "cache", "--config-path", out / "config", "--security-path", out / "security",
             "-c", "release", "--disable-prefetching", "--skip-update", "--force-resolved-versions"]
    run("build", "/usr/bin/swift", "build", *flags, "-Xcc", "-I", "-Xcc", ROOT / "vm/include",
        "-Xlinker", "-L", "-Xlinker", lib, timeout=180)
    binary = Path(run("bin-path", "/usr/bin/swift", "build", *flags, "--show-bin-path")) / "Probe"
    result["hostBinary"] = identity(binary)
    result["differential"] = {}
    for name in NAMES:
        row = strict_json(run(f"differential-{name}", binary, "differential", name, files[name]))
        verify_work(row, name, timed=False)
        result["differential"][name] = row
    result["guards"] = {name: strict_json(run(f"guards-{name}", binary, "guards", files[name], files["fullSDK"]))
                        for name in NAMES}

    rows = {name: [] for name in NAMES}
    result["loadBefore"] = os.getloadavg()
    for index in range(ROUNDS):
        for name in NAMES:
            row = strict_json(run(f"sample-{index + 1}-{name}", binary, "timed", name, files[name]))
            verify_work(row, name, timed=True)
            if row["statuses"] != result["differential"][name]["statuses"]:
                raise ValueError(f"Timed policy differs from differential for {name}")
            rows[name].append(row)
    result["loadAfter"] = os.getloadavg()
    result["metrics"] = {name: metrics(rows[name]) for name in NAMES}
    if any(digest(ROOT / path) != sha for path, sha in (inputs | source_inputs).items()):
        raise ValueError("Source inputs changed during the benchmark")
    result["processGroupsClosed"] = sum(row.get("groupGone") is True for row in commands.rows)
    result["sampleOrder"] = list(NAMES) * ROUNDS
    (out / "samples.json").write_bytes(serialized(rows))
    result["samples"] = identity(out / "samples.json")
    result["errors"] = 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Unused directory component under verification/local")
    parser.add_argument("--compact", action="store_true", help="Write a compact receipt for this name")
    args = parser.parse_args()
    if not re.fullmatch(r"fieldlog-guest-benchmark-[a-zA-Z0-9][a-zA-Z0-9._-]{0,40}", args.name):
        parser.error("use a fresh fieldlog-guest-benchmark-NAME component")
    if platform.system() != "Darwin":
        parser.error("this host benchmark requires macOS")
    out = ROOT / "verification/local" / args.name
    compact = ROOT / "verification/receipts" / (args.name + ".json")
    if args.compact and compact.exists():
        parser.error("compact receipt already exists")
    out.mkdir(exist_ok=False)
    commands = Commands(out)
    result = {"schema": 1, "id": args.name, "status": "FAIL", "gate": "L03",
              "boundaries": BOUNDARIES, "observedUTC": datetime.now(timezone.utc).isoformat(),
              "acceptedReceipt": str(ACCEPTED.relative_to(ROOT)),
              "localGatesPassed": [], "gaGatesPassed": []}
    try:
        campaign(out, commands, result)
        result["status"] = "PASS_LOCAL_COMPACT_FIELDLOG_BENCHMARK"
    except Exception as error:
        result["errors"] = 1
        result["failure"] = str(error)
        if any(row.get("groupGone") is False for row in commands.rows):
            result["status"] = "HOLD_UNKNOWN_PROCESS_CUSTODY"
        raise
    finally:
        detail = out / "result.json"
        detail.write_text(json.dumps({**result, "commands": commands.rows}, indent=2) + "\n")
        if args.compact:
            result["details"] = {"path": str(detail.relative_to(ROOT)), **identity(detail)}
            result["replay"] = "python3 -B compiler/experiments/fieldlog-guest-benchmark/run.py fieldlog-guest-benchmark-FRESH"
            with compact.open("x") as stream:
                stream.write(json.dumps(result, indent=2) + "\n")
    print(detail.relative_to(ROOT))


if __name__ == "__main__":
    main()

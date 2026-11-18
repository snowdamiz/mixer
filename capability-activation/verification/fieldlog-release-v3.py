#!/usr/bin/env python3
"""Run the exact compact FieldLog guests through the localhost v3 service and macOS owner."""
import argparse
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "compiler"))
from qualification_support import CommandRecorder, clean_environment, digest, strict_json

PIN = ROOT / "verification/receipts/fieldlog-compact-abi2-41a05264.json"
INPUT_ROOT = ROOT / "verification/local/fieldlog-installed-guest-proof-41a05264"
SOURCE_ROOTS = (
    "capability-activation", "experimental-capability-runtime", "runtime-identity", "sdk", "updates", "services", "vm",
    "compiler/qualification_support.py",
)
HOST_TOOLS = {
    "capability-activation/verification/fieldlog-release-v3.py",
    "capability-activation/verification/fieldlog-press.swift",
}

EXPECTED_AX = {
    "ax-baseline-complete": "Complete task",
    "ax-reviewed-complete": "Complete task",
    "ax-reviewed-confirm": "Confirm completion",
    "ax-rollback-complete": "Complete task",
    "ax-offline-complete": "Complete task",
}
DENIAL_CONTROL = "FIELDLOG custody control real group absence observed before injected EPERM"


def closed(child, code):
    return (child.get("state") == "CLOSED" and child.get("directChildReaped") is True
            and child.get("ownedGroupAbsent") is True and child.get("exitCode") == code)


def read_children(directory):
    children = {}
    for path in sorted(directory.glob("*.json")):
        try:
            child = strict_json(path.read_text())
            if not isinstance(child, dict):
                raise ValueError("expected a child custody object")
        except (OSError, ValueError) as error:
            child = {"state": "UNREADABLE", "error": str(error), "path": str(path)}
        children[path.stem] = child
    return children


def has_identity(child):
    return (type(child.get("pid")) is int and child["pid"] > 1 and child.get("pgid") == child["pid"]
            and type(child.get("parentPID")) is int and child["parentPID"] > 1
            and child["parentPID"] != child["pid"])


def simulated_denial(child, observations):
    return (has_identity(child) and child.get("state") == "HOLD"
            and child.get("directChildReaped") is True and child.get("ownedGroupAbsent") is False
            and child.get("exitCode") == 0 and "injected group observation EPERM" in child.get("error", "")
            and DENIAL_CONTROL in observations)


def collect_custody(out, receipt, host):
    children = read_children(out / "custody")
    controls = read_children(out / "custody-control")
    observations = []
    for stream in ("stdout", "stderr"):
        path = out / "logs" / f"host-proof.{stream}"
        if path.is_file():
            observations.extend(line for line in path.read_text(errors="replace").splitlines()
                                if line.startswith("FIELDLOG "))
    receipt.update(children=children, custodyControls=controls, observations=observations)
    unresolved = {}
    for directory, records, expected in (
        ("custody", children, {"service", *EXPECTED_AX}),
        ("custody-control", controls, {"nonzero", "probe-denied"}),
    ):
        for name, child in records.items():
            if child.get("state") == "NOT_LAUNCHED":
                continue
            if (child.get("state") == "CLOSED" and child.get("directChildReaped") is True
                    and child.get("ownedGroupAbsent") is True and has_identity(child)):
                continue
            if directory == "custody-control" and name == "probe-denied" and simulated_denial(child, observations):
                continue
            unresolved[f"{directory}/{name}"] = child
        if host["exitCode"] == 0:
            for name in expected - records.keys():
                unresolved[f"{directory}/{name}"] = {"state": "MISSING"}
    if (unresolved or host["exitCode"] not in {0, 1} or host["timedOut"] or host["outputLimitExceeded"]
            or any(line.startswith("FIELDLOG HOLD ") for line in observations)):
        receipt["status"] = "HOLD"
        receipt["custodyHold"] = {
            "directory": str(out),
            "children": unresolved,
            "reason": "Preserve this run. Signed-pair child closure was not established.",
        }
        (out / "HOLD.json").write_text(json.dumps(receipt["custodyHold"], indent=2) + "\n")


def verify_custody(out, children, controls, observations):
    expected = {"service": out / "mixer-service", **{name: out / "fieldlog-press" for name in EXPECTED_AX}}
    if children.keys() != expected.keys() or controls.keys() != {"nonzero", "probe-denied"}:
        raise RuntimeError("Signed-pair custody records are incomplete")
    for name, executable in expected.items():
        child = children[name]
        if not closed(child, 0) or child["executable"] != str(executable):
            raise RuntimeError(f"Signed-pair child {name} did not close successfully")
        if name in EXPECTED_AX:
            log = (out / "custody" / (name + ".log")).read_text()
            if f"FIELDLOG native AX press {EXPECTED_AX[name]}" not in log.splitlines():
                raise RuntimeError(f"AX action evidence missing for {name}")
    all_children = [*children.values(), *controls.values()]
    if not all(has_identity(child) for child in all_children):
        raise RuntimeError("Child launch identity missing or invalid")
    if not closed(controls["nonzero"], 1) or not simulated_denial(controls["probe-denied"], observations):
        raise RuntimeError("Child failure controls did not observe the required custody outcomes")


def snapshot_sources(read, destination):
    paths = read("source-files", shutil.which("git"), "ls-files", "-z", "--cached",
                 "--others", "--exclude-standard", "--", *SOURCE_ROOTS).rstrip("\0").split("\0")
    sources = {}
    for name in sorted(set(paths)):
        if name.startswith("capability-activation/verification/") and name not in HOST_TOOLS:
            continue
        if not (ROOT / name).is_file():
            continue
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
        sources[name] = digest(target)
    return sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Unused directory name under verification/local")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", args.name):
        parser.error("name must be a single bounded path component")
    if sys.platform != "darwin":
        parser.error("a graphical macOS session is required")

    os.umask(0o077)
    out = ROOT / "verification/local" / args.name
    out.mkdir(mode=0o700)
    for child in ("logs", "lib", "tmp", "custody", "custody-control"):
        (out / child).mkdir()
    environment = clean_environment()
    environment.update(TMPDIR=str(out / "tmp"), GOCACHE=str(out / "go-cache"))
    commands = []
    recorder = CommandRecorder(out / "logs", commands, ROOT)
    receipt = {"status": "FAILED", "predecessor": str(PIN.relative_to(ROOT)), "commands": commands}

    def run(name, *command, timeout=90):
        return recorder.run(name, command, env=environment, timeout=timeout)

    try:
        source = out / "source"
        pin = strict_json(PIN.read_text())
        for module in pin["modules"].values():
            path = source / module["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / module["path"], path)
            if path.stat().st_size != module["bytes"] or digest(path) != module["sha256"]:
                raise ValueError(f"Payload disagrees with compact receipt: {path}")
        prior = ROOT / pin["details"]["path"]
        if digest(prior) != pin["details"]["sha256"]:
            raise ValueError("Compact guest detailed receipt digest did not match")
        vm = INPUT_ROOT / "rust/release/libmixer_vm.a"
        vm_digest = digest(vm)
        if vm_digest != strict_json(prior.read_text())["vmArchiveSHA256"]:
            raise ValueError("Owned bridge archive differs from compact Swift probe")
        library = out / "lib/libmixer_vm_capability_experimental.a"
        shutil.copyfile(vm, library)
        if digest(library) != vm_digest:
            raise ValueError("Copied VM archive differs")

        receipt["pinnedModules"] = pin["modules"]
        receipt["archiveSHA256"] = vm_digest
        receipt["mixerRevision"] = run("revision", shutil.which("git"), "rev-parse", "HEAD").strip()
        sources = snapshot_sources(run, source)
        encoded_sources = json.dumps(sources, sort_keys=True).encode()
        (out / "source-inputs.json").write_bytes(encoded_sources)
        receipt["mixerSourceDigest"] = hashlib.sha256(encoded_sources).hexdigest()

        swift = shutil.which("swift")
        go = shutil.which("go")
        receipt["tools"] = {
            "swift": run("swift-version", swift, "--version").strip(),
            "go": run("go-version", go, "version").strip(),
            "macOS": run("macos-version", "/usr/bin/sw_vers").strip(),
        }
        run("service-build", go, "-C", source / "services", "build", "-mod=readonly", "-o",
            out / "mixer-service", "./cmd/mixer-service")
        swift_arguments = (
            "--package-path", source / "capability-activation", "--scratch-path", out / "swiftpm",
            "--disable-prefetching", "--skip-update", "--force-resolved-versions",
            "-Xcc", "-I", "-Xcc", source / "vm/include", "-Xlinker", "-L", "-Xlinker", out / "lib",
        )
        run("host-build", swift, "build", "--build-tests", *swift_arguments)
        run("accessibility-build", shutil.which("swiftc"), source / "capability-activation/verification/fieldlog-press.swift",
            "-o", out / "fieldlog-press")
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        environment.update(MIXER_FIELDLOG_V3_REPOSITORY=str(source), MIXER_FIELDLOG_V3_RUN=str(out),
                           MIXER_FIELDLOG_V3_ARCHIVE_SHA256=vm_digest, MIXER_FIELDLOG_V3_PORT=str(port))
        receipt["loopbackPort"] = port
        try:
            run("host-proof", swift, "test", "--skip-build", *swift_arguments,
                "--filter", "FieldLogReleaseV3Tests",
                timeout=60)
        finally:
            host = next((command for command in commands if command["name"] == "host-proof"), None)
            if host is not None:
                collect_custody(out, receipt, host)
        if "custodyHold" in receipt:
            raise RuntimeError("Signed-pair teardown requires a custody hold")
        with socket.socket() as observer:
            observer.settimeout(1)
            receipt["loopbackClosed"] = observer.connect_ex(("127.0.0.1", port)) == errno.ECONNREFUSED

        observations = receipt["observations"]
        verify_custody(out, receipt["children"], receipt["custodyControls"], observations)
        if not receipt["loopbackClosed"] or not any(line.startswith("FIELDLOG durable ") for line in observations):
            raise RuntimeError("Host test did not observe terminal durable recovery and listener closure")
        if any(digest(source / name) != sha for name, sha in sources.items()):
            raise RuntimeError("A host build input in the private snapshot changed during the replay")
        state_path = out / "recovery/state.json"
        state = strict_json(state_path.read_text())
        receipt["recoveryStateSHA256"] = digest(state_path)
        receipt["installedRuntime"] = state["fingerprint"]
        receipt["fixtures"] = {path.name: digest(path) for path in sorted((out / "public-fixtures").iterdir())}
        receipt["status"] = "PASS_MACOS_SIGNED_FIELDLOG_LOOPBACK"
    except (OSError, RuntimeError, ValueError) as error:
        receipt["error"] = str(error)
        raise
    finally:
        receipt["observedUTC"] = datetime.now(timezone.utc).isoformat()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(f'{receipt["status"]} {out / "receipt.json"}')


if __name__ == "__main__":
    main()

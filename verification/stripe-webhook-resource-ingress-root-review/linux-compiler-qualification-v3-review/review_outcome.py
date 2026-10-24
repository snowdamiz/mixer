#!/usr/bin/env python3
"""Replay retained V3 compiler observations; never execute native tools."""
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "verification/stripe-resource-linux-compiler-qualification-v3"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def check(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    seal_path = PACKET / "execution-seal.json"
    seal_hash = digest(seal_path)
    check(seal_hash == "814ae23a1351c2d370e174fb8bbcd62417764f517a4a9893868bd83e7710e49c", "execution seal changed")
    seal = read(seal_path)
    check(len(seal["files"]) == 107, "sealed inventory changed")
    for name, expected in seal["files"].items():
        check(digest(ROOT / name) == expected, f"sealed binding changed: {name}")
    receipt = read(PACKET / "attempt-1/receipt.json")
    outcome = read(PACKET / "execution-outcome.json")
    check(digest(PACKET / "execution-outcome.json") == "9d3b3fb54968451da68b3a30ac1dec677c98ad8fbcdcc486b70607c84f1112d8", "outcome changed")
    commands = receipt["commands"]
    check(len(commands) == 24, "command inventory changed")
    by_label = {command["label"]: command for command in commands}
    check(len(by_label) == 24, "duplicate command labels")
    for command in commands:
        for stream in command["outputs"].values():
            file = ROOT / stream["path"]
            check(digest(file) == stream["sha256"] and file.stat().st_size == stream["bytes"], "command output changed")

    def output(label, stream="stdout"):
        return (ROOT / by_label[label]["outputs"][stream]["path"]).read_text()

    check(by_label["qualify"]["exitCode"] == 0, "native compilation did not complete")
    check(by_label["start"]["exitCode"] == 0, "container did not start")
    native = output("qualify")
    script = (PACKET / "native-qualify.sh").read_text()
    check("set -eu\n" in script, "native failure propagation missing")
    hashes = {
        "fault_helper": "b7bfbcc94dc6add54c91f8d4815fe0594dde2c19206f1414acfe157dfd086558",
        "control_nif.so": "8620976b6e8d6282f3dea3235660fe75644182161b6cef1dbbdd0e5543bc049c",
    }
    for name, expected in hashes.items():
        for iteration in (1, 2):
            check(native.splitlines().count(f"{expected}  /tmp/mixer-compiler-qualification/run-{iteration}/{name}") == 1, "native product hash missing")
        check(f'cmp "$out/run-1/{name}" "$out/run-2/{name}"' in script, "repeat comparison missing")
    check(native.count("Machine:                           AArch64") == 4, "four native ELF headers missing")
    for marker in ("MIXER_C6_COMPILES=4", "MIXER_HELPER_EXECUTED=0", "MIXER_NIF_LOADED=0", "MIXER_BEAM_EXECUTED=0", "MIXER_RESOURCE_ROWS_EXECUTED=0"):
        check(native.splitlines().count(marker) == 1, "native terminal marker missing")
    check(by_label["product-1-fault_helper"]["exitCode"] == 1, "preserved export failure changed")
    check(by_label["product-1-fault_helper"]["outputs"]["stdout"]["bytes"] == 0, "unexpected product bytes")
    check("Could not find the file /tmp/mixer-compiler-qualification/run-1/fault_helper" in output("product-1-fault_helper", "stderr"), "export failure differs")
    check(outcome["externalProductBytesRetained"] == 0 and not outcome["compilerQualificationAccepted"], "incomplete export credited")

    identity = json.loads(output("cleanup-identity"))[0]
    name = receipt["containerName"]
    check(identity["Name"] == "/" + name, "foreign cleanup name")
    check(identity["Id"] == output("create").strip(), "foreign cleanup container")
    check(identity["Config"]["Labels"]["com.mixer.private-compiler-qualification.owner"] == receipt["ownerToken"], "foreign cleanup owner")
    check(identity["Config"]["Image"] == receipt["requiredImage"], "foreign cleanup image")
    check(by_label["cleanup-remove"]["exitCode"] == 0, "removal failed")
    check(by_label["cleanup-absence"]["exitCode"] == 1 and json.loads(output("cleanup-absence")) == [], "absence not observed")
    check(output("cleanup-absence", "stderr").strip() == "error: no such object: " + name, "absence response differs")
    mounts = identity["Mounts"]
    snapshots = [Path(mount["Source"]) for mount in mounts if mount["Destination"] == "/inputs"]
    check(len(snapshots) == 1 and not snapshots[0].exists(), "temporary input snapshot remains")
    check(receipt["cleanup"] == {"ownedContainerAbsent": True, "temporaryInputSnapshotRemoved": True}, "cleanup receipt disagrees")
    check(len(receipt["ERTSHeaders"]) == 10 and len(receipt["baseExportObservations"]) == 7, "preflight inventory differs")
    check(outcome["completedCompilationCommands"] == 4 and outcome["resourceRuntimeRowsExecuted"] == 0, "scope differs")
    result = {
        "schema": 1, "accountableReviewer": "/root", "observedUTC": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__).resolve())], "pythonVersion": platform.python_version(),
        "reviewerSHA256": digest(Path(__file__)), "executionSealSHA256": seal_hash, "verifiedFiles": 107,
        "sourceDigest": receipt["sourceDigest"], "sourceRevisionContext": "384e22ac22165fa309d8fcb628cc7a1ccb16eb2d",
        "nativeCommandsVerified": 24, "completedCompilationCommands": 4, "nativeRepeatComparisonsPassed": 2,
        "nativeReportedHashes": hashes, "externalProductBytesRetained": 0,
        "actualOutcome": "Four native compilations and repeat comparisons passed; first binary export failed.",
        "compilerQualificationAccepted": False, "helperExecuted": False, "NIFLoaded": False, "BEAMExecuted": False,
        "resourceRuntimeRowsExecuted": 0, "GAaccepted": False, "ownedContainerAbsent": True, "snapshotRemoved": True,
        "nativeRerunPerformed": False, "tmpfsVisibilityCauseProven": False,
        "next": "Review transport-only product export correction in a separate packet before selecting another attempt.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

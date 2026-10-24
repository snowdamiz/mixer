"""Three-way static bytes audit: input graph, native manifest, output tar.

Only streams data. No host extraction, executable payload loading, or execution.
"""
import hashlib
import json
from pathlib import Path
import tarfile
import time

import inspect_packages as inspection
import run_container as native


def main():
    here, root = inspection.HERE, inspection.ROOT
    require = inspection.require
    receipt = json.loads((here/"attempt/receipt.json").read_text())
    require(receipt["status"] == "native-static-assembly-completed-host-validation-pending"
            and receipt["assemblyExitCode"] == 0, "native static assembly unsuccessful")
    require(native.sha(native.SELECTION) == native.SELECTION_SHA, "selection changed")
    require(native.sha(here/"run_container.py") == receipt["runnerSha256"], "executed native runner changed")
    require(native.sha(here/"inputs/assemble.sh") == receipt["assemblyScriptSha256"], "executed assembly script changed")
    source_receipt = json.loads((here/"inspection/receipt.json").read_text())
    require(inspection.sha(here/"inspect_packages.py") == source_receipt["sourceSha256"], "executed inspector changed")
    require(inspection.sha(inspection.ACQUISITION/"seal.json") == inspection.ACQUISITION_SHA, "acquisition seal changed")
    preserved = json.loads((inspection.ACQUISITION/"seal.json").read_text())
    for name, expected in {**preserved["files"], **preserved["localCacheFiles"]}.items():
        require(inspection.sha(root/name) == expected, "immutable acquisition input changed")
    for command in receipt["commands"]:
        require(command["refusal"] is None and command["elapsedSeconds"] <= 30, "native command bound or failure")
        for record in command["outputs"].values():
            path = root/record["path"]
            require(path.stat().st_size == record["bytes"] and inspection.sha(path) == record["sha256"], "raw output changed")
    require(receipt["elapsedSecondsIncludingCleanup"] <= 120, "native wall bound")
    require(all(value <= 524288 for value in receipt["ordinaryStreamBytes"].values()), "ordinary stream bound")
    require(receipt["fixedArtifactExportBytes"] <= 301989888, "artifact aggregate bound")
    require(receipt["cleanup"] == {"ownedContainerAbsent": True, "temporaryInputSnapshotRemoved": True}, "native cleanup incomplete")
    for name, maximum in native.EXPORTS.items():
        record = receipt["artifacts"][name]
        require(record["available"] and record["bytes"] <= maximum, "fixed artifact export unavailable or over bound")
        path = root/record["path"]
        require(path.stat().st_size == record["bytes"] and inspection.sha(path) == record["sha256"], "artifact record changed")
    exports = here/"attempt/exports"
    for name in ("control-inventory.json", "notice-inventory.json"):
        require((exports/name).read_bytes() == (here/"inspection"/name).read_bytes(), "data-only control/notice export changed")
    expected_manifest = json.loads((here/"inspection/expected-manifest.json").read_text())
    expected = {item["path"]: item for item in expected_manifest["files"]}
    actual_manifest = json.loads((exports/"payload-manifest.json").read_text())
    actual = {item["path"]: item for item in actual_manifest["files"]}
    require(len(actual) == len(actual_manifest["files"]) and set(actual) == set(expected), "actual native path graph mismatch")
    total = 0
    for path, item in expected.items():
        record = actual[path]
        expected_type = {"file": "f", "directory": "d", "symlink": "l", "hardlink": "f"}[item["type"]]
        require(record["nativeType"] == expected_type and int(record["modeOctal"], 8) == item["mode"], "native type/mode mismatch")
        require(record["uid"] == record["gid"] == 65534, "unselected native ownership")
        if expected_type == "f":
            require(record["bytes"] == item["bytes"] and record["sha256"] == item["sha256"], "native file size/hash mismatch")
            total += item["bytes"]
        elif expected_type == "l":
            require(record["target"] == item["target"], "native symlink target mismatch")
    require(total == actual_manifest["expandedRegularBytes"] <= 536870912, "actual payload byte bound")
    # Native tar is a generated local artifact; all entries still undergo the
    # same bounded raw-header/path checks and independent per-file data hashes.
    budget = {"expanded": 0, "deadline": time.monotonic()+30}
    seen = set()
    with (exports/"compiler-payload.tar").open("rb") as stream:
        with tarfile.open(fileobj=inspection.BoundedReader(stream, budget), mode="r|", tarinfo=inspection.BoundedTarInfo) as archive:
            for member in archive:
                path = inspection.member_path(member.name)
                require(member.uid == member.gid == 0 and member.mtime == 0, "archive deterministic metadata mismatch")
                if not path:
                    require(member.isdir(), "archive root marker invalid")
                    continue
                require(path in expected and path not in seen, "unexpected/duplicate output archive path")
                seen.add(path)
                item = expected[path]
                require(member.mode == item["mode"], "output archive mode mismatch")
                if item["type"] == "file":
                    require(member.isfile() and member.size == item["bytes"], "output archive regular identity mismatch")
                    value = hashlib.sha256()
                    source = archive.extractfile(member)
                    require(source is not None, "output archive regular data absent")
                    while True:
                        block = source.read(65536)
                        if not block:
                            break
                        value.update(block)
                    require(value.hexdigest() == item["sha256"], "output archive data hash mismatch")
                elif item["type"] == "directory":
                    require(member.isdir(), "output archive directory mismatch")
                elif item["type"] == "symlink":
                    require(member.issym() and member.linkname == item["target"], "output archive symlink mismatch")
                else:
                    raise ValueError("unexpected hardlink in this observed zero-hardlink payload")
            while True:
                padding = archive.fileobj.read(65536)
                if not padding:
                    break
                require(not any(padding), "nonzero ambiguous output archive padding")
    require(seen == set(expected), "output archive graph incomplete")
    require("usr/bin/cc" not in actual and "MIXER_ARCHIVED_CC_PRESENT=0" in receipt["markers"], "cc absence evidence changed")
    print(json.dumps({"status": "three-way-static-payload-audit-pass", "paths": len(expected),
        "regularFiles": sum(item["type"] == "file" for item in expected.values()),
        "actualRegularBytes": total, "outputArchiveBytes": (exports/"compiler-payload.tar").stat().st_size,
        "insidePrefixDanglingDependencies": len(expected_manifest["danglingInsidePrefixLinks"]),
        "ccPresent": False, "toolchainClosureAccepted": False, "hostExtractionExecuted": False,
        "compilerOrHelperOrNifExecuted": False, "cleanupObserved": True}, sort_keys=True))


if __name__ == "__main__":
    main()

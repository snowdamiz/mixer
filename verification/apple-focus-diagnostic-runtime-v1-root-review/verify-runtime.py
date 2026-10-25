"""Verify retained local evidence without starting native or hosted processes."""
import datetime
import hashlib
import json
import pathlib
import platform
import stat
import sys

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / "verification/apple-focus-diagnostic-runtime-v1"
REVIEW = ROOT / "verification/apple-focus-diagnostic-runtime-v1-independent-review"
ANALYSIS = ROOT / "verification/apple-focus-diagnostic-v1-analysis"
PACKET = "d7c4c0f146434eeb7323036809acb5b4a80d41ff10f596eed8c25bdaa314e783"
bindings = {}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path, expected=None):
    assert path.is_file() and not path.is_symlink(), path
    value = sha(path)
    if expected is not None:
        assert value == expected, path
    bindings[str(path.relative_to(ROOT))] = value
    return value


def read(path, expected=None):
    bind(path, expected)
    return json.loads(path.read_bytes())


def verify_files(base, rows):
    for name, row in rows.items():
        relative = pathlib.PurePosixPath(name)
        assert not relative.is_absolute() and ".." not in relative.parts
        path = base / name
        bind(path, row["sha256"])
        info = path.stat()
        assert info.st_size == row["bytes"], path
        if "mode" in row:
            assert stat.S_IMODE(info.st_mode) == row["mode"], path


packet = read(PRODUCER / "packet.json", PACKET)
verify_files(PRODUCER, packet["ownedSourceFiles"])
read(PRODUCER / "input-lock.json", packet["inputLockSHA256"])
read(PRODUCER / "output-manifest.json", packet["outputManifestSHA256"])
bind(PRODUCER / "selected-runtime-sources.tar.gz", packet["selectedSourceArchive"]["sha256"])
read(PRODUCER / "selected-runtime-source-manifest.json", packet["selectedSourceArchiveManifestSHA256"])
bind(ROOT / "verification/apple-toggle-keyboard-focus-diagnostic-v1-build/products.tar.gz", packet["productArchiveSHA256"])
bind(ROOT / "docs/apple-focus-diagnostic-runtime-v1.md", packet["documentation"]["sha256"])
preparation = read(BASE / "acceptance.json")
review = read(REVIEW / "acceptance.json", preparation["independentReviewSHA256"])
freeze = read(REVIEW / "freeze-manifest.json", review["freezeManifest"]["sha256"])
verify_files(REVIEW, freeze["files"])
verify_files(PRODUCER, review["reviewedProducerInputs"])
host = read(PRODUCER / "host-receipt.json", preparation["hostReceiptSHA256"])
assert host["testsRun"] == 34 and host["passed"]
assert review["testsRun"] == 7 and review["failures"] == review["errors"] == review["skipped"] == 0

archive = read(BASE / "runtime-archive.json")
manifest = read(PRODUCER / "runtime-evidence-manifest.json", archive["manifestSHA256"])
runtime = PRODUCER / "runtime"
actual = {str(p.relative_to(runtime)) for p in runtime.rglob("*") if p.is_file()}
assert actual == set(manifest["files"])
verify_files(runtime, manifest["files"])
bind(PRODUCER / "runtime-evidence.tar.gz", archive["archiveSHA256"])
assert len(actual) == archive["files"] == 2726

analysis = read(ANALYSIS / "receipt.json", "206adbd7acc8856602f9315121d1c6214e4039d0f2d6f185a725488e883e5fc7")
bind(ANALYSIS / "reanalyze.py", analysis["scriptSHA256"])
for name, expected in analysis["inputSHA256"].items():
    bind(PRODUCER / name, expected)
for name, expected in analysis["outputs"].items():
    bind(ANALYSIS / name, expected)
bind(ROOT / "docs/apple-focus-diagnostic-v1-analysis.md", "404c2ff79949e677ba27f0bb8ea8bda136814c742522bb7e009efb689c4d2cbe")
assert analysis["passed"] and len(analysis["checksPassed"]) == 39
assert analysis["scratchOracleExtractionRemoved"] and not analysis["nativeExecuted"]
summary = read(ANALYSIS / "summary.json")
assert summary["strictReplay"]["falsePredicates"] == ["actualNativeFocusTraversal"]
assert not summary["strictReplay"]["passed"]

official = read(runtime / "xctest-summary.json")
assert (official["totalTestCount"], official["passedTests"], official["failedTests"], official["skippedTests"]) == (2, 1, 1, 0)
observer = read(runtime / "session/command-observer/observer.json")
assert observer["exitCode"] == 65 and all(row["eof"] for row in observer["streams"].values())
assert observer["ownedProcessGroup"]["state"] == "absent"
assert observer["outcome"] == "command-exited-and-streams-EOF"
lifecycle = read(runtime / "lifecycle.json")
assert len(lifecycle["cleanupResults"]) == 5 and all(row["passed"] for row in lifecycle["cleanupResults"])
assert all(lifecycle[name] for name in ["ownedDeviceAbsent", "baselineStatesPreserved", "secretConfigurationAbsent"])
cleanup = read(BASE / "cleanup-review.json")
assert cleanup["ownedSimulatorAbsent"] and cleanup["ownedCommandProcessGroupAbsent"]
assert cleanup["physicalDevicesQueried"] is False
scratch = read(BASE / "scratch-cleanup.json")
assert scratch["postNativePacketVerificationPassed"] and scratch["scratchAbsent"]
assert not (PRODUCER / "scratch").exists()
read(BASE / "dispatch.json")
bind(pathlib.Path(__file__).resolve())

result = {
    "schema": 1,
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-I", "-B", str(pathlib.Path(__file__).resolve())],
    "python": sys.version,
    "platform": platform.platform(),
    "status": "verified-failed-native-diagnostic-evidence",
    "packetSHA256": PACKET,
    "sourceRevisionMeaning": "Compilation label is inherited; exact source and product hashes define the run.",
    "compilationRevisionLabel": packet["sourceRevisionLabel"],
    "ownedSourceTreeSHA256": packet["ownedSourceTreeSHA256"],
    "producerHostControls": 34,
    "independentHostControls": 7,
    "offlineAnalysisChecks": 39,
    "runtimeFilesVerified": len(actual),
    "independentFilesVerified": len(freeze["files"]),
    "officialTests": {"total": 2, "passed": 1, "failed": 1, "skipped": 0},
    "nativeRunPassed": False,
    "firstTabPredicate": "actualNativeFocusTraversal failed",
    "completedCursors": 0,
    "xcodebuildExitCode": 65,
    "xcodebuildElapsedSeconds": observer["elapsedSeconds"],
    "bothCommandStreamsReachedEOF": True,
    "ownedCommandGroupAbsent": True,
    "ownedSimulatorAbsent": True,
    "cleanupOperationsPassed": 5,
    "ownedPreparedScratchRemovedBytes": scratch["removedFileBytes"],
    "physicalPhones": "disconnected-deferred",
    "gaAccepted": False,
    "limitations": [
        "Settings setup passes; first Tab remains failed with no identified replacement focus item.",
        "The earlier command-finalization stall was not reproduced; its cause is still unproved.",
        "Fixed sequential AX reads are neither an atomic nor a continuous focus observation.",
        "No comparator, complete keyboard matrix, physical-phone, FieldLog or GA qualification.",
        "Raw xcresult, media, compiled copies and complete runtime archive remain local; compact evidence is published separately.",
        "Prepared scratch was intentionally retired after post-run verification; do not replay this selected packet.",
    ],
    "inputSHA256": bindings,
}
(BASE / "runtime-review.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({key: result[key] for key in ["status", "runtimeFilesVerified", "independentFilesVerified", "offlineAnalysisChecks", "officialTests", "nativeRunPassed"]}, sort_keys=True))

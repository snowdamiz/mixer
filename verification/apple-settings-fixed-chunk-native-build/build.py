#!/usr/bin/env python3
"""Fresh generic runner build from the root-selected fixed4992 source closure.

No device query, simulator lifecycle command, runner execution, or network task.
Only the original application bytes are reused; every runner product is fresh.
"""
import collections
import datetime
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time
import traceback

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "attempt-1"
SCRATCH = OUT / "owned-build"
DEV = Path("/Applications/Xcode_26.6.app/Contents/Developer")
SDK = DEV / "Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk"
REVISION = "be472ce6424a691de5673e3438d2768264827d23"
PRODUCER = "verification/apple-settings-fixed-chunk-implementation"
REVIEW = "verification/apple-settings-fixed-chunk-review"
PRIOR = "verification/apple-settings-instrumented-native-build"
SELECTION = "verification/apple-settings-fixed-chunk-root-review/acceptance.json"
PINS = {
    SELECTION: "2addcd0f2b37463241cec8451b444cb4b933ce5dfcf5b2f0ecec483aae2b7db8",
    PRODUCER + "/handoff.json": "2d01866f3fa0f88b283ba8f2774f03092eb93d9616daeaa7d5d2875618cf6748",
    REVIEW + "/handoff.json": "43f2ee87e461d28a8d05d113adf7a9581ea34c6d16e0dfe5caee26773febc092",
    PRIOR + "/handoff.json": "246f5e9486f804d2ab784ba474696bcf7905873aa5a1200117b570bd66933e91",
    PRODUCER + "/review-source-package.tar.gz": "585f44532cb67ca626ae7c2c95bfa7030408bf2b4dc57f5bac0fdbd84cea66af",
    "verification/apple-focus-reference-runtime-v5/frozen-inputs.tar.gz": "3b509aadf2b31314ec9fd910acb4fe3b3040505a446fff8f691bf765a599da7e",
    "verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/commands/runner.stdout": "0cd1b66a3e73b6ad7cfa8a8511106db40fe40c64004e4c1e7ad572f573da48e3",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def row(raw, mode):
    return {"kind": "file", "mode": mode, "bytes": len(raw), "sha256": sha(raw)}


def binding(path, exclusive=False):
    s = path.lstat()
    assert stat.S_ISREG(s.st_mode) and not path.is_symlink(), path
    assert not exclusive or s.st_nlink == 1, path
    return row(path.read_bytes(), stat.S_IMODE(s.st_mode))


def save(name, value):
    (OUT / name).write_bytes(canonical(value))


def safe(name):
    p = PurePosixPath(name)
    assert name and not p.is_absolute() and ".." not in p.parts and str(p) == name, name


def payload(raw):
    """Inspect confined directory/regular-only archives; never extract links."""
    result = {}
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for m in archive:
            safe(m.name)
            assert m.name not in seen, m.name
            seen.add(m.name)
            assert m.isdir() or m.isfile(), (m.name, m.type)
            if m.isfile():
                result[m.name] = (archive.extractfile(m).read(), m.mode)
    assert not any(str(PurePosixPath(n).parent) in result for n in result)
    return result


def rows(values):
    return {n: row(b, m) for n, (b, m) in sorted(values.items())}


def materialize(values, destination):
    assert not destination.exists()
    destination.mkdir(parents=True)
    for name, (raw, mode) in sorted(values.items()):
        safe(name)
        p = destination / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        p.chmod(mode)


def tree(path):
    result = {}
    for p in sorted(path.rglob("*")):
        s = p.lstat()
        assert stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode), p
        if stat.S_ISREG(s.st_mode):
            result[str(p.relative_to(path))] = binding(p, True)
    return result


def archive_tree(path, source):
    expected = tree(source)
    # Explicit regular headers and fixed metadata avoid hardlink aliasing.
    with path.open("wb") as out:
        with gzip.GzipFile(filename="", fileobj=out, mode="wb", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for name, r in expected.items():
                    raw = (source / name).read_bytes()
                    m = tarfile.TarInfo(name)
                    m.size = len(raw)
                    m.mode = r["mode"]
                    m.mtime = 0
                    archive.addfile(m, io.BytesIO(raw))
    assert rows(payload(path.read_bytes())) == expected
    return expected


def group_members(pgid):
    r = subprocess.run(["/bin/ps", "-axo", "pid=,pgid="], capture_output=True, timeout=10, check=True)
    assert not r.stderr
    return [int(line.split()[0]) for line in r.stdout.decode().splitlines() if int(line.split()[1]) == pgid]


def verify_inputs():
    for n, expected in PINS.items():
        assert binding(ROOT / n)["sha256"] == expected, n
    counts = {}
    for lane, count in [(PRODUCER, 176), (REVIEW, 163), (PRIOR, 22)]:
        handoff = json.loads((ROOT / lane / "handoff.json").read_bytes())
        for n, expected in handoff["members"].items():
            safe(n)
            actual = binding(ROOT / n)
            assert all(actual[k] == v for k, v in expected.items()), n
        assert len(handoff["members"]) == count, (lane, len(handoff["members"]))
        counts[lane] = count
    a = json.loads((ROOT / SELECTION).read_bytes())
    assert a["sourceRevision"] == REVISION and a["sourceAndHostAccepted"]
    assert a["freshGenericRunnerBuildSelected"] and not a["nativeExecutionSelected"] and not a["gaAccepted"]
    assert a["producerHandoffSHA256"] == PINS[PRODUCER + "/handoff.json"]
    assert a["reviewHandoffSHA256"] == PINS[REVIEW + "/handoff.json"]
    return counts


def warnings(raw):
    return [line.split("warning:", 1)[1].strip() for line in raw.decode().splitlines() if "warning:" in line]


def main():
    assert not OUT.exists(), "Do not overwrite an earlier attempt"
    OUT.mkdir(parents=True)
    counts = verify_inputs()
    save("input-bindings.json", {"schema": 1, "controllerSourceRevision": REVISION, "pins": PINS, "handoffMembersVerified": counts})
    package = payload((ROOT / PRODUCER / "review-source-package.tar.gz").read_bytes())
    assert len(package) == 97
    source_payload = {n.removeprefix("package/sources/"): v for n, v in package.items() if n.startswith("package/sources/accepted/")}
    original = payload((ROOT / PRIOR / "attempt-1/accepted-sources.tar.gz").read_bytes())
    assert len(source_payload) == len(original) == 40 and set(source_payload) == set(original)
    changed = [n for n in source_payload if source_payload[n] != original[n]]
    assert changed == ["accepted/harness/UITests/ToggleUITests.swift"], changed
    source_bindings = json.loads(package["package/source-bindings.json"][0])
    assert source_bindings["unchangedSourceFiles"] == 70 and len(source_bindings["derivativeFiles"]) == 72
    for n, r in rows(source_payload).items():
        assert {k: r[k] for k in ["bytes", "sha256"]} == source_bindings["derivativeFiles"][n], n
    typecheck = json.loads((ROOT / REVIEW / "typecheck.json").read_bytes())
    exact_four = {PurePosixPath(n).name: sha(b) for n, (b, _) in source_payload.items() if n.startswith("accepted/harness/UITests/")}
    assert exact_four == typecheck["exactSourceHashes"] and len(exact_four) == 4
    assert exact_four["ToggleUITests.swift"] == "0e43bd202946711ff6f1c89c8ebeb7d26f692f7ab4d5ec862e67e674f3765fb3"
    SCRATCH.mkdir()
    (SCRATCH / "tmp").mkdir()
    materialize(source_payload, SCRATCH / "sources")
    source_rows = archive_tree(OUT / "accepted-sources.tar.gz", SCRATCH / "sources")
    save("source-manifest.json", {"schema": 1, "sources": source_rows, "sourceTreeSHA256": sha(canonical(source_rows)), "changedFromPriorCompileClosure": changed, "unchangedCompileClosureFiles": 39, "exactFourSwiftFiles": exact_four, "archive": binding(OUT / "accepted-sources.tar.gz"), "reviewSourceArchiveSHA256": PINS[PRODUCER + "/review-source-package.tar.gz"], "projectAndSchemeUnchanged": True})
    commands = []

    def command(name, argv, timeout):
        argv = list(map(str, argv))
        env = os.environ.copy()
        explicit = {"DEVELOPER_DIR": str(DEV), "SDKROOT": str(SDK), "LC_ALL": "C", "TMPDIR": str(SCRATCH / "tmp") + "/", "CLANG_MODULE_CACHE_PATH": str(SCRATCH / "module-cache"), "SWIFT_MODULECACHE_PATH": str(SCRATCH / "module-cache")}
        env.update(explicit)
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        stamp = time.monotonic()
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        sent = []
        timedout = False
        try:
            out, err = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timedout = True
            if group_members(child.pid):
                os.killpg(child.pid, signal.SIGTERM)
                sent.append("SIGTERM")
            try:
                out, err = child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                if group_members(child.pid):
                    os.killpg(child.pid, signal.SIGKILL)
                    sent.append("SIGKILL")
                out, err = child.communicate(timeout=5)
        (OUT / (name + ".stdout")).write_bytes(out)
        (OUT / (name + ".stderr")).write_bytes(err)
        absent = not group_members(child.pid)
        commands.append({"name": name, "argv": argv, "cwd": str(ROOT), "explicitEnvironment": explicit, "startedUTC": started, "elapsedSeconds": time.monotonic() - stamp, "exitCode": child.returncode, "timeoutSeconds": timeout, "timedOut": timedout, "signalsSent": sent, "ownedPID": child.pid, "ownedPGID": child.pid, "processGroupAbsent": absent, "stdoutEOF": True, "stderrEOF": True, "stdoutSHA256": sha(out), "stderrSHA256": sha(err)})
        save("commands.json", commands)
        assert absent, "Preserve scratch: owned process survives"
        return child.returncode, out, err

    swift = DEV / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc"
    tool_paths = [swift.resolve(), swift.with_name("swift-frontend").resolve(), DEV / "usr/bin/xcodebuild", SDK.resolve() / "SDKSettings.json", Path(sys.executable).resolve()]
    tools_before = {str(p): binding(p) for p in tool_paths}
    assert tools_before[str(swift.resolve())]["sha256"] == typecheck["compilerSHA256"]
    assert tools_before[str(SDK.resolve() / "SDKSettings.json")]["sha256"] == typecheck["sdkSettingsSHA256"]
    save("tools.json", {"schema": 1, "bindings": tools_before, "sdkRequested": str(SDK), "sdkResolved": str(SDK.resolve()), "pythonVersion": sys.version})
    for name, argv, expected in [("xcode-version", [DEV / "usr/bin/xcodebuild", "-version"], b"Xcode 26.6\nBuild version 17F113\n"), ("swift-version", [swift, "--version"], b"Apple Swift version 6.3.3 (swiftlang-6.3.3.5.2 clang-2100.3.34.2)\nTarget: arm64-apple-macosx26.0\n"), ("sdk-version", [DEV / "usr/bin/xcodebuild", "-version", "-sdk", SDK, "SDKVersion"], b"26.5\n")]:
        code, out, _ = command(name, argv, 30)
        assert code == 0 and (name == "swift-version" or out == expected), (name, out)
        if name == "swift-version":
            assert b"Apple Swift version 6.3.3" in out
    argv = [DEV / "usr/bin/xcodebuild", "build-for-testing", "-project", SCRATCH / "sources/accepted/harness/MixerToggleUITests.xcodeproj", "-scheme", "MixerToggleUITests", "-sdk", "iphonesimulator", "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", SCRATCH / "runner-build", "-disableAutomaticPackageResolution", "-skipPackageUpdates", "CODE_SIGNING_ALLOWED=NO", "CODE_SIGNING_REQUIRED=NO", "ARCHS=arm64", "IPHONEOS_DEPLOYMENT_TARGET=26.0", "COMPILER_INDEX_STORE_ENABLE=NO", "SWIFT_MODULE_CACHE_PATH=" + str(SCRATCH / "module-cache"), "CLANG_MODULE_CACHE_PATH=" + str(SCRATCH / "module-cache")]
    assert not (SCRATCH / "runner-build").exists()
    code, out, err = command("runner-build", argv, 240)
    assert tree(SCRATCH / "sources") == source_rows
    assert {str(p): binding(p) for p in tool_paths} == tools_before
    old_warning_paths = ["verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/commands/runner.stdout", PRIOR + "/attempt-1/runner-build.stdout"]
    old_warnings = {n: warnings((ROOT / n).read_bytes()) for n in old_warning_paths}
    current_warnings = warnings(out) + warnings(err)
    save("warning-comparison.json", {"schema": 1, "newLog": str((OUT / "runner-build.stdout").relative_to(ROOT)), "newWarningLines": len(current_warnings), "newWarnings": current_warnings, "baselines": {n: {"sha256": sha((ROOT / n).read_bytes()), "warningLines": len(w), "warnings": w, "sameMessageMultiset": collections.Counter(w) == collections.Counter(current_warnings)} for n, w in old_warnings.items()}, "compilerAndMetadataWarnings": sum(not w.startswith("not stripping binary because it is signed:") for w in current_warnings), "signedAppleFrameworkStrippingWarnings": sum(w.startswith("not stripping binary because it is signed:") for w in current_warnings), "priorSummaryCountWasPartial": True, "warningsSuppressed": False})
    with tarfile.open(ROOT / "verification/apple-focus-reference-runtime-v5/frozen-inputs.tar.gz") as frozen:
        old_archive = frozen.extractfile("verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/products.tar.gz").read()
        old_manifest = frozen.extractfile("verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/product-manifest.json").read()
    assert sha(old_archive) == "0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8"
    assert sha(old_manifest) == "2791292716192ebfa074854007a1867f3477c45fcfb86365c0f5ea1ab91ddb9a"
    original_products = payload(old_archive)
    assert rows(original_products) == json.loads(old_manifest)["products"]
    app = {n: v for n, v in original_products.items() if n.startswith("MixerToggleDiagnostics.app/")}
    assert len(app) == 13
    materialize(app, SCRATCH / "export")
    products = SCRATCH / "runner-build/Build/Products"
    if products.is_dir():
        shutil.copytree(products, SCRATCH / "export/runner-products")
    product_archive = OUT / ("products.tar.gz" if code == 0 else "failed-partial-products.tar.gz")
    product_rows = archive_tree(product_archive, SCRATCH / "export")
    assert all(product_rows[n] == r for n, r in rows(app).items())
    save("product-manifest.json", {"schema": 1, "products": product_rows, "archive": binding(product_archive), "productTreeSHA256": sha(canonical(product_rows)), "sourceTreeSHA256": sha(canonical(source_rows)), "target": "arm64-apple-ios26.0-simulator", "originalApplicationFilesUnchanged": len(app), "originalApplicationFiles": rows(app), "originalQualificationArchiveSHA256": sha(old_archive), "originalQualificationManifestSHA256": sha(old_manifest), "runnerProductsFresh": code == 0, "runnerProductFiles": sum(n.startswith("runner-products/") for n in product_rows), "nativeExecuted": False})
    assert verify_inputs() == counts
    holders = subprocess.run(["/usr/sbin/lsof", "-nP", "+D", str(SCRATCH)], capture_output=True, timeout=30)
    (OUT / "holders.stdout").write_bytes(holders.stdout)
    (OUT / "holders.stderr").write_bytes(holders.stderr)
    save("holder-check.json", {"argv": ["/usr/sbin/lsof", "-nP", "+D", str(SCRATCH)], "exitCode": holders.returncode, "stdoutEOF": True, "stderrEOF": True, "stdoutSHA256": sha(holders.stdout), "stderrSHA256": sha(holders.stderr)})
    assert holders.returncode == 1 and not holders.stdout and not holders.stderr
    assert all(not group_members(c["ownedPGID"]) for c in commands)
    removed = sum(p.stat().st_size for p in SCRATCH.rglob("*") if p.is_file())
    shutil.rmtree(SCRATCH)
    save("cleanup.json", {"ownedScratchRemoved": not SCRATCH.exists(), "removedFileBytes": removed, "processGroupsAbsent": True, "holdersAbsent": True, "nativeInstancesTouched": 0, "otherProjectsTouched": False})
    comparison = json.loads((OUT / "warning-comparison.json").read_bytes())
    passed = code == 0 and all(c["exitCode"] == 0 and not c["timedOut"] and not c["signalsSent"] for c in commands) and all(b["sameMessageMultiset"] for b in comparison["baselines"].values())
    save("receipt.json", {"schema": 1, "status": "compiled-generic-simulator-runner-only" if passed else "build-or-comparison-failed-preserved", "controllerSourceRevision": REVISION, "sourceTreeSHA256": sha(canonical(source_rows)), "productTreeSHA256": sha(canonical(product_rows)), "buildScript": binding(Path(__file__)), "sourceArchive": binding(OUT / "accepted-sources.tar.gz"), "productArchive": binding(product_archive), "buildExitCode": code, "passed": passed, "sourceFiles": len(source_rows), "products": len(product_rows), "exactFourSwiftFiles": exact_four, "originalApplicationFilesUnchanged": len(app), "runnerProductFilesFresh": sum(n.startswith("runner-products/") for n in product_rows), "warningLines": len(current_warnings), "compilerAndMetadataWarnings": comparison["compilerAndMetadataWarnings"], "signedAppleFrameworkStrippingWarnings": comparison["signedAppleFrameworkStrippingWarnings"], "allWarningMessagesMatchOriginalAndPrior": all(b["sameMessageMultiset"] for b in comparison["baselines"].values()), "allCommandsExitZeroEOFAndGroupsAbsent": all(c["exitCode"] == 0 and c["stdoutEOF"] and c["stderrEOF"] and c["processGroupAbsent"] for c in commands), "inputsUnchangedAfterBuild": True, "ownedScratchRemoved": True, "simulatorInventoryOrLifecycle": False, "nativeExecuted": False, "nativeExecutionSelected": False, "importerRebound": False, "physicalPhones": "disconnected-deferred", "gaAccepted": False})
    print(json.dumps({"passed": passed, "runnerBuildExitCode": code, "sourceFiles": len(source_rows), "products": len(product_rows), "originalApplicationFilesUnchanged": len(app), "warningLines": len(current_warnings), "ownedScratchRemoved": True}), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        if OUT.exists():
            (OUT / "failure.txt").write_text(traceback.format_exc())
        raise

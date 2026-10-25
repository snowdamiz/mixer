#!/usr/bin/env python3
"""Build the accepted diagnostic runner; reuse the exact original application."""
import datetime
import difflib
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

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "attempt-1"
SCRATCH = OUT / "owned-build"
DEV = Path("/Applications/Xcode_26.6.app/Contents/Developer")
SDK = DEV / "Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk"
PRODUCER = ROOT / "verification/apple-settings-failure-instrumentation"
FROZEN = ROOT / "verification/apple-focus-reference-runtime-v5/frozen-inputs.tar.gz"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(path):
    s = path.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and not path.is_symlink(), path
    raw = path.read_bytes()
    return {"kind": "file", "mode": stat.S_IMODE(s.st_mode), "bytes": len(raw), "sha256": digest(raw)}


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def safe(name):
    p = PurePosixPath(name)
    assert name and not p.is_absolute() and ".." not in p.parts and str(p) == name


def payload(raw):
    result = {}
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive:
            safe(member.name)
            assert member.name not in seen
            seen.add(member.name)
            if member.isdir():
                continue
            assert member.isfile()
            data = archive.extractfile(member).read()
            result[member.name] = (data, member.mode)
    return result


def materialize(values, destination):
    assert not destination.exists()
    destination.mkdir(parents=True)
    for name, (raw, mode) in values.items():
        safe(name)
        p = destination / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        p.chmod(mode)


def tree(path):
    return {str(p.relative_to(path)): binding(p) for p in sorted(path.rglob("*")) if p.is_file()}


def archive_tree(path, source):
    rows = tree(source)
    with tarfile.open(path, "w:gz") as out:
        for child in sorted(source.iterdir()):
            out.add(child, arcname=child.name, recursive=True)
    recovered = payload(path.read_bytes())
    assert {n: {"kind": "file", "mode": m, "bytes": len(b), "sha256": digest(b)} for n, (b, m) in recovered.items()} == rows
    return rows


def members(pgid):
    r = subprocess.run(["/bin/ps", "-axo", "pid=,pgid="], capture_output=True, timeout=10, check=True)
    assert not r.stderr
    return [int(row.split()[0]) for row in r.stdout.decode().splitlines() if int(row.split()[1]) == pgid]


def main():
    acceptance = ROOT / "verification/apple-settings-failure-instrumentation-root-review/acceptance.json"
    assert digest(acceptance.read_bytes()) == "9956f0384828da9cdd8082ca387716c439131f6a2f0c4fcde4065cc5c96995ff"
    a = json.loads(acceptance.read_text())
    assert a["nativePreparationSelected"] and not a["nativeExecutionSelected"]
    assert not OUT.exists()
    OUT.mkdir()
    SCRATCH.mkdir()
    (SCRATCH / "tmp").mkdir()
    assert digest(FROZEN.read_bytes()) == "3b509aadf2b31314ec9fd910acb4fe3b3040505a446fff8f691bf765a599da7e"
    with tarfile.open(FROZEN) as frozen:
        sources = frozen.extractfile("verification/apple-focus-reference-diagnostic-v1/accepted-sources.tar.gz").read()
        old_products = frozen.extractfile("verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/products.tar.gz").read()
        old_manifest = frozen.extractfile("verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/product-manifest.json").read()
    assert digest(sources) == "c1e59b3e950acfe4afa46ae69e8eed29e6c8e1816e1d845e1c40548833201294"
    assert digest(old_products) == "0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8"
    assert digest(old_manifest) == "2791292716192ebfa074854007a1867f3477c45fcfb86365c0f5ea1ab91ddb9a"
    source_payload = payload(sources)
    original = dict(source_payload)
    for name in ["DiagnosticTransport.swift", "SettingsFailureDiagnostic.swift", "ToggleUITests.swift"]:
        raw = (PRODUCER / "derivative" / name).read_bytes()
        assert digest(raw) == a["sourceFiles"][name]
        source_payload["accepted/harness/UITests/" + name] = (raw, 0o644)
    project = "accepted/harness/MixerToggleUITests.xcodeproj/project.pbxproj"
    text = source_payload[project][0].decode()
    old = "children = (A00000000000000000000019,"
    assert text.count(old) == 1
    text = text.replace(old, "children = (A00000000000000000000021,A00000000000000000000019,")
    old = "files = (A00000000000000000000020,"
    assert text.count(old) == 1
    text = text.replace(old, "files = (A00000000000000000000022,A00000000000000000000020,")
    old = " };\n rootObject ="
    assert text.count(old) == 1
    text = text.replace(old, '  A00000000000000000000021 = { isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = UITests/SettingsFailureDiagnostic.swift; sourceTree = "<group>"; };\n  A00000000000000000000022 = { isa = PBXBuildFile; fileRef = A00000000000000000000021; };\n' + old)
    source_payload[project] = (text.encode(), 0o644)
    changed = [n for n in source_payload if source_payload[n] != original.get(n)]
    assert sorted(changed) == sorted([project, "accepted/harness/UITests/ToggleUITests.swift", "accepted/harness/UITests/SettingsFailureDiagnostic.swift"])
    (OUT / "project.patch").write_text("".join(difflib.unified_diff(original[project][0].decode().splitlines(True), text.splitlines(True), fromfile="original/" + project, tofile="derivative/" + project)))
    materialize(source_payload, SCRATCH / "sources")
    source_rows = archive_tree(OUT / "accepted-sources.tar.gz", SCRATCH / "sources")
    save("source-manifest.json", {"schema": 1, "sources": source_rows, "changedSources": changed, "archive": binding(OUT / "accepted-sources.tar.gz"), "rootAcceptanceSHA256": digest(acceptance.read_bytes())})
    commands = []

    def command(name, argv, timeout):
        argv = list(map(str, argv))
        env = os.environ.copy()
        explicit = {"DEVELOPER_DIR": str(DEV), "SDKROOT": str(SDK), "LC_ALL": "C", "TMPDIR": str(SCRATCH / "tmp") + "/", "CLANG_MODULE_CACHE_PATH": str(SCRATCH / "module-cache"), "SWIFT_MODULECACHE_PATH": str(SCRATCH / "module-cache")}
        env.update(explicit)
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        stamp = time.monotonic()
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        signals = []
        timedout = False
        try:
            out, err = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timedout = True
            if members(child.pid):
                os.killpg(child.pid, signal.SIGTERM)
                signals.append("SIGTERM")
            try:
                out, err = child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                if members(child.pid):
                    os.killpg(child.pid, signal.SIGKILL)
                    signals.append("SIGKILL")
                out, err = child.communicate(timeout=5)
        (OUT / (name + ".stdout")).write_bytes(out)
        (OUT / (name + ".stderr")).write_bytes(err)
        absent = not members(child.pid)
        commands.append({"name": name, "argv": argv, "cwd": str(ROOT), "explicitEnvironment": explicit, "startedUTC": started, "elapsedSeconds": time.monotonic() - stamp, "exitCode": child.returncode, "timeoutSeconds": timeout, "timedOut": timedout, "signalsSent": signals, "ownedPID": child.pid, "ownedPGID": child.pid, "processGroupAbsent": absent, "stdoutEOF": True, "stderrEOF": True, "stdoutSHA256": digest(out), "stderrSHA256": digest(err)})
        save("commands.json", commands)
        assert absent, "Preserve scratch: owned process survives"
        return child.returncode, out

    swift = DEV / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc"
    for name, argv, expected in [("xcode-version", [DEV / "usr/bin/xcodebuild", "-version"], b"Xcode 26.6\nBuild version 17F113\n"), ("swift-version", [swift, "--version"], None), ("sdk-version", [DEV / "usr/bin/xcodebuild", "-version", "-sdk", SDK, "SDKVersion"], b"26.5\n")]:
        code, out = command(name, argv, 30)
        assert code == 0 and (expected is None or out == expected)
    save("tools.json", {str(p.resolve()): binding(p.resolve()) for p in [swift, swift.with_name("swift-frontend"), DEV / "usr/bin/xcodebuild", SDK / "SDKSettings.json", Path(sys.executable)]})
    argv = [DEV / "usr/bin/xcodebuild", "build-for-testing", "-project", SCRATCH / "sources/accepted/harness/MixerToggleUITests.xcodeproj", "-scheme", "MixerToggleUITests", "-sdk", "iphonesimulator", "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", SCRATCH / "runner-build", "-disableAutomaticPackageResolution", "-skipPackageUpdates", "CODE_SIGNING_ALLOWED=NO", "CODE_SIGNING_REQUIRED=NO", "ARCHS=arm64", "IPHONEOS_DEPLOYMENT_TARGET=26.0", "COMPILER_INDEX_STORE_ENABLE=NO", "SWIFT_MODULE_CACHE_PATH=" + str(SCRATCH / "module-cache"), "CLANG_MODULE_CACHE_PATH=" + str(SCRATCH / "module-cache")]
    code, _ = command("runner-build", argv, 240)
    assert tree(SCRATCH / "sources") == source_rows
    original_products = payload(old_products)
    expected_products = json.loads(old_manifest)["products"]
    assert {n: {"kind": "file", "mode": m, "bytes": len(b), "sha256": digest(b)} for n, (b, m) in original_products.items()} == expected_products
    app = {n: v for n, v in original_products.items() if n.startswith("MixerToggleDiagnostics.app/")}
    materialize(app, SCRATCH / "export")
    products = SCRATCH / "runner-build/Build/Products"
    if products.is_dir():
        shutil.copytree(products, SCRATCH / "export/runner-products")
    product_archive = OUT / ("products.tar.gz" if code == 0 else "failed-partial-products.tar.gz")
    product_rows = archive_tree(product_archive, SCRATCH / "export")
    assert all(product_rows[n] == expected_products[n] for n in app)
    save("product-manifest.json", {"schema": 1, "products": product_rows, "archive": binding(product_archive), "productTreeSHA256": digest((json.dumps(product_rows, indent=2, sort_keys=True) + "\n").encode()), "target": "arm64-apple-ios26.0-simulator", "originalApplicationFilesUnchanged": len(app), "runnerRebuilt": code == 0, "nativeExecuted": False})
    holders = subprocess.run(["/usr/sbin/lsof", "-nP", "+D", str(SCRATCH)], capture_output=True, timeout=30)
    (OUT / "holders.stdout").write_bytes(holders.stdout)
    (OUT / "holders.stderr").write_bytes(holders.stderr)
    assert holders.returncode == 1 and not holders.stdout and not holders.stderr
    assert all(not members(c["ownedPGID"]) for c in commands)
    removed = sum(p.stat().st_size for p in SCRATCH.rglob("*") if p.is_file())
    shutil.rmtree(SCRATCH)
    save("cleanup.json", {"ownedScratchRemoved": not SCRATCH.exists(), "removedFileBytes": removed, "processGroupsAbsent": True, "holdersAbsent": True, "nativeInstancesTouched": 0})
    save("receipt.json", {"schema": 1, "status": "compiled-generic-simulator-runner" if code == 0 else "compile-failed-preserved", "sourceRevisionContext": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "buildScript": binding(Path(__file__)), "sourceArchive": binding(OUT / "accepted-sources.tar.gz"), "productArchive": binding(product_archive), "exitCode": code, "originalApplicationFilesUnchanged": len(app), "nativeExecuted": False, "nativeExecutionSelected": False, "physicalPhones": "disconnected-deferred", "gaAccepted": False, "ownedScratchRemoved": True})
    print(json.dumps({"runnerBuildExitCode": code, "sourceFiles": len(source_rows), "products": len(product_rows), "originalApplicationFilesUnchanged": len(app), "ownedScratchRemoved": True}), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Review immutable inputs and typecheck the complete XCTest derivative; no runtime."""
import datetime
import hashlib
import json
import io
import tarfile
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / "verification/apple-settings-failure-instrumentation"
REVIEW = ROOT / "verification/apple-settings-failure-instrumentation-review"
DEV = Path("/Applications/Xcode_26.6.app/Contents/Developer")
SWIFT = DEV / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc"
SDK = DEV / "Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk"
OUT = HERE / "attempts/typecheck-2"
SCRATCH = OUT / "owned-typecheck"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def group_members(pgid):
    observed = subprocess.run(["/bin/ps", "-axo", "pid=,pgid="], capture_output=True, timeout=10)
    assert observed.returncode == 0 and not observed.stderr
    rows = [tuple(map(int, row.split())) for row in observed.stdout.decode().splitlines()]
    assert all(len(row) == 2 for row in rows)
    return [pid for pid, group in rows if group == pgid]


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    for folder, expected in [(PRODUCER, "d637e80716b9407028f059dd44673e09cd74f536d7bec2909fa02a0da5b40190"),
                             (REVIEW, "2bb9a71648df29c1a46e928a0037eebe31418388108ad5169264da7721ec4316")]:
        assert sha(folder / "handoff.json") == expected
        for name, binding in json.loads((folder / "handoff.json").read_text())["members"].items():
            path = ROOT / name
            assert path.stat().st_size == binding["bytes"] and sha(path) == binding["sha256"], name
    verify = [sys.executable, "-B", str(PRODUCER / "verify.py"), "--expected-handoff-sha256", sha(PRODUCER / "handoff.json")]
    checked = subprocess.run(verify, capture_output=True, timeout=45)
    (OUT / "producer-verify.stdout").write_bytes(checked.stdout)
    (OUT / "producer-verify.stderr").write_bytes(checked.stderr)
    assert checked.returncode == 0, checked.stderr.decode()
    assert not SCRATCH.exists()
    SCRATCH.mkdir()
    names = ["DiagnosticTransport.swift", "SettingsFailureDiagnostic.swift", "ToggleUITests.swift"]
    for name in names:
        shutil.copyfile(PRODUCER / "derivative" / name, SCRATCH / name)
    binding = json.loads((PRODUCER / "source-bindings.json").read_text())["sources"][0]
    archive = ROOT / binding["archive"]
    assert sha(archive) == binding["archiveSHA256"]
    with tarfile.open(archive) as outer:
        nested = outer.extractfile(binding["nestedMember"]).read()
    assert hashlib.sha256(nested).hexdigest() == binding["nestedSHA256"]
    member = "accepted/harness/UITests/PublicSwitchSelection.swift"
    with tarfile.open(fileobj=io.BytesIO(nested)) as inner:
        helper = inner.extractfile(member).read()
    assert len(helper) == 6149 and hashlib.sha256(helper).hexdigest() == "c8aafd9829b5a19c23eceb27e196248619df7a3c468b48791c064209987473a7"
    (SCRATCH / "PublicSwitchSelection.swift").write_bytes(helper)
    save("helper-binding.json", {"archive": binding["archive"], "archiveSHA256": binding["archiveSHA256"], "nestedMember": binding["nestedMember"], "nestedSHA256": binding["nestedSHA256"], "member": member, "bytes": len(helper), "sha256": hashlib.sha256(helper).hexdigest()})
    names.append("PublicSwitchSelection.swift")
    source = {name: sha(SCRATCH / name) for name in names}
    argv = [str(SWIFT), "-typecheck", "-target", "arm64-apple-ios26.0-simulator", "-sdk", str(SDK),
            "-F", str(DEV / "Platforms/iPhoneSimulator.platform/Developer/Library/Frameworks"),
            "-I", str(DEV / "Platforms/iPhoneSimulator.platform/Developer/usr/lib"),
            "-module-cache-path", str(SCRATCH / "module-cache"), "-module-name", "MixerSettingsDiagnostic"]
    argv += [str(SCRATCH / name) for name in names]
    version = subprocess.run([str(SWIFT), "--version"], capture_output=True, timeout=15)
    assert version.returncode == 0
    started = datetime.datetime.now(datetime.timezone.utc)
    child = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    signals = []
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        timed_out = True
        if group_members(child.pid):
            os.killpg(child.pid, signal.SIGTERM)
            signals.append("SIGTERM")
        try:
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if group_members(child.pid):
                os.killpg(child.pid, signal.SIGKILL)
                signals.append("SIGKILL")
            stdout, stderr = child.communicate(timeout=5)
    (OUT / "typecheck.stdout").write_bytes(stdout)
    (OUT / "typecheck.stderr").write_bytes(stderr)
    empty = not group_members(child.pid)
    assert all(sha(SCRATCH / name) == expected for name, expected in source.items())
    assert all(sha(PRODUCER / "derivative" / name) == source[name] for name in names if name != "PublicSwitchSelection.swift")
    receipt = {"schema": 1, "startedUTC": started.isoformat(), "endedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "sourceRevisionContext": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
               "producerHandoffSHA256": sha(PRODUCER / "handoff.json"), "reviewHandoffSHA256": sha(REVIEW / "handoff.json"),
               "producerMembersVerified": 26, "reviewMembersVerified": 9, "sourceFiles": source,
               "command": argv, "exitCode": child.returncode, "timeoutSeconds": 90, "timedOut": timed_out,
               "ownedPID": child.pid, "ownedPGID": child.pid, "processGroupEmpty": empty, "signalsSent": signals,
               "stdoutSHA256": sha(OUT / "typecheck.stdout"), "stderrSHA256": sha(OUT / "typecheck.stderr"),
               "rawStreamEOFConfirmed": empty, "swiftSHA256": sha(SWIFT), "swiftVersion": version.stdout.decode(),
               "swiftVersionStderr": version.stderr.decode(), "fullUIKitXCTestTypecheckPassed": child.returncode == 0 and not timed_out,
               "nativeRuntimeExecuted": False, "deviceQuery": False, "nativeRetrySelected": False, "gaAccepted": False}
    save("typecheck-receipt.json", receipt)
    assert empty, "Owned process group is not empty; preserve scratch"
    info = SCRATCH.stat()
    holders = subprocess.run(["/usr/sbin/lsof", "-nP", "+D", str(SCRATCH)], capture_output=True, timeout=30)
    (OUT / "holders.stdout").write_bytes(holders.stdout)
    (OUT / "holders.stderr").write_bytes(holders.stderr)
    assert holders.returncode == 1 and not holders.stdout and not holders.stderr
    assert (SCRATCH.stat().st_dev, SCRATCH.stat().st_ino) == (info.st_dev, info.st_ino)
    removed_bytes = sum(path.stat().st_size for path in SCRATCH.rglob("*") if path.is_file())
    shutil.rmtree(SCRATCH)
    save("cleanup.json", {"ownedScratchRemoved": not SCRATCH.exists(), "removedBytes": removed_bytes,
                          "holderExitCode": holders.returncode, "processGroupEmpty": empty, "signalsSent": signals,
                          "nativeRuntimeExecuted": False, "otherProjectsChanged": False})
    print(json.dumps({"fullUIKitXCTestTypecheckPassed": receipt["fullUIKitXCTestTypecheckPassed"], "exitCode": child.returncode,
                      "ownedScratchRemoved": not SCRATCH.exists(), "processGroupEmpty": empty, "sourceFiles": len(source)}))


if __name__ == "__main__":
    main()

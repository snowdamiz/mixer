#!/usr/bin/env python3
"""Record the actual host deadline fix independently of derived review probes."""
import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capabilities/verification/host-deadline"
APPLE = "/Applications/Xcode.app/Contents/Developer"
EXPECTED_HOST = "21e1580d078e026f0cbb2fa9f1983fc54d08b196feaf67785fcd889eb89caacd"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source():
    paths = [ROOT / "sdk/Package.swift", ROOT / "capabilities/Package.swift"]
    for folder in ["sdk/Sources", "sdk/Tests", "capabilities/Tests", "capabilities/Probe", "capabilities/GuestTransportProbe", "capabilities/tools", "capabilities/schema", "capabilities/java"]:
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(set(paths))]


def main():
    OUT.mkdir(exist_ok=True)
    before = source()
    if sha((ROOT / "sdk/Sources/MixerCapabilities/Host.swift").read_bytes()) != EXPECTED_HOST:
        raise RuntimeError("Host differs from independently tested candidate")
    previous = json.loads((ROOT / "capabilities/verification/guest-transport-codec/receipt.json").read_text())
    commands = []

    def run(name, command, environment=None, scope=""):
        start = time.monotonic()
        env = dict(os.environ, DEVELOPER_DIR=APPLE)
        env.update(environment or {})
        print("Started " + name, flush=True)
        proc = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        path = OUT / (name + ".log")
        path.write_bytes(proc.stdout)
        item = {"name": name, "command": command, "environment": {"DEVELOPER_DIR": env["DEVELOPER_DIR"], **(environment or {})},
                "exitCode": proc.returncode, "elapsedSeconds": round(time.monotonic() - start, 3),
                "output": str(path.relative_to(ROOT)), "outputSHA256": sha(proc.stdout), "scope": scope}
        counts = re.findall(rb"Test run with (\d+) tests? .*passed", proc.stdout)
        if counts:
            item["passedTests"] = int(counts[-1])
        print(f"Finished {name}: exit{proc.returncode}" + (f", {item['passedTests']} tests" if "passedTests" in item else ""), flush=True)
        return item

    for name, command in [("swift-version", ["swift", "--version"]), ("xcode-version", ["xcodebuild", "-version"]),
                          ("host-version", ["uname", "-a"]), ("python-version", ["python3", "--version"]),
                          ("generator-check", ["python3", "capabilities/tools/generate.py", "--check"])]:
        commands.append(run(name, command))
    jobs = [
        ("capability-debug", ["swift", "test", "--package-path", "capabilities", "--scratch-path", "capabilities/.build/exit-debug", "-Xswiftc", "-warnings-as-errors"], {}, "Full native/legacy/new transport plus real public actor-delay regression"),
        ("capability-release", ["swift", "test", "--package-path", "capabilities", "--scratch-path", "capabilities/.build/exit-release", "-c", "release", "-Xswiftc", "-warnings-as-errors"], {}, "Same suite under optimization"),
        ("native-deadline-tsan", ["swift", "test", "--package-path", "capabilities", "--scratch-path", "capabilities/.build/exit-tsan", "--sanitize", "thread", "--filter", "NativeCapabilityExitTests|NativeHTTPTransportTests|CapabilityHostDeadlineTests"], {}, "Owned native HTTP, exit join and actual public actor-delay tests under Thread Sanitizer"),
    ]
    for name in ["ios-cross-build", "android-cross-build", "wasi-module-build"]:
        old = next(c for c in previous["commands"] if c["name"] == name)
        jobs.append((name, old["command"], old["environment"], old["scope"]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run, *job) for job in jobs]
        for future in futures:
            commands.append(future.result())
    after = source()
    passed = before == after and all(c["exitCode"] == 0 for c in commands)
    canonical = json.dumps(before, sort_keys=True, separators=(",", ":")).encode()
    receipt = {
        "schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "baselineRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "source": {"digest": sha(canonical), "algorithm": "SHA256 of sorted compact JSON source entries", "files": before},
        "sourceUnchangedDuringRun": before == after, "hostMatchesIndependentlyTestedCandidateSHA256": EXPECTED_HOST,
        "runnerSHA256": sha(Path(__file__).read_bytes()), "commands": commands, "passed": passed,
        "independentDerivedReview": "verification/capability-deadline-review/receipt.json",
        "priorTestHarnessCompileFailure": "capabilities/verification/host-deadline/initial-test-compile-failure.json",
        "behavior": ["Absolute monotonic deadline captured before work scheduling", "Pre-invoke expiry rejects without adapter call and supplies no-I/O native exit fact", "Result selection rechecks expiry independently of watchdog scheduling", "Timely first terminal remains immutable and installed capacity still waits for both exit facts"],
        "limitations": ["No hard real-time guarantee; suspension after pre-invoke check can still precede I/O", "Cancellation/deadline cannot roll back committed effects", "Public regression deliberately stalls a delivery callback to delay the host actor", "Independent review uses documented captured-source gates, not an unmodified scheduler exploit", "Cross-builds do not execute on devices; no C/guest bridge, release/activation, FieldLog package or GA qualification"]
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if not passed:
        raise SystemExit("Qualification failed; outputs and receipt retained")
    print(json.dumps({"passed": passed, "sourceFiles": len(before), "sourceDigest": sha(canonical)}), flush=True)


if __name__ == "__main__":
    main()

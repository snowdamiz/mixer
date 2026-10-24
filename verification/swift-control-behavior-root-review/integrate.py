#!/usr/bin/env python3
"""Root's one-time exact-source integration and host smoke collector."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PRODUCER = ROOT / "verification/swift-control-behavior-implementation"
REVIEW = ROOT / "verification/swift-control-behavior-review"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def save(name, value):
    (OUT / name).write_bytes(encoded(value))


def source():
    vm = ROOT / "vm"
    paths = [vm / "Cargo.toml", vm / "Cargo.lock"]
    for directory in ["src", "tests", "include"]:
        paths += sorted(p for p in (vm / directory).rglob("*") if p.is_file())
    return {str(p.relative_to(vm)): sha(p) for p in paths}


assert not (OUT / "integration.json").exists(), "one-time collector"
baseline = json.loads((PRODUCER / "baseline-manifest.json").read_text())
expected = json.loads((PRODUCER / "source-manifest.json").read_text())
assert source() == baseline, "live VM drift; do not overwrite"
bindings = {}
for packet in [PRODUCER, REVIEW]:
    seal = json.loads((packet / "seal.json").read_text())
    for name, digest in seal["files"].items():
        path = packet / name
        assert sha(path) == digest, str(path)
        bindings[str(path.relative_to(ROOT))] = digest
    for name, digest in seal.get("externalBindings", {}).items():
        assert sha(ROOT / name) == digest, name
        bindings[name] = digest
    bindings[str((packet / "seal.json").relative_to(ROOT))] = sha(packet / "seal.json")
    check = subprocess.run([sys.executable, "-B", str(packet / "verify.py")], cwd=ROOT, capture_output=True)
    (OUT / (packet.name + "-offline.log")).write_bytes(check.stdout + check.stderr)
    assert check.returncode == 0
assert json.loads((REVIEW / "findings.json").read_text())["unresolvedFindings"] == []
save("accepted-input-bindings.json", bindings)
save("before-integration.json", {
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "baseline": hashlib.sha256(encoded(baseline)).hexdigest(),
    "acceptedCandidate": hashlib.sha256(encoded(expected)).hexdigest(),
    "patchSHA256": sha(PRODUCER / "source.patch"),
    "boundEvidenceFiles": len(bindings),
    "sourceReview": [
        "Shared macro bodies preserve Frozen expansions and reservation.",
        "Private helper operates original phase/frame/control/value owners; no new owner or public dispatcher.",
        "Current frame floors, sentinel and decoded targets are checked before relevant control mutation.",
        "Actual post-pop removal failure retains first failure and latches unreconciled cleanup debt.",
        "Work-prefix, cancellation, deepest retained pins and completion barriers have independent executable probes.",
        "Production candidate2 accounting unchanged; test-only hook supplement is separately enumerated and measured.",
    ],
})
patch_args = ["git", "apply", "--directory=vm", str(PRODUCER / "source.patch")]
subprocess.run(patch_args[:2] + ["--check"] + patch_args[2:], cwd=ROOT, check=True)
subprocess.run(patch_args, cwd=ROOT, check=True)
assert source() == expected
save("integrated-source-manifest.json", source())
scratch = Path(tempfile.mkdtemp(prefix="mixer-control-root-", dir="/private/tmp"))
env = dict(os.environ, PATH="/opt/homebrew/opt/rustup/bin:" + os.environ["PATH"], CARGO_TARGET_DIR=str(scratch / "target"))
for name in ["RUSTFLAGS", "RUSTC_BOOTSTRAP"]:
    env.pop(name, None)
commands = [
    ["rustc", "--version", "--verbose"],
    ["cargo", "--version"],
    ["cargo", "test", "--lib", "--locked", "--offline", "--all-features", "--release", "experimental_swift_reactor::execution::", "--", "--nocapture", "--test-threads=1"],
    ["cargo", "test", "--test", "span_control_extraction", "--locked", "--offline", "--all-features", "--release", "--", "--nocapture", "--test-threads=1"],
]
results = []
try:
    for index, args in enumerate(commands):
        assert source() == expected
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(args, cwd=ROOT / "vm", env=env, capture_output=True)
        name = f"integration-{index}.log"
        (OUT / name).write_bytes(result.stdout + result.stderr)
        results.append({"argv": args, "cwd": str(ROOT / "vm"), "startedUTC": start, "finishedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "exitCode": result.returncode, "output": name, "outputSHA256": sha(OUT / name), "sourceDigest": hashlib.sha256(encoded(expected)).hexdigest()})
        save("integration-commands.json", results)
        assert result.returncode == 0, name
        if index in [2, 3]:
            count = 46 if index == 2 else 6
            assert f"test result: ok. {count} passed; 0 failed; 0 ignored;" in result.stdout.decode()
        print(f"passed {index}: {' '.join(args)}", flush=True)
    assert source() == expected
finally:
    shutil.rmtree(scratch)
    save("integration-cleanup.json", {"ownedScratch": str(scratch), "removed": not scratch.exists(), "nativeInstancesStarted": 0, "physicalRuns": 0, "otherProjectProcessesModified": False})
save("integration.json", {"schema": 1, "status": "exact-private-control-overlay-integrated-host-smoke-passed", "commands": len(results), "sourceDigest": hashlib.sha256(encoded(expected)).hexdigest(), "sourceFiles": len(expected), "rootTests": {"frameValueControl": 46, "frozenParity": 6, "configuration": "all features Release, serial"}, "scope": "Exact accepted source integration and two host smoke suites. Independent four-mode/full-library/layout evidence is separate. No full dispatcher, Ready, public invoke, native, physical, provider or GA acceptance."})

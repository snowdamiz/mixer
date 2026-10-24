#!/usr/bin/env python3
"""Independent source-bound scratch collector; never starts the hosted application."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STATE = OUT / "state.json"

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2) + "\n")

def setup():
    producer_path = ROOT / "verification/hosted-key-owner-implementation/receipt.json"
    receipt = json.loads(producer_path.read_text())
    assert sha(producer_path) == "a9a6f27494a4b6af7452f0300f7b62f5942af69c0f73e128462a065f28986286"
    checks = {path: sha(ROOT / path) == digest for path, digest in receipt["bindings"].items()}
    assert len(checks) == 205 and all(checks.values()), [p for p, valid in checks.items() if not valid]
    src = json.loads((ROOT / "verification/hosted-key-owner-implementation/source-manifest.json").read_text())["files"]
    digest = hashlib.sha256(json.dumps(src, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == receipt["sourceTreeDigest"] == "a6e39fe48602d9044a43d4f3e617292fe19418856006f713d914487945577aee"
    pure = json.loads((ROOT / "verification/hosted-token-verifier/source-manifest.json").read_text())["files"]
    assert all(sha(ROOT / p["path"]) == p["sha256"] for p in pure)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-key-owner-independent-", dir="/private/tmp"))
    shutil.copytree(ROOT / "hosted", scratch / "hosted", ignore=shutil.ignore_patterns("_build"))
    (scratch / "verification/hosted-key-owner-implementation").mkdir(parents=True)
    dependencies = {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / "hosted/deps").rglob("*")) if p.is_file() and "_build" not in p.parts}
    assert all(sha(scratch / path) == value for path, value in src.items())
    assert all(sha(scratch / path) == value for path, value in dependencies.items())
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    save("input-validation.json", {"producerReceiptSHA256": sha(producer_path), "producerBindingsVerified": len(checks),
         "sourceRevision": revision, "sourceTreeDigest": digest, "sourceFiles": src, "acceptedPureVerifierFilesVerified": pure,
         "dependencyFiles": dependencies, "dependenciesTreeDigest": hashlib.sha256(json.dumps(dependencies, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
         "selectedMintVersion": "1.11.0", "scratch": str(scratch), "allCopiedSourceAndDependencyHashesMatch": True})
    save("state.json", {"scratch": str(scratch), "commands": [], "fixtureDirectoriesBefore": [str(p) for p in Path("/private/tmp").glob("mixer-key-owner-tls-*")]})
    print(scratch)

def run(label, argv, prod=False):
    state = json.loads(STATE.read_text())
    scratch = Path(state["scratch"])
    env = dict(os.environ, MIX_ENV="prod" if prod else "test", MIX_BUILD_PATH=str(scratch / ("prod-build" if prod else "build")))
    started = time.monotonic()
    with (OUT / (label + ".log")).open("w") as log:
        try:
            result = subprocess.run(argv, cwd=scratch / "hosted", env=env, stdout=log, stderr=subprocess.STDOUT, timeout=300)
            status = {"exitCode": result.returncode}
        except subprocess.TimeoutExpired:
            status = {"timeoutSeconds": 300}
    state["commands"].append({"label": label, "argv": argv, "cwd": str(scratch / "hosted"),
         "environment": {k: env[k] for k in ["MIX_ENV", "MIX_BUILD_PATH"]}, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "elapsedSeconds": time.monotonic() - started, "output": label + ".log", "outputSHA256": sha(OUT / (label + ".log")), **status})
    save("state.json", state)
    print(json.dumps(state["commands"][-1]))

def cleanup():
    state = json.loads(STATE.read_text())
    scratch = Path(state["scratch"])
    src = json.loads((OUT / "input-validation.json").read_text())
    checks = {p: sha(ROOT / p) == digest for p, digest in src["sourceFiles"].items()}
    scratch_checks = {p: sha(scratch / p) == digest for p, digest in src["sourceFiles"].items()}
    dependency_checks = {p: sha(scratch / p) == digest and sha(ROOT / p) == digest for p, digest in src["dependencyFiles"].items()}
    producer = json.loads((ROOT / "verification/hosted-key-owner-implementation/receipt.json").read_text())
    producer_checks = {p: sha(ROOT / p) == digest for p, digest in producer["bindings"].items()}
    test_source_matches = sha(OUT / "adversarial_test.exs") == sha(scratch / "hosted/test/mixer_hosted/identity/independent_adversarial_test.exs")
    artifacts = scratch / "verification/hosted-key-owner-implementation"
    if artifacts.exists(): shutil.copytree(artifacts, OUT / "replayed-producer-artifacts", dirs_exist_ok=True)
    shutil.rmtree(scratch)
    new_keys = set(str(p) for p in Path("/private/tmp").glob("mixer-key-owner-tls-*")) - set(state["fixtureDirectoriesBefore"])
    save("cleanup.json", {"scratchRemoved": not scratch.exists(), "sourceUnchanged": all(checks.values()),
        "scratchProductSourceUnchanged": all(scratch_checks.values()), "dependencySourceUnchanged": all(dependency_checks.values()),
        "producerBindingsReverified": len(producer_checks), "producerPacketUnchanged": all(producer_checks.values()),
        "executedIndependentTestSourceMatchesDelivered": test_source_matches, "newFixtureKeyDirectoriesRetained": sorted(new_keys),
        "scope": "Owned scratch/build and test fixtures only; unrelated processes and instances untouched"})

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["setup", "run", "cleanup"])
    p.add_argument("--label")
    p.add_argument("--prod", action="store_true")
    p.add_argument("argv", nargs=argparse.REMAINDER)
    a = p.parse_args()
    if a.action == "setup": setup()
    elif a.action == "cleanup": cleanup()
    else: run(a.label, a.argv[1:] if a.argv[:1] == ["--"] else a.argv, a.prod)

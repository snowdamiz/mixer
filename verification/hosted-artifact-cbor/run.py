#!/usr/bin/env python3
"""Qualify only this hosted codec slice over an explicit committed baseline."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--base", required=True)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
overrides = [
    "hosted/lib/mixer_hosted/protocol/artifact_cbor.ex",
    "hosted/test/mixer_hosted/protocol/artifact_cbor_test.exs",
    "hosted/scripts/test-local.py",
    ".github/workflows/hosted.yml",
    "docs/hosted-artifact-cbor.md",
    "verification/hosted-artifact-cbor/run.py",
]
base = subprocess.check_output(["git", "rev-parse", args.base], cwd=root, text=True).strip()
scratch = Path(tempfile.mkdtemp(prefix="mixer-artifact-cbor-", dir="/private/tmp")).resolve()
commands = []
status = "failed"
inputs = {}
changes = {}
cleanup = {}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(label, argv, cwd, env=None, timeout=300):
    log = output / (label + ".log")
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with log.open("wb") as stream:
        try:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            stream.write(b"\nCOLLECTOR: timeout\n")
            code = 124
    commands.append({"label": label, "argv": argv, "cwd": str(cwd), "started": started,
                     "exitCode": code, "output": log.name, "sha256": digest(log.read_bytes())})
    if code:
        raise RuntimeError(f"{label}: exit {code}")


try:
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", base, "hosted", "services"],
        cwd=root, text=True).splitlines()
    for name in names:
        data = subprocess.check_output(["git", "show", f"{base}:{name}"], cwd=root)
        path = scratch / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        inputs[name] = digest(data)
    for name in overrides:
        data = (root / name).read_bytes()
        path = scratch / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        inputs[name] = digest(data)
        changes[name] = digest(data)

    # Give the nested collector a real local snapshot revision without copying
    # any user's Git metadata, uncommitted identity lane or credentials.
    run("snapshot-init", ["git", "init", "--quiet"], scratch)
    run("snapshot-stage", ["git", "add", "--all"], scratch)
    run("snapshot-commit", ["git", "-c", "user.name=Mixer Verification",
         "-c", "user.email=verification@example.invalid", "-c", "commit.gpgsign=false",
         "commit", "--quiet", "-m", "Isolated artifact CBOR qualification inputs"], scratch)
    with tarfile.open(output / "source.tar.gz", "w:gz") as archive:
        for name in sorted(inputs):
            archive.add(scratch / name, arcname=name, recursive=False)

    shutil.copytree(root / "hosted/deps", scratch / "hosted/deps")
    run("elixir-version", ["elixir", "--version"], scratch)
    run("mix-version", ["mix", "--version"], scratch)
    run("go-version", ["go", "version"], scratch)
    run("locked-dependencies", ["mix", "deps.get", "--check-locked"], scratch / "hosted")
    run("go-shared-vectors", ["go", "test", "./protocol", "-count=1", "-v", "-run",
         "^(TestV3SharedCanonicalAndSignatureVector|TestCanonicalRFC8949Subset)$"],
        scratch / "services")
    run("hosted", ["python3", "scripts/test-local.py", "--output", str(output / "host")],
        scratch / "hosted", timeout=900)
    if any(digest((scratch / p).read_bytes()) != sha for p, sha in inputs.items()):
        raise RuntimeError("isolated input changed during qualification")
    if any(digest((root / p).read_bytes()) != sha for p, sha in changes.items()):
        raise RuntimeError("owned live input changed during qualification")
    status = "passed"
finally:
    # The nested collector owns/stops its PostgreSQL fixture; do not remove an
    # unfinished fixture if its own failure receipt reports unsuccessful stop.
    host_receipt = output / "host/receipt.json"
    nested_clean = host_receipt.exists() and json.loads(host_receipt.read_text())["cleanup"].get("postgres_stopped") is True
    cleanup["nested_postgres_stopped"] = nested_clean
    if nested_clean or not (output / "host").exists():
        shutil.rmtree(scratch)
        cleanup["scratch_removed"] = not scratch.exists()
    else:
        cleanup["scratch_removed"] = False
        status = "failed"
    archive = output / "source.tar.gz"
    receipt = {
        "schema": 1, "status": status, "baseRevision": base,
        "sourceInputs": inputs, "liveOverrides": changes,
        "sourceTreeSHA256": digest(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()),
        "sourceArchiveSHA256": digest(archive.read_bytes()) if archive.exists() else None,
        "commands": commands, "cleanup": cleanup,
        "scope": "Elixir bounded artifact CBOR and existing shared Go wire/signature vectors, plus the accepted hosted foundation/identity suite. Isolated baseline deliberately excludes concurrent key-owner additions and the pending Mint dependency pin.",
        "limitations": ["No artifact schema/root/payload admission or authorization route.",
                        "No hosted provider, membership/persistence, audit or cloud qualification.",
                        "No phone/simulator runtime or GA gate qualification."]}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": status, "receipt": str(output / "receipt.json"), "cleanup": cleanup}))

#!/usr/bin/env python3
"""Independent bounded custody checks. No product code is executed."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "verification/android-private-owner-effect-integration-proposal"
EXPECTED = "7547220cc7f1ba6648ca2cbb3fdf96e402b5b3af9abf68906263be57688838a7"
ACCEPTANCE = "verification/android-environment-observer-root-review/implementation-acceptance.json"
ACCEPTANCE_HASH = "ca6616f73fb7c342a3a74747c571c29f78ab3b6dacf7c3227375a6807295c022"

def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def read(path):
    if path.is_symlink() or not path.is_file():
        raise AssertionError(f"not a regular nonsymlink file: {path}")
    return path.read_bytes()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

def command(argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15, check=False)
    if result.returncode:
        raise AssertionError(f"command failed: {argv}: {result.stderr!r}")
    return {"argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
            "stdout": result.stdout.decode(), "stderr": result.stderr.decode()}

def capture():
    raw_manifest = read(UPSTREAM / "manifest.json")
    assert identity(raw_manifest)["sha256"] == EXPECTED
    manifest = json.loads(raw_manifest)
    receipt = json.loads(read(UPSTREAM / "receipt.json"))
    assert len(manifest["files"]) == 36
    assert sum(v["bytes"] for v in manifest["files"].values()) == 606635
    assert len(receipt["inputs"]) == 25
    captured = {}
    for name, expected in sorted(manifest["files"].items()):
        path = Path(name)
        assert not path.is_absolute() and ".." not in path.parts
        data = read(ROOT / path)
        assert identity(data) == expected, name
        target = OUT / "frozen-proposal" / path
        write(target, data)
        captured[str(target.relative_to(OUT))] = identity(data)
    target = OUT / "frozen-proposal/manifest.json"
    write(target, raw_manifest)
    captured[str(target.relative_to(OUT))] = identity(raw_manifest)
    drift = []
    for name, expected in sorted(receipt["inputs"].items()):
        data = read(ROOT / name)
        target = OUT / "current-inputs" / name
        write(target, data)
        captured[str(target.relative_to(OUT))] = identity(data)
        if identity(data) != expected:
            drift.append({"path": name, "frozen": expected, "current": identity(data)})
    assert [v["path"] for v in drift] == ["PLAN.md"]
    acceptance = read(ROOT / ACCEPTANCE)
    assert identity(acceptance)["sha256"] == ACCEPTANCE_HASH
    target = OUT / "current-inputs" / ACCEPTANCE
    write(target, acceptance)
    captured[str(target.relative_to(OUT))] = identity(acceptance)
    commands = [command(["git", "rev-parse", "HEAD"]),
                command(["git", "rev-parse", "HEAD^{tree}"]),
                command(["git", "--version"]),
                command(["git", "status", "--short", "--untracked-files=no", "--", *receipt["inputs"]])]
    python = Path(sys.executable).resolve()
    git = Path(shutil.which("git")).resolve()
    projection = hashlib.sha256(json.dumps(captured, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    report = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [str(python), "-B", str(Path(__file__).resolve()), "capture"],
        "commands": commands, "tools": {"python": {"path": str(python), "version": sys.version, **identity(read(python))},
        "git": {"path": str(git), "version": commands[2]["stdout"].strip(), **identity(read(git))}},
        "context_revision": commands[0]["stdout"].strip(), "context_tree": commands[1]["stdout"].strip(),
        "proposal_manifest_sha256": EXPECTED, "proposal_members": 36, "proposal_bytes": 606635,
        "proposal_inputs": 25, "relevant_current_inputs_unchanged": 24, "context_drift": drift,
        "observer_acceptance_sha256": ACCEPTANCE_HASH, "captured": captured,
        "selected_projection_sha256": projection, "full_repository_tree_snapshot": False,
        "scope": "Independent source custody only; no producer checker or product implementation executed.",
        "product_tests_run": False, "cross_compilation_run": False, "native_runtime_started": False,
        "computer_use_or_capture": False, "network_install_signing_credentials_publication": False,
        "process_discovery": False, "product_or_metadata_edits": False,
        "cleanup": "No scratch or native instances were created; no other project processes or data touched."}
    (OUT / "custody.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "source-custody-pass", "members": 36, "bytes": 606635,
                     "inputs": 25, "unchanged": 24, "context_only_drift": [v["path"] for v in drift]}))

def check():
    report = json.loads(read(OUT / "custody.json"))
    for name, expected in report["captured"].items():
        assert identity(read(OUT / name)) == expected, name
    assert report["selected_projection_sha256"] == hashlib.sha256(json.dumps(
        report["captured"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(json.dumps({"status": "frozen-custody-pass", "frozen_files": len(report["captured"]),
                      "scope": "source-only; not product tests or implementation acceptance"}))

if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in ("capture", "check")
    {"capture": capture, "check": check}[sys.argv[1]]()

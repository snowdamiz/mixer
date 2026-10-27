#!/usr/bin/env python3
"""Run only independent finite Python/File controls and verify frozen inputs."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PREP = HERE.parent / "swift-guarded-snapshot-export-preparation"
EXPECTED_SOURCE = "9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb"
EXPECTED_SEAL = "7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe"
ACCEPTANCE = HERE.parent / "swift-semantic-adapter-root-review/selected-adoption-host-acceptance.json"
DIRECTION = HERE.parent / "swift-semantic-adapter-root-review/guarded-snapshot-export-admission-proposal-direction.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def source_review():
    # Navigation/excerpt evidence only. No text match authorizes a release.
    selected = {
        "src/experimental_swift_reactor/control.rs": [
            (400, 420, "actual control ownership"),
            (550, 588, "original foundation source roles"),
            (822, 833, "cloning cancellation accessor and actual deadline"),
            (890, 949, "terminal interruption and immutable first-failure semantics"),
            (1120, 1168, "terminal construction enlargement"),
            (1186, 1238, "consuming actual phase storage then narrowing"),
            (1435, 1485, "terminal work debit and checked ExecutionWork"),
            (1739, 1812, "actual single-floor final cleanup"),
        ],
        "src/experimental_swift_reactor/cache/initial_profile_v1.rs": [
            (25, 47, "private sole guard type and eight exact outcomes"),
            (66, 106, "original complete wrapper ingress/caller/move places"),
            (125, 175, "original order and sole guard literal"),
            (187, 248, "actual original inspection"),
        ],
        "src/execute.rs": [(7, 16, "actual immutable shared atomic cancellation read")],
        "src/experimental_swift_reactor/diagnostic_profile.rs": [
            (127, 139, "actual row File admission"),
            (148, 184, "original continuous 4096-byte block and 32-call discipline"),
        ],
        "src/experimental_swift_reactor/retained_profile_loader_v1.rs": [
            (193, 202, "retained actual File identity fields"),
            (569, 589, "actual File metadata device/inode derivation"),
        ],
    }
    rows = []
    for relative, facts in selected.items():
        path = PREP / "inputs/accepted-source/vm" / relative
        lines = path.read_text().splitlines()
        rows.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path),
                     "facts": [{"start": start, "end": end, "role": role,
                                "source": "\n".join(lines[start-1:end])}
                               for start, end, role in facts]})
    dump(HERE / "source-review.json", {"scope": "accepted source navigation/excerpts and independent semantic review, not syntax-only authorization", "sources": rows})


def main():
    previous_attempts = [int(path.name.removeprefix("attempt-"))
                         for path in (HERE / "commands").glob("attempt-*")]
    original = 1 if (HERE / "commands/independent-controls/receipt.json").exists() else 0
    attempt = max([original, *previous_attempts], default=0) + 1
    if attempt == 2 and original:
        for name in ["pre-release-receipt", "input-verification"]:
            source_path = HERE / f"{name}.json"
            historical_path = HERE / f"{name}-attempt-1.json"
            if source_path.exists() and not historical_path.exists():
                shutil.copyfile(source_path, historical_path)
    commands = []
    inputs = {}
    for filename in ["README.md", "requirements.md", "admission_model.py", "test_controls.py", "run_controls.py"]:
        inputs[filename] = sha(HERE / filename)
    source = json.loads((PREP / "inputs/source-manifest.json").read_text())
    assert source["member_count"] == 144 and source["tree_sha256"] == EXPECTED_SOURCE
    for row in source["members"]:
        path = PREP / "inputs/accepted-source/vm" / row["path"]
        assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], row["path"]
    assert sha(PREP / "seal.json") == EXPECTED_SEAL
    sealed = json.loads((PREP / "seal.json").read_text())
    assert sealed["member_count"] == 639
    for row in sealed["members"]:
        path = PREP / row["path"]
        assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], row["path"]
    assert sha(ACCEPTANCE) == "635696d0f95e7adf231095ca05a223d47f0353c563b63f60ab242e9cf7bc2697"
    assert sha(DIRECTION) == "26dd7ba06c216978b94c1aed9378a9065a91d6c5ec78d3239d3bf0d706c68dc7"
    source_review()
    inputs["../swift-guarded-snapshot-export-preparation/seal.json"] = sha(PREP / "seal.json")
    inputs["../swift-semantic-adapter-root-review/selected-adoption-host-acceptance.json"] = sha(ACCEPTANCE)
    inputs["../swift-semantic-adapter-root-review/guarded-snapshot-export-admission-proposal-direction.json"] = sha(DIRECTION)
    dump(HERE / "input-verification.json", {
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "accepted_source_members_verified": 144,
        "accepted_source_tree_sha256": EXPECTED_SOURCE,
        "historical_preparation_members_verified": 639,
        "historical_preparation_seal_sha256": EXPECTED_SEAL,
        "source_facts": "actual accepted-source; historical proposal not treated as implementation",
        "active_producer_design_read": False,
        "active_wire_correction_read": False,
        "inputs": inputs,
    })
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    invocations = [
        ("python-version", [sys.executable, "--version"]),
        ("rust-version-only", ["/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc", "--version"]),
        ("source-revision-context", ["git", "rev-parse", "HEAD"]),
        ("independent-controls", [sys.executable, "-m", "unittest", "-v", "test_controls"]),
    ]
    for name, argv in invocations:
        folder = HERE / "commands" / f"attempt-{attempt}" / name
        folder.mkdir(parents=True, exist_ok=True)
        started = datetime.datetime.now(datetime.timezone.utc)
        result = subprocess.run(argv, cwd=HERE, env=env, capture_output=True, timeout=45)
        (folder / "stdout").write_bytes(result.stdout)
        (folder / "stderr").write_bytes(result.stderr)
        receipt = {"name": name, "argv": argv, "cwd": str(HERE), "exit_code": result.returncode,
                   "started": started.isoformat(), "ended": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "source_inputs": inputs, "accepted_source_tree_sha256": EXPECTED_SOURCE,
                   "stdout_sha256": sha(folder / "stdout"), "stderr_sha256": sha(folder / "stderr"),
                   "scope": "bounded independent model and temporary host regular Files; no Rust compile or original wrapper",
                   "expectation_met": result.returncode == 0}
        dump(folder / "receipt.json", receipt)
        commands.append({"name": name, "receipt_sha256": sha(folder / "receipt.json"), "expectation_met": receipt["expectation_met"]})
        print(json.dumps({"name": name, "exit_code": result.returncode, "stdout": result.stdout.decode(errors="replace"), "stderr": result.stderr.decode(errors="replace")}))
    passed = all(row["expectation_met"] for row in commands)
    dump(HERE / "pre-release-receipt.json", {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "independent-requirements-and-controls-prepared-awaiting-root-producer-release" if passed else "independent-control-failure",
        "attempt": attempt, "commands": commands, "all_expectations_met": passed,
        "independent_model_and_host_file_test_methods": 25,
        "producer_read_or_accepted": False, "source_measured_or_compiled": False,
        "canonical_product_changed": False, "GA_gates_verified": 0,
        "limits": ["Synthetic pure model is not Rust behavior or layout evidence", "No working writer or new grant selected", "Producer review awaits root exact freeze release", "Native/device/simulator/emulator/UI/capture/process inventories paused"],
        "cleanup": {"temporary_files": "TemporaryDirectory removed on exit", "new_processes_persistent": False, "no_compiler_scratch": True, "pycache_disabled": True},
    })
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Seal only the selected host-core implementation and its small receipts."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
OWNED = ["native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java",
         "native/android/tests/OwnerLifecycleV2HostTests.java",
         "native/android/tests/run-owner-core-host.py", "docs/android-public-owner-core.md"]
SELECTION = "verification/android-public-owner-root-review/implementation-selection.json"
SELECTION_HASH = "763f049c2c95a006874d78ad5cd473d19fc147482c952bbd0725348e7609d5a9"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(name, value):
    (PACKET / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    if (PACKET / "manifest.json").exists():
        raise SystemExit("Frozen implementation exists; preserve it")
    selection = (ROOT / SELECTION).read_bytes()
    assert identity(selection)["sha256"] == SELECTION_HASH
    selected = json.loads(selection)
    original = json.loads((ROOT / "verification/android-public-owner-contract/source-bindings.json").read_bytes())
    profile = {name: {key: value[key] for key in ("bytes", "sha256")}
               for name, value in original["files"].items() if "profile_group" in value}
    assert len(profile) == 42
    for path, expected in profile.items():
        assert identity((ROOT / path).read_bytes()) == expected, path
    implementation = {path: identity((ROOT / path).read_bytes()) for path in OWNED}
    binding = {"implementation": implementation, "unchanged_source_pair_1": profile,
               "root_selection": {"path": SELECTION, **identity(selection)},
               "selected_proposal_manifest_sha256": selected["contract_manifest_sha256"]}
    digest = hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write("source-bindings.json", {**binding, "tree_sha256": digest,
                                   "tree_algorithm": "sha256 of compact sorted-key UTF-8 JSON without tree fields"})
    final = PACKET / "attempts/final"
    run = json.loads((final / "receipt.json").read_bytes())
    assert run["status"] == "pass" and run["test_result"]["tests"] == 22
    inputs = json.loads((final / "source-bindings.json").read_bytes())
    for path in OWNED[:2]:
        assert {key: inputs["sources"][path][key] for key in ("bytes", "sha256")} == implementation[path]
    assert inputs["runner"] == implementation[OWNED[2]]
    cleanup = {}
    for name in ("first", "final"):
        attempt = PACKET / "attempts" / name
        value = json.loads((attempt / "cleanup.json").read_bytes())
        assert value["removed"] and value["owned_children_waited"] and not (attempt / "scratch").exists()
        cleanup[name] = value
    commands = []
    checks = [["git", "rev-parse", "HEAD"], ["git", "--version"]]
    checks += [["git", "diff", "--no-index", "--check", "/dev/null", path] for path in OWNED]
    for argv in checks:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        commands.append({"argv": argv, "exit_code": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
        if argv[1] == "diff":
            assert result.returncode == 1 and not result.stdout and not result.stderr, argv
        else:
            assert result.returncode == 0, argv
    scripts = [ROOT / OWNED[2], PACKET / "freeze.py", PACKET / "verify.py"]
    for path in scripts:
        ast.parse(path.read_text(), filename=str(path))
    json_paths = sorted(PACKET.rglob("*.json"))
    for path in json_paths:
        json.loads(path.read_bytes())
    write("checks.json", {"commands": commands, "python_syntax_files": len(scripts),
                          "json_files_before_checks_receipt_manifest": len(json_paths),
                          "status": "pass", "scope": "format, new-file whitespace and source identity only"})
    write("receipt.json", {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python_version": sys.version,
        "context_revision": commands[0]["stdout"].strip(),
        "status": "frozen-host-owner-core-awaiting-independent-review",
        "source_binding_tree_sha256": digest,
        "scope": "Actual host ownership decisions with no Android effect runner or public routing",
        "root_selection_sha256": SELECTION_HASH, "implementation_files": 4,
        "unchanged_profile_inputs_checked": 42,
        "final_host_methods": run["test_result"]["tests"], "final_host_assertions": run["test_result"]["assertions"],
        "final_class_files": run["class_files"], "final_attempt": "attempts/final",
        "historical_attempt": "attempts/first; previous source version, counts not additive",
        "cleanup": cleanup, "implementation_accepted": False,
        "native_UI_capture_device_or_process_discovery": False,
        "public_V2_or_profile_change": False, "GA_qualified": False,
        "pending": ["independent review", "Android effect runner and lifecycle/environment integration after selection", "actual native runtime checks after pause", "API28 and OS/environment/resource/font/accessibility matrix", "state continuity and physical design parity", "immutable published separate-repository FieldLog, signing/store/operations and accountable GA evidence"]
    })
    members = dict(implementation)
    for path in sorted(PACKET.rglob("*")):
        assert not path.is_symlink(), path
        if path.is_file():
            members[path.relative_to(ROOT).as_posix()] = identity(path.read_bytes())
    write("manifest.json", {"schema": 1, "scope": "Host-core implementation and exact receipts; no historical packet archives", "members": members})
    print(json.dumps({"status": "frozen", "sealed_members": len(members),
                      "source_binding_tree_sha256": digest, "methods": 22,
                      "assertions": run["test_result"]["assertions"], "classes": run["class_files"]}, sort_keys=True))


if __name__ == "__main__":
    main()

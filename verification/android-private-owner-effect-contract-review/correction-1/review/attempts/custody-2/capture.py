#!/usr/bin/env python3
"""Independent custody/inventory only. Never imports producer or product helpers."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
UPSTREAM = ROOT / "verification/android-private-owner-effect-integration-proposal/correction-1"
EXPECTED = "1479c098f5721cc80e0c82f8699d1482a30f71ad241fa06cfe2c6902255bec08"
PREACCESS = BASE.parent / "preaccess"
PREACCESS_SEAL = "638028e6531f4846d5d68e8979b24a0742d243207e54d184addc14bd2246923c"
ORIGINAL = BASE.parents[1]
ORIGINAL_SEAL = "8f84a627384e42a5695a52b266f420cb4a26e7c670982266432a022ef1071d58"

def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def read(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return path.read_bytes()

def copy(path, target):
    data = read(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return ident(data)

def command(argv):
    x = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15, check=False)
    assert x.returncode == 0, (argv, x.stderr)
    return {"argv": argv, "cwd": str(ROOT), "exit_code": x.returncode,
            "stdout": x.stdout.decode(), "stderr": x.stderr.decode()}

def main():
    assert not (BASE / "custody.json").exists(), "capture is one-shot"
    pre = read(PREACCESS / "manifest.json")
    assert ident(pre)["sha256"] == PREACCESS_SEAL
    for name, expected in json.loads(pre)["files"].items():
        assert ident(read(PREACCESS / name)) == expected
    original = read(ORIGINAL / "manifest.json")
    assert ident(original)["sha256"] == ORIGINAL_SEAL
    for name, expected in json.loads(original)["files"].items():
        assert ident(read(ROOT / name)) == expected, name
    raw = read(UPSTREAM / "manifest.json")
    assert ident(raw)["sha256"] == EXPECTED
    m = json.loads(raw)
    assert len(m["files"]) == m["members"] == 48
    assert sum(v["bytes"] for v in m["files"].values()) == m["bytes"] == 974667
    snapshots = {}
    for name, expected in sorted(m["files"].items()):
        p = Path(name)
        assert not p.is_absolute() and ".." not in p.parts
        assert name == "docs/android-private-owner-effect-integration-correction.md" or name.startswith(
            "verification/android-private-owner-effect-integration-proposal/correction-1/")
        assert ident(read(ROOT / name)) == expected, name
        target = BASE / "candidate" / name
        snapshots[str(target.relative_to(BASE))] = copy(ROOT / name, target)
    target = BASE / "candidate/manifest.json"
    snapshots[str(target.relative_to(BASE))] = copy(UPSTREAM / "manifest.json", target)
    admission = ROOT / "verification/android-private-owner-effect-integration-root-review/correction-candidate-admission.json"
    target = BASE / "root-admission.json"
    snapshots[str(target.relative_to(BASE))] = copy(admission, target)
    assert json.loads(read(target))["manifest_sha256"] == EXPECTED
    r = json.loads(read(UPSTREAM / "required-host-roster.json"))
    barriers = r["baseline_callback_barriers"]
    assert len(barriers) == 189 and len({v["id"] for v in barriers}) == 189
    barrier_checks = []
    for entry in barriers:
        source = UPSTREAM / "inputs" / entry["source"]
        lines = read(source).decode().splitlines()
        actual = lines[entry["line"] - 1].strip()
        assert actual == entry["source_line"], entry["id"]
        assert actual[entry["column"] - 1:].startswith(entry["expression"]), entry["id"]
        barrier_checks.append({"id": entry["id"], "source": entry["source"],
            "line": entry["line"], "column": entry["column"], "expression": entry["expression"],
            "current_frozen_source_line_verified": True,
            "legacy_V1_helper": entry["source"].endswith("/NativeRenderer.java") and entry["line"] < 65})
    assert len([v for v in barrier_checks if v["legacy_V1_helper"]]) == 5
    closures = {}
    for name, closure in r["closures"].items():
        subjects = closure["actual_production_sources"]
        leaves = closure["substitutes"]
        assert len(subjects) == len(set(subjects))
        assert len(leaves) == len({v["fqcn"] for v in leaves}) == len({v["source"] for v in leaves})
        closures[name] = {"subjects": subjects, "subject_count": len(subjects),
            "substitute_count": len(leaves), "substitutes": leaves,
            "non_Android_substitutes": [v["fqcn"] for v in leaves if not v["fqcn"].startswith("android.")]}
    assert closures["B-concrete-renderer-views"]["subject_count"] == 14
    assert closures["B-concrete-renderer-views"]["substitute_count"] == 73
    assert closures["B-concrete-renderer-views"]["non_Android_substitutes"] == ["dev.mixer.android.NativeBridge"]
    producer_result = json.loads(read(UPSTREAM / "source-only-result.json"))
    assert producer_result["passed"] == 666 and producer_result["failed"] == 0
    assert producer_result["product_tests_run"] is False
    inventory = {"scope": "Independent literal roster and frozen source-anchor inventory only; no behavior proved.",
        "closures": closures, "barriers": barrier_checks, "barrier_count": 189,
        "V1_barrier_count": 5, "V2_region_barrier_count": 184,
        "producer_666_result": "Reported custody/coverage checks, not implementation tests; producer helper not executed.",
        "product_tests_run": False, "host_closures_executed": False}
    (BASE / "independent-inventory.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    commands = [command(["git", "rev-parse", "HEAD"]), command(["git", "rev-parse", "HEAD^{tree}"]), command(["git", "--version"])]
    py = Path(sys.executable).resolve(); git = Path(shutil.which("git")).resolve()
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [str(py), "-B", str(Path(__file__).resolve())],
        "commands": commands, "context_revision": commands[0]["stdout"].strip(), "context_tree": commands[1]["stdout"].strip(),
        "tools": {"python": {"path": str(py), "version": sys.version, **ident(read(py))},
                  "git": {"path": str(git), "version": commands[2]["stdout"].strip(), **ident(read(git))}},
        "candidate_manifest_sha256": EXPECTED, "members": 48, "bytes": 974667,
        "preaccess_manifest_sha256": PREACCESS_SEAL, "original_review_manifest_sha256": ORIGINAL_SEAL,
        "original_review_members_unchanged": 77, "snapshots": snapshots,
        "scope": "Independent exact admitted correction custody/source-only review, authorized by root.",
        "producer_helpers_executed": False, "product_tests_run": False,
        "native_runtime_UI_capture_process_discovery_network_install_signing_credentials_publication": False,
        "product_profile_metadata_CI_or_original_packet_edits": False}
    (BASE / "custody.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "admitted-correction-independent-source-custody-pass", "members": 48,
        "bytes": 974667, "baseline_barriers_verified": 189, "legacy_V1_barriers": 5,
        "concrete_subjects": 14, "concrete_substitutes": 73, "product_tests_run": False}))

if __name__ == "__main__":
    main()

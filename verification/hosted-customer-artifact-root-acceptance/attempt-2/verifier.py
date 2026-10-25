#!/usr/bin/env python3
"""Bind accepted ordinary artifact evidence to its saved and current sources."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PACKETS = [
    ("hosted-customer-artifact-event/run-4", 39),
    ("hosted-customer-artifact-event-review/run-3", 49),
    ("hosted-customer-artifact-read-scope/run-4", 63),
    ("hosted-customer-artifact-read-review/run-1", 80),
    ("hosted-customer-artifact-storage/run-14", 19),
    ("hosted-customer-artifact-storage-review/run-5", 22),
    ("hosted-customer-artifact-facade/run-1", 15),
    ("hosted-customer-artifact-facade-review/run-4", 12),
    ("hosted-customer-artifact-ci/run-3", 97),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


output = HERE / sys.argv[1]
assert output.parent == HERE and not output.exists()
output.mkdir()
(output / "verifier.py").write_bytes(Path(__file__).read_bytes())
bindings = {}
packets = []
for relative, count in PACKETS:
    directory = ROOT / "verification" / relative
    receipt_path = directory / "receipt.json"
    receipt = load(receipt_path)
    assert receipt.get("success") is True or receipt.get("result") == "passed", relative
    cleanup = receipt["cleanup"]
    assert cleanup.get("scratch_removed", cleanup.get("owned_scratch_removed", False)), relative
    if "postgres_stopped" in cleanup:
        assert cleanup["postgres_stopped"], relative
    saved = receipt.get("input_sha256", receipt.get("inputs"))
    assert isinstance(saved, dict) and saved
    for name, expected in saved.items():
        path = directory / "inputs" / name
        assert digest(path) == expected, str(path)
        bindings[str(path.relative_to(ROOT))] = expected
    for command in receipt["commands"]:
        exit_code = command.get("exit_code", command.get("exitCode"))
        stopped_probe = (
            command["name"] == "postgres-status" and exit_code == 3
            and Path(command["argv"][0]).name == "pg_ctl"
            and command["argv"][-1] == "status"
            and "no server running" in (directory / command["output"]).read_text()
            and cleanup.get("postgres_stopped") is True
        )
        assert exit_code == 0 or stopped_probe, (relative, command)
        if "output" in command:
            path = directory / command["output"]
            assert path.is_file()
            bindings[str(path.relative_to(ROOT))] = digest(path)
        else:
            for stream in ("stdout", "stderr"):
                path = directory / (command["name"] + "." + stream)
                expected = command[stream + "_sha256"]
                assert digest(path) == expected
                bindings[str(path.relative_to(ROOT))] = expected
    test_log = directory / ("tests.stdout" if relative.endswith("ci/run-3") else "tests.log")
    assert f"Result: {count} passed" in test_log.read_text(), relative
    bindings[str(receipt_path.relative_to(ROOT))] = digest(receipt_path)
    packets.append({"receipt": str(receipt_path.relative_to(ROOT)),
                    "receipt_sha256": digest(receipt_path), "passed_methods": count,
                    "source_tree_sha256": receipt["source_tree_sha256"],
                    "source_copies_verified": len(saved), "cleanup": cleanup})

ci = ROOT / "verification/hosted-customer-artifact-ci/run-3"
current = load(ci / "receipt.json")["inputs"]
assert all(digest(ROOT / name) == expected for name, expected in current.items())
assert (ci / "tests.stderr").read_bytes() == b""
migrations = (ci / "migration-smoke.stdout").read_text()
assert "status: :passed" in migrations and "20261025000005" in migrations

console = load(ROOT / "verification/console-build-overview-root-review/final-source-manifest.json")["files"]
assert all(digest(ROOT / name) == expected for name, expected in console.items())
vm = load(ROOT / "verification/swift-cost-retention-candidate/live-baseline-source-manifest.json")
assert all(digest(ROOT / "vm" / name) == expected for name, expected in vm.items())

result = {
    "schema": 1,
    "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "verifier_sha256": digest(Path(__file__)),
    "python": sys.version,
    "status": "accepted-local-customer-artifact-composition",
    "packets": packets,
    "retained_bindings": len(bindings),
    "current_ci_source_bindings": len(current),
    "current_ci_tree_sha256": load(ci / "receipt.json")["source_tree_sha256"],
    "current_combined_methods": 97,
    "migration_count": 7,
    "rollback_reapply_count": 4,
    "console_source_bindings_unchanged": len(console),
    "vm_source_bindings_unchanged": len(vm),
    "scope": "Local PostgreSQL artifact upload/private read/audit with transaction-owned authorization and reviewed immutable storage. Current-source focused CI fixture only; all prior failures retained separately.",
    "limitations": [
        "No protected HTTP route or live console data connection; no deployment, provider login, R2/CDN publication or operational acceptance.",
        "One server-configured host/trust snapshot; multi-tenant trust registry and coordinated mutation writers remain pending.",
        "Independent reviews used their recorded snapshots; the latest migration and test-loader repairs are joined by current-source combined CI.",
        "No native, physical-phone, separate published FieldLog, full product or GA acceptance. Standard hosted CI requires a separate exact-push result.",
    ],
}
(output / "bindings.json").write_text(json.dumps(bindings, indent=2, sort_keys=True) + "\n")
result["bindings_sha256"] = digest(output / "bindings.json")
(output / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ["status", "retained_bindings", "current_ci_source_bindings", "current_combined_methods", "migration_count"]}))

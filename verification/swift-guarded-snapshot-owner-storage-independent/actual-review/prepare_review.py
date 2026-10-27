"""Independent read-only custody check before owner-storage producer access.

Writes only this new actual-review folder. Never executes or imports evidence.
"""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import sys

HERE = Path(__file__).resolve().parent
V = HERE.parents[1]
PRE = V / "swift-guarded-snapshot-owner-storage-independent/preaccess"
AUTH = V / "swift-guarded-snapshot-scope-authority-correction"
sha = lambda b: hashlib.sha256(b).hexdigest()


def exact_file(path, digest):
    data = path.read_bytes()
    assert sha(data) == digest, f"Changed frozen file: {path}"
    return {"path": str(path.relative_to(V)), "bytes": len(data), "sha256": sha(data)}


def verify_seal(directory, digest, count):
    result = exact_file(directory / "seal.json", digest)
    seal = json.loads((directory / "seal.json").read_text())
    members = seal["members"]
    assert len(members) == count
    assert len({m["path"] for m in members}) == count
    for member in members:
        path = directory / member["path"]
        assert path.resolve().is_relative_to(directory.resolve())
        data = path.read_bytes()
        assert (len(data), sha(data)) == (member["bytes"], member["sha256"]), str(path)
    result.update(member_count=count, member_bytes=sum(m["bytes"] for m in members), all_members_verified=True)
    return result


def main():
    inputs = [
        verify_seal(PRE, "acce273e604a3c868789af271dc4160e25a498f9dddbfaef24c2bb7d0caaa879", 6),
        verify_seal(AUTH, "351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c", 225),
        verify_seal(V / "swift-guarded-snapshot-composition-independent/candidate-review", "c38fc429932b8681569b57c3a86416c1d003d032e82d942ad424fc02712c5a58", 102),
        verify_seal(V / "swift-guarded-snapshot-composition-independent/authority-correction-review", "ed396b3b74fb5e399d7ebee1759b19dae35d8f7fc577fdd92825f7eb31421b36", 77),
        exact_file(V / "swift-semantic-adapter-root-review/guarded-snapshot-owner-storage-independent-preaccess-custody.json", "1ed2588f4677f30d4f90620f71568dd2a53099e44c4efd98a0d747163515d739"),
        exact_file(V / "swift-semantic-adapter-root-review/guarded-snapshot-encoder-storage-host-acceptance.json", "ae71f01a593007cf89b093ca8dc5cfc5dc5e5801374d0f900be012bfd43d86b3"),
    ]
    manifest = json.loads((AUTH / "source-manifest.json").read_text())
    assert len(manifest["members"]) == 144
    tree = sha(json.dumps(manifest["members"], sort_keys=True, separators=(",", ":")).encode())
    # The original tree convention is checked by exact manifest custody above;
    # retain the independently serialized digest separately, without relabeling.
    assert manifest["source_tree_sha256"] == "575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896"
    expectations = json.loads((PRE / "source-expectations.json").read_text())
    for group in expectations["groups"]:
        for region in group["sources"]:
            path = AUTH / "source/vm" / region["path"]
            data = path.read_bytes()
            assert sha(data) == region["source_sha256"]
            lines = data.decode().splitlines(keepends=True)
            subset = "".join(lines[region["start_line"]-1:region["end_line"]]).encode()
            assert sha(subset) == region["region_sha256"]
    assert len(expectations["groups"]) == 12
    report = {
        "schema": 1,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "preparation-ready-awaiting-root-producer-release",
        "command": [sys.executable, str(Path(__file__).resolve())],
        "python_version": platform.python_version(),
        "inputs": inputs,
        "source_revision": json.loads((PRE / "receipt.json").read_text())["source_revision"],
        "source_revision_provenance": "frozen preaccess receipt; source bytes independently verified",
        "source_tree_sha256": manifest["source_tree_sha256"],
        "manifest_canonical_json_sha256": tree,
        "source_members_verified": 144,
        "funding_families_verified": [g["id"] for g in expectations["groups"]],
        "producer_packet_accessed": False,
        "compiler_invocations": 0,
        "engine_VM_writer_runtime_executions": 0,
        "native_device_simulator_emulator_UI_capture_process_inventory_executions": 0,
        "canonical_or_git_mutations": False,
        "new_evidence_only": str(HERE.relative_to(V)),
        "acceptance": {
            "complete_inventory": False,
            "storage_floor_selected": False,
            "healthy_cleanup": False,
            "production_caller": False,
            "operational_execution": False,
            "GA_gates_verified": 0,
        },
    }
    (HERE / "preparation-receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "source_members": 144, "families": 12, "producer_accessed": False}))


if __name__ == "__main__":
    main()

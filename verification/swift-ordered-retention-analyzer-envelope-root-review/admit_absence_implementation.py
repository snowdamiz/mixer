"""Verify exact selected producer evidence without executing frozen collectors."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "verification/swift-envelope-absent-state-correction/implementation"


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def verify(row):
    path = Path(row["path"])
    assert not path.is_absolute() and ".." not in path.parts
    assert identity(ROOT / path) == {k: row[k] for k in ("bytes", "sha256")}, str(path)


packets = []
for name, digest, count, size in [
    ("verification/swift-envelope-absent-state-correction/proposal-1/seal.json", "3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c", 35, 205372),
    ("verification/swift-envelope-absent-state-accounting-review/seal.json", "c9191a26ed0c5081e9c2ad97082fc61cee3f6eeb94ea49c4be5028b0f54536e4", 22, 119706),
    ("verification/swift-envelope-absent-state-correction/implementation/seal.json", "1e45ae55b5a159fd2c384bfdbbc520467e467b391af9f6a1d655e8ab67f0012a", 120, 8532453),
]:
    assert identity(ROOT / name)["sha256"] == digest
    members = json.loads((ROOT / name).read_text())["members"]
    assert len(members) == count and sum(x["bytes"] for x in members) == size
    for row in members:
        verify(row)
    packets.append({"seal": name, "sha256": digest, "members": count, "bytes": size})
final = json.loads((BASE / "final-receipt.json").read_text())
assert identity(BASE / "final-receipt.json")["sha256"] == "6f6b1c607237aaaf5a0df3ed880165752af7f221180de6ef176e8608833f7f79"
assert final["distinct_final_host_method_bodies_passed"] == 78
assert final["fresh_unchanged_methods"]["passed"] == 70
assert final["focused_controls"]["passed"] == 8
assert final["fresh_candidate_oracle_comparisons"]["total"] == 21714
assert final["fresh_complete_layouts"]["count"] == 32
assert final["API"]["positive"] == 1 and final["API"]["expected_negative"] == 8
assert final["claim_of_one_all_green_attempt"] is False
command_count = 0
for tag in ("run-1", "run-2"):
    run = BASE / tag
    receipt = json.loads((run / "receipt.json").read_text())
    assert receipt["all_children_reaped"] and receipt["owned_scratch_removed"]
    assert receipt["source_and_frozen_inputs_preserved"]
    assert receipt["compiled_owned_inputs_before"] == receipt["compiled_owned_inputs_after"]
    assert receipt["direct_immutable_inputs_before"] == receipt["direct_immutable_inputs_after"]
    assert len(receipt["direct_immutable_inputs_after"]) == 44
    for row in receipt["direct_immutable_inputs_after"] + receipt["compiled_owned_inputs_after"]:
        verify(row)
    assert not (run / "owned-scratch").exists()
    for command in receipt["commands"]:
        assert command["child_reaped"] and not command["timed_out"]
        assert command["immediate_inputs_before"] == command["immediate_inputs_after"]
        for stream in ("stdout", "stderr"):
            assert identity(run / command[stream]) == {"bytes": command[stream + "_bytes"], "sha256": command[stream + "_sha256"]}
        expected_code = 101 if tag == "run-1" and command["name"] == "focused-absence8" else (1 if command["name"].startswith("api-negative-") else 0)
        assert command["returncode"] == expected_code
        command_count += 1
assert command_count == 27
binding = json.loads((BASE / "source-test-model-binding.json").read_text())
for row in binding["product_source_pair"]:
    verify(row)
assert final["candidate_source_sha256"] == "2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef"
assert final["parent_source_sha256"] == "1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b"
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())],
    "python_version": sys.version,
    "checker": identity(Path(__file__)),
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "packets": packets,
    "root_verified_members": 177,
    "root_verified_bytes": 8857531,
    "qualification_commands": command_count,
    "raw_streams_verified": command_count * 2,
    "direct_immutable_fixture_inputs_verified": 44,
    "producer_methods_passed_across_two_attempts": 78,
    "first_focused_test_expectation_failure_preserved": True,
    "selected_source_changed": False,
    "candidate_source_sha256": final["candidate_source_sha256"],
    "parent_source_sha256": final["parent_source_sha256"],
    "independent_behavior": "Still running; no implementation acceptance inferred",
    "implementation_accepted": False,
    "native_runtime_or_capture_started": False,
    "semantic_or_GA_qualified": False,
    "errors": [],
}
(OUT / "absence-implementation-preflight.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ("root_verified_members", "root_verified_bytes", "qualification_commands", "implementation_accepted")}))

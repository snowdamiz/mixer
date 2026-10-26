"""Accept only the independently tested host lifecycle decision core."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REVIEW = ROOT / "verification/android-public-owner-core-independent-review"


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


packets = []
for name, digest, count, size in [
    ("verification/android-public-owner-contract/manifest.json", "4ecf1287a35219c11992769f95dfc7d699031001bf7d73306caaa4817f78c747", 8, 53755),
    ("verification/android-public-owner-core/manifest.json", "0719d4cf27fcd5284aa04ee68dd96db186b06fc64cf4ce93f18cd4b60c12660f", 48, 183472),
    ("verification/android-public-owner-core-independent-review/manifest.json", "5f3c6a2b2ff1a0146fa07e0676e7eed52f5160cc302c597fdcd680da811e4103", 63, 549903),
]:
    assert identity(ROOT / name)["sha256"] == digest
    members = json.loads((ROOT / name).read_text())["members"]
    assert len(members) == count and sum(v["bytes"] for v in members.values()) == size
    for member, expected in members.items():
        path = Path(member)
        assert not path.is_absolute() and ".." not in path.parts
        assert identity(ROOT / path) == expected, member
    packets.append({"manifest": name, "sha256": digest, "members": count, "bytes": size})
assert identity(REVIEW / "seal.json")["sha256"] == "e285befba1558c1d54ce5e48aa3985c717e1a1d8409b4f90a4b20b19243f8dd8"
receipt = json.loads((REVIEW / "receipt.json").read_text())
assert receipt["candidate_defects"] == [] and receipt["harness_or_oracle_defects"] == []
assert receipt["owned_host_child_count"] == 12 and receipt["all_owned_children_returned_and_reaped"]
assert receipt["owned_scratch_removed_only_after_children_returned"]
assert identity(OUT / "preaccess-seal.json")["sha256"] == receipt["root_preaccess_seal_sha256"]
summary = receipt["attempts"]["final"]["summary"]
assert (summary["methods"], summary["scenarios"], summary["assertions"]) == (33, 71, 264289)
assert summary["failures"] == 0 and summary["max_batch"] == 4
assert set(summary["control_passed_methods"]) == {f"R{i:02d}" for i in range(1, 16)}
for tag in ("first", "final"):
    attempt = REVIEW / "attempts" / tag
    commands = json.loads((attempt / "commands.json").read_text())
    assert len(commands) == 6
    for command in commands:
        assert command["returncode"] == 0 and command["returned_and_reaped"] and not command["timed_out"]
        for stream in ("stdout", "stderr"):
            assert identity(attempt / (command["name"] + "." + stream)) == command[stream]
    cleanup = receipt["attempts"][tag]["cleanup"]
    assert not Path(cleanup["owned_scratch"]).exists()
binding = json.loads((ROOT / "verification/android-public-owner-core/source-bindings.json").read_text())
for group in ("implementation", "unchanged_source_pair_1"):
    for name, expected in binding[group].items():
        assert identity(ROOT / name) == expected
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())],
    "python_version": sys.version,
    "checker": identity(Path(__file__)),
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "accepted-scoped-host-owner-decision-core",
    "packets": packets,
    "root_verified_members": 119,
    "root_verified_bytes": 787130,
    "current_implementation_and_profile_inputs_verified": 46,
    "source_pair_1_unchanged_inputs": 42,
    "candidate_source": receipt["candidate"],
    "root_verified_independent_commands": 12,
    "root_verified_independent_raw_streams": 24,
    "producer_host_methods": 22,
    "producer_host_assertions": 45841,
    "independent_final_summary": summary,
    "attempt_counts_nonadditive": True,
    "accepted_scope": "Pure package-private Java lifecycle ownership decisions outside exported adapter map, exact terminal/resource/token/dirty-epoch rules, bounded core slots and per-call decisions. Official OpenJDK25.0.4.1 host compilation targets Java17; no Android runtime or effect execution.",
    "retained_state_bound": "28 fixed instance fields, including20reference slots,6booleans,2longs; no core-owned history. Caller-owned object graphs are not bounded by this claim.",
    "limitations": receipt["pending_limits"],
    "actual_cleanup_or_reclamation_proven": False,
    "implementation_accepted": True,
    "public_V2_selected": False,
    "source_pair_profile_changed": False,
    "native_runtime_or_capture_started": False,
    "GA_qualified": False,
    "errors": [],
}
assert sum(p["members"] for p in packets) == result["root_verified_members"]
assert sum(p["bytes"] for p in packets) == result["root_verified_bytes"]
(OUT / "implementation-acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ("status", "root_verified_members", "root_verified_bytes", "implementation_accepted")}))

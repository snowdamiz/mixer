"""Read only explicitly selected frozen inputs; never execute producer tools.

This review records custody and baseline source facts before candidate release.
It does not inspect verification/swift-selected-profile-adoption/**.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "verification/swift-real-profile-loader-binding"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def identity(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": sha(data)}


def checked_json(relative, expected):
    path = ROOT / relative
    assert sha(path.read_bytes()) == expected, str(path)
    return load(path)


def closed_packet(relative, expected):
    packet = ROOT / relative
    seal = checked_json(relative + "/seal.json", expected)
    members = seal["members"]
    expected_paths = {m["path"] for m in members}
    assert len(expected_paths) == len(members) == seal["member_count"]
    actual_paths = set()
    for path in packet.rglob("*"):
        assert not path.is_symlink(), str(path)
        if path.is_file():
            actual_paths.add(str(path.relative_to(packet)))
    assert actual_paths == expected_paths | {"seal.json"}
    for member in members:
        path = packet / member["path"]
        assert path.is_relative_to(packet)
        data = path.read_bytes()
        assert len(data) == member["bytes"]
        assert sha(data) == member["sha256"], str(path)
    return {"path": relative, "seal_sha256": expected,
            "member_count": len(members),
            "member_bytes": sum(m["bytes"] for m in members),
            "all_member_bytes_and_exact_closed_file_set_verified": True}


selection = checked_json(
    "verification/swift-semantic-adapter-root-review/selected-profile-adoption-implementation-selection.json",
    "632f68edac578808b2162e94e0051c50732e45a48ebaa3a0d8ea790e3b51f2e3",
)
acceptance = checked_json(
    "verification/swift-semantic-adapter-root-review/real-loader-host-acceptance.json",
    "6c579a2a868bb2eb8ba94f7680355171d28ade46f5a5c89ebf96f014915eeb70",
)
packets = [closed_packet(
    "verification/swift-real-profile-loader-binding",
    "e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2",
), closed_packet(
    "verification/swift-real-profile-loader-independent",
    "20841ffd95685e0a65d926c747dfd2c7394341663593cca7c6c01d2c2f329c3f",
)]

source = load(BASE / "source-manifest.json")
assert source["member_count"] == 144
assert source["tree_sha256"] == selection["baseline_source_tree_sha256"]
for member in source["members"]:
    path = BASE / "source/vm" / member["path"]
    data = path.read_bytes()
    assert len(data) == member["bytes"] and sha(data) == member["sha256"]

support = load(BASE / "baseline-host-support-manifest.json")
assert support["member_count"] == 11
for member in support["members"]:
    data = (BASE / member["retained_path"]).read_bytes()
    assert len(data) == member["bytes"] and sha(data) == member["sha256"]

src = BASE / "source/vm/src/experimental_swift_reactor"
facts = {
    "control.rs": [(344, 354), (516, 544), (559, 675), (1200, 1216), (1219, 1229)],
    "cache.rs": [(268, 281), (300, 322), (334, 356), (1047, 1137)],
    "execution.rs": [(846, 890)],
    "cache/initial_profile_v1.rs": [(38, 47), (64, 99), (114, 159)],
    "cache/initial_profile_v1/local_structure.rs": [(1, 177)],
    "retained_profile_loader_v1.rs": [(134, 180), (1094, 1133)],
}
fact_rows = []
for name, spans in facts.items():
    path = src / name
    lines = path.read_text().splitlines()
    for first, last in spans:
        excerpt = "\n".join(lines[first - 1:last]) + "\n"
        fact_rows.append({"source": str(path.relative_to(ROOT)), "source_sha256": sha(path.read_bytes()),
                          "first_line": first, "last_line": last, "excerpt_sha256": sha(excerpt.encode()),
                          "text": excerpt})

local = (src / "cache/initial_profile_v1/local_structure.rs").read_text()
old_types = [{"id": int(i), "type": ty}
             for i, ty in re.findall(r"compare!\((\d+),(.+)\);", local)]
assert [x["id"] for x in old_types] == list(range(1, 166))
layouts = load(BASE / "data-layouts.json")
assert all(len(layouts[mode]) == 23 for mode in ["debug", "optimized"])

producer = load(BASE / "receipt.json")
rustc = Path(producer["rustc"]["path"])
assert identity(rustc) == producer["rustc"]
commands = []
for label, argv in [
    ("revision", ["/usr/bin/git", "rev-parse", "HEAD"]),
    ("rustc-version", [str(rustc), "--version", "--verbose"]),
    ("rustc-target-cfg", [str(rustc), "--print", "cfg"]),
]:
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    assert result.returncode == 0, label
    commands.append({"label": label, "argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
                     "stdout": result.stdout.decode(), "stderr": result.stderr.decode()})

out = {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "independent-preaccess-baseline-source-review-prepared-candidate-unread",
    "script": identity(Path(__file__)), "python": identity(Path(sys.executable).resolve()),
    "python_version": sys.version, "commands": commands,
    "selected_contract_sha256": "632f68edac578808b2162e94e0051c50732e45a48ebaa3a0d8ea790e3b51f2e3",
    "accepted_loader_sha256": "6c579a2a868bb2eb8ba94f7680355171d28ade46f5a5c89ebf96f014915eeb70",
    "packets": packets, "baseline_source_tree_sha256": source["tree_sha256"],
    "source_members_verified": 144, "host_support_members_verified": 11,
    "source_facts": fact_rows, "old165_exact_identity_roster": old_types,
    "baseline_loader23_actual_unit_measurements": layouts,
    "candidate_files_read_or_executed": 0, "frozen_runner_or_finalizer_executions": 0,
    "paused_native_UI_capture_process_inventory_used": False,
    "runtime_adoption_or_operational_storage_or_GA_accepted": False,
    "cleanup": {"direct_host_children_terminally_waited": True,
                "scratch_or_native_instances_created": False,
                "frozen_packets_mutated": False, "File_drop_is_close_success": False},
}
(HERE / "preaccess-receipt.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": out["status"], "packets": packets,
                  "old_type_identities": len(old_types), "source_facts": len(fact_rows),
                  "candidate_files_read_or_executed": 0}, sort_keys=True))

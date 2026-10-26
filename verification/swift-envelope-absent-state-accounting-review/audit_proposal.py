#!/usr/bin/env python3
"""Independent byte/delta/arithmetic audit. No proposal code is imported or run."""
from pathlib import Path
import hashlib
import json
import math
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent / "audit-1"
OWN.mkdir(exist_ok=False)
P = ROOT / "verification/swift-envelope-absent-state-correction/proposal-1"
checks = []
digest = lambda b: hashlib.sha256(b).hexdigest()
canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def check(name, condition, detail=None):
    checks.append({"name": name, "passed": bool(condition), "detail": detail})

def bound_file(record):
    data = (ROOT / record["path"]).read_bytes()
    check("bound input " + record["path"], len(data) == record["bytes"] and digest(data) == record["sha256"])
    return data

seal_data = (P / "seal.json").read_bytes()
check("explicit handoff seal", digest(seal_data) == "3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c")
seal = json.loads(seal_data)
for member in seal["members"]:
    bound_file(member)

binding = json.loads((P / "source-binding.json").read_text())
before = bound_file(binding["baseline"])
after = bound_file(binding["candidate"])
rebuilt = before
for i, replacement in enumerate(binding["exact_replacements"]):
    old = replacement["before"].encode()
    new = replacement["after"].encode()
    check(f"source replacement {i} is unique", rebuilt.count(old) == 1)
    rebuilt = rebuilt.replace(old, new, 1)
check("exactly two source replacements", len(binding["exact_replacements"]) == 2)
check("otherwise exact baseline bytes", rebuilt == after)
check("candidate source identity", digest(after) == "2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef")
parent = bound_file(binding["parent"])
check("parent identity unchanged", digest(parent) == "1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b")

delta = json.loads((P / "ledger-delta.json").read_text())
old_ledger = json.loads(bound_file(delta["baseline"]))
old_rows = {r["id"]: r for r in old_ledger["rows"]}
check("old ledger unique116", len(old_rows) == len(old_ledger["rows"]) == 116)
for entry in delta["unchanged_rows"]:
    check("unchanged row " + entry["id"], digest(canonical(old_rows[entry["id"]])) == entry["canonical_sha256"])
rows = dict(old_rows)
for entry in delta["replaced_rows"]:
    check("replaced old row " + entry["id"], digest(canonical(old_rows[entry["id"]])) == entry["old_canonical_sha256"])
    rows[entry["id"]] = entry["new"]
for entry in delta["removed_rows"]:
    check("removed old row " + entry["id"], digest(canonical(old_rows[entry["id"]])) == entry["canonical_sha256"])
    del rows[entry["id"]]
for entry in delta["added_rows"]:
    check("added id absent " + entry["id"], entry["id"] not in rows)
    rows[entry["id"]] = entry
classified_old = [r["id"] for r in delta["unchanged_rows"] + delta["replaced_rows"] + delta["removed_rows"]]
check("all old rows classified exactly once", len(classified_old) == len(set(classified_old)) == 116 and set(classified_old) == set(old_rows))
check("reconstructed rows121", len(rows) == delta["result_row_count"] == 121)

# These source-block counts were independently derived from actual source,
# using the already accepted native indexed-read primitive6+member selection1.
expected = {"DV00": 7, "DV01": 15, "DV02": 15, "DV02R": 2, "DV03": 10, "DV04": 10, "DV05": 25}
partitions = {"DV00": [7], "DV01": [15], "DV02": [15], "DV02R": [2], "DV03": [10], "DV04": [10], "DV05": [10, 15]}
for name, count in expected.items():
    row = rows[name]
    check("scalar atom count " + name, count == row["scalar_operations"] == sum(a["count"] for a in row["scalar_atoms"]))
    check("scalar group partition " + name, sum(partitions[name]) == count and all(0 < n <= 16 for n in partitions[name]) and len(partitions[name]) == row["scalar_groups"] == row["groups"] and row["copy_groups"] == 0)
paths = {
    "paid": ["DV00", "DV01"],
    "unpaid-inconsistent": ["DV00", "DV02", "DV02R"],
    "unpaid-poison-reason": ["DV00", "DV02", "DV03", "DV04"],
    "unpaid-Steps-or-reject": ["DV00", "DV02", "DV03", "DV05"]
}
path_groups = {name: sum(rows[r]["groups"] for r in path) for name, path in paths.items()}
check("independent validator path maxima", list(path_groups.values()) == [2, 3, 4, 5] and max(path_groups.values()) == rows["W08"]["groups"] == 5)
check("L01 reorder scalar total", rows["L01"]["scalar_operations"] == sum(a["count"] for a in rows["L01"]["scalar_atoms"]) == 25 and rows["L01"]["groups"] == 2)

compositions = {}
for title, ids_key, result_key in [
    ("leaf", "leaf_rows", "leaf_total"),
    ("guard", "guard_shared_rows", "guard_total"),
    ("wrapper", "wrapper_record_rows", "wrapper_record_total"),
    ("setup_actual", "setup_rows", "setup_actual_bound"),
    ("T", "wrapper_setup_rows", "wrapper_setup_total"),
    ("finish", "finish_rows", "finish_total"),
    ("F", "wrapper_final_rows", "wrapper_final_total")
]:
    compositions[title] = sum(rows[name]["groups"] for name in delta["composition"][ids_key])
    check("composition " + title, compositions[title] == delta["composition"][result_key])
check("selected composition totals", compositions == {"leaf": 425, "guard": 112, "wrapper": 24, "setup_actual": 329, "T": 42, "finish": 47, "F": 42})
check("combined B471", 22 + compositions["leaf"] + compositions["wrapper"] == 471)
check("zero-call public581", 534 + compositions["finish"] == 581)
guard_groups = {"absent": math.ceil(9/16) + 1 + 1 + 4, "invalid_entry_spent": math.ceil(13/16) + 1 + 1 + 4, "present_underfunded": 2+3+96+1+10}
check("guard paths7/7/112", list(guard_groups.values()) == [7, 7, 112] and max(guard_groups.values()) == 112)

edges_delta = json.loads((P / "copy-edge-delta.json").read_text())
edges = json.loads(bound_file(edges_delta["baseline"]))["edges"]
edge_by_id = {(e["row"], e["index"]): e for e in edges}
check("108 unique inherited edges", len(edge_by_id) == len(edges) == 108)
for entry in edges_delta["unchanged_edge_ids"]:
    key = (entry["row"], entry["index"])
    check("unchanged edge " + str(key), digest(canonical(edge_by_id[key])) == entry["canonical_sha256"])
check("all edges classified with no delta", len(edges_delta["unchanged_edge_ids"]) == 108 and not any(edges_delta[k] for k in ["added", "changed", "removed"]))
check("all edge list identity", digest(canonical(edges)) == edges_delta["all_edge_canonical_sha256"])
check("actual transfer chunks bounded128", all(0 < e["transfer_chunk_bytes"] <= 128 for e in edges))

memory = json.loads((P / "type-lifetime-delta.json").read_text())
inventory = json.loads(bound_file(memory["baseline_inventory"]))
bound_file(memory["baseline_layout_receipt"])
check("logical groups unchanged24656", sum(memory["groups"].values()) == memory["named_total"] == inventory["named_role_upper_total"] == 24656)
check("unchanged reservation41984/ceiling65536", memory["reservation"] == inventory["reserved_total"] == 41984 and memory["ceiling"] == inventory["transient_ceiling"] == 65536)
check("no named owner or complete type added", memory["new_locals_or_value_owners"] == [] and memory["type_declarations_changed"] == [])

# Recheck every candidate member after audit. No source/test/runner was imported.
for member in seal["members"]:
    data = (ROOT / member["path"]).read_bytes()
    check("post-audit immutable " + member["path"], len(data) == member["bytes"] and digest(data) == member["sha256"])
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
receipt = {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "command": "python3 verification/swift-envelope-absent-state-accounting-review/audit_proposal.py",
    "tool": {"python": platform.python_version(), "executable": sys.executable},
    "source_revision_context": head, "source_pair_digest_recipe": "sha256(canonical JSON sorted-key compact object of candidate/parent SHA256)",
    "source_pair_digest": digest(canonical({"candidate": digest(after), "parent": digest(parent)})),
    "candidate_source_sha256": digest(after), "parent_source_sha256": digest(parent), "producer_seal_sha256": digest(seal_data),
    "scope": "Independent offline byte reconstruction, ledger/edge identity and bounded arithmetic checks only. No corrected Rust candidate compilation/runtime, no source interpretation/eval or producer script import/execution, no native/capture/process discovery.",
    "checks": checks, "passed": sum(c["passed"] for c in checks), "failed": sum(not c["passed"] for c in checks),
    "rows": len(rows), "copy_edges": len(edges), "compositions": compositions, "validator_path_groups": path_groups, "guard_path_groups": guard_groups,
    "independent_scalar_partitions": partitions,
    "ownership_selection": False, "runtime_behavior_accepted": False, "product_or_GA_accepted": False
}
(OWN / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
summary = json.dumps({k:receipt[k] for k in ["passed", "failed", "rows", "copy_edges", "compositions", "validator_path_groups", "guard_path_groups", "source_pair_digest"]}, sort_keys=True) + "\n"
(OWN / "stdout.txt").write_text(summary)
(OWN / "stderr.txt").write_bytes(b"")
print(summary, end="")
if receipt["failed"]:
    raise SystemExit(1)

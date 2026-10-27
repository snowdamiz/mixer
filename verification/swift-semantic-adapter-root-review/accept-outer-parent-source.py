"""One-shot bounded source acceptance; no selector or operational grant changes."""
from datetime import datetime, timezone
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
NAME = "guarded-snapshot-outer-parent-host-acceptance.json"
assert not (OUT / NAME).exists(), "Root acceptance already recorded"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def verify(name, expected):
    folder = ROOT / "verification" / name
    assert sha(folder / "seal.json") == expected
    seal = read(folder / "seal.json")
    names, total = set(), 0
    for row in seal["members"]:
        relative = Path(row["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert str(relative) not in names
        names.add(str(relative))
        p = folder / relative
        assert p.is_file() and not p.is_symlink()
        assert p.stat().st_size == row["bytes"] and sha(p) == row["sha256"]
        total += row["bytes"]
    assert names == {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file() and p.name != "seal.json"}
    assert len(names) == seal["member_count"]
    assert total == seal.get("bytes", seal.get("member_bytes"))
    return {"path": str(folder.relative_to(ROOT)), "seal_sha256": expected,
            "members": len(names), "bytes": total}

producer = verify("swift-guarded-snapshot-outer-parent-source", "3936c73a0f3558000834c92c3ade9822465069492740a954765cb775684bcb57")
independent = verify("swift-guarded-snapshot-outer-parent-independent", "70bbf1cdd9a63494e63c4c7cbda22cd8e8c1cd8c961af36dee37d528b695902e")
ind = ROOT / independent["path"]
result = read(ind / "results.json")
compiler = read(ind / "commands/compiler-metadata-mir/receipt.json")
assert result["assertions"] == 917 and result["compiler_observations"] == 44
assert result["all_three_selectors_pending"] and not result["new_outer_work_and_storage_priced"]
assert compiler["exit_code"] == 0 and compiler["compile_success"]
assert not compiler["timed_out"] and compiler["child_reaped"] and compiler["owned_group_absent"]
assert compiler["owned_scratch_removed"] and compiler["compiler_invocations"] == 1 and compiler["retries"] == 0
artifact = next(a for a in compiler["artifacts"] if a["path"] == "query.mir")
decoded = gzip.decompress((ind / "commands/compiler-metadata-mir/query.mir.gz").read_bytes())
assert len(decoded) == artifact["bytes"] and hashlib.sha256(decoded).hexdigest() == artifact["sha256"]
del decoded
receipt = {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "bounded-private-outer-parent-source-and-layout-host-acceptance",
    "producer": producer, "independent": independent,
    "original_source_tree_sha256": "690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185",
    "candidate_source_tree_sha256": "27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3",
    "source_members": 146, "unchanged_members": 145,
    "all_original_changed_member_bytes_preserved": True,
    "main_assertions": 917, "additional_adverse_assertions": 47, "hostile_mutations_rejected": 15,
    "reviewer_failures_preserved": 3, "source_blocking_findings": 0,
    "review_results_sha256": sha(ind / "results.json"),
    "compiler_receipt": str((ind / "commands/compiler-metadata-mir/receipt.json").relative_to(ROOT)),
    "compiler_receipt_sha256": sha(ind / "commands/compiler-metadata-mir/receipt.json"),
    "independent_compiler_exit": 0, "compiler_elapsed_seconds": compiler["elapsed_seconds"],
    "compiler_query_tree_sha256": compiler["query_tree_sha256"],
    "compiler_cleanup_confirmed": True, "layout_observations": 44,
    "full_retained_MIR_rehashed": artifact,
    "conditional_counts": result["conditional_route_maxima"],
    "direct_terminal_paths": 43, "consumer_terminal_paths": 32,
    "old_account_component_at_conditional_ceilings": 2628088 + 194231 + 3 * 1039,
    "selection": "Exact private caller source, affine original-owner view/destruction/token flow and conditional occurrence ceilings are accepted for subsequent source-bound pricing. Normal Some-token release follows original payload/carrier destruction; None/refusal/unwind cannot refund. No selector, account, actual I/U execution or operational funding is selected.",
    "original_producer_compiler_terminal_facts": "Unknown exit/time/timeout/PID/group facts remain unknown; fresh independent success does not repair the historical receipt failure.",
    "all_three_selectors_pending": True, "rust_tests_compiled_or_run": False,
    "new_outer_work_storage_priced": False, "actual_immutable_binding_selected": False,
    "complete_compiled_caller_correspondence": False,
    "fixture_writer_healthy_cleanup_runtime_accepted": False,
    "native_runtime_FieldLog_OTA_GA": False,
    "root_verification": {"argv": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
        "python": sys.version, "script_sha256": sha(Path(__file__)),
        "source_revision": "a32d056355ec2f417e9ef7a73788b420176377b6",
        "scope": "Exact producer/reviewer custody, retained compiler terminal/cleanup facts and complete decompressed MIR hash; no runtime or compiler launch"},
}
with (OUT / NAME).open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
w, g = read(ROOT / "work-graph.json"), read(ROOT / "gates/ga.json")
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["outer_parent_source"].update({"status": "bounded-source-layout-host-accepted-pricing-pending",
    "accepted": True, "acceptance": str((OUT / NAME).relative_to(ROOT)),
    "acceptance_sha256": sha(OUT / NAME), "independent_seal_sha256": independent["seal_sha256"],
    "independent_compiler_terminal_status": "passed-with-owned-cleanup",
    "conditional_I_max": 1, "conditional_U_max": 3,
    "actual_immutable_binding_selected": False, "runtime_selected": False})
delivery_dir = ROOT / "verification/github-delivery-host-interface-amendment"
delivery = read(delivery_dir / "receipt.json")
runs = read(delivery_dir / "ci-runs-1.stdout")
assert len(runs) == 1 and runs[0]["headSha"] == delivery["commit"]
c["guarded_snapshot_host_interface_amendment_delivery"] = {
    "commit": delivery["commit"], "tree": delivery["tree"], "parent": delivery["parent"],
    "paths": delivery["committed_paths"], "packets": 4, "pushed": True,
    "receipt": str((delivery_dir / "receipt.json").relative_to(ROOT)),
    "receipt_sha256": sha(delivery_dir / "receipt.json"), "manifest_sha256": delivery["manifest_sha256"],
    "CI": {"run": runs[0]["databaseId"], "status": runs[0]["status"], "conclusion": runs[0]["conclusion"],
           "terminal": False, "url": runs[0]["url"], "evidence": str((delivery_dir / "ci-runs-1.stdout").relative_to(ROOT))},
    "canonical_product_changed": False, "whole_host_grant_or_GA": False,
    "three_active_lanes_excluded": True,
}
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
for name, value in (("work-graph.json", w), ("gates/ga.json", g)):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
lead = "Host-interface checkpoint `a32d056` is pushed with 441 selected paths and four frozen packets. Fourteen exact logical-interface clarifications are selected after independent review; twelve external work inputs remain. The preceding `975b2e3` CI passes all six jobs and 64 steps, including the exact 103-command Rust 1.98.1 cache qualification. [Fresh CI](https://github.com/snowdamiz/mixer/actions/runs/40523809565) is queued. The outer-parent source now has bounded acceptance after 964 assertions and one successful compiler-only check with owned cleanup; this later acceptance is not included in that push. Its new work/storage, actual immutable binding and all three selectors remain pending. String review and compiled native-open correspondence continue. Canonical product source, native runtime and GA status are unchanged."
for name in ("PLAN.md", "STATUS.md"):
    text = (ROOT / name).read_text()
    marker = "## Resumed checkpoint\n\n" if name == "PLAN.md" else "# Implementation status\n\n"
    assert marker in text
    text = text.replace(marker, marker + lead + "\n\n", 1)
    (ROOT / name).write_text(text)
print(json.dumps({"acceptance": str((OUT / NAME).relative_to(ROOT)), "sha256": sha(OUT / NAME),
    "independent_members": 42, "conditional_I": 1, "conditional_U": 3,
    "new_prices_or_binding_selected": False, "delivery": delivery["commit"], "CI": runs[0]["databaseId"]}))

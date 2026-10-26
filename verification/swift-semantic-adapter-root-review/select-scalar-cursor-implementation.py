"""Accept isolated Rust host component and select closed CI candidate preparation."""
import datetime, hashlib, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok, message):
    if not ok: raise ValueError(message)
target = HERE / "scalar-cursor-implementation-selection.json"
require(not target.exists(), "Immutable selection exists")
packets = []
for name, expected, count, size in [
    ("swift-cache-state-scalar-cursor-implementation", "efc43d467a112522b40b4113bb21aa13086c0669d9d911707a85a148e3d4037c", 1682, 51805181),
    ("swift-cache-state-scalar-cursor-implementation-independent", "267905beda1bd6abdb4a83bbfe174c87258a5d432603306946ca88c047ba3f86", 85, 8863712),
]:
    base = ROOT / "verification" / name
    seal = base / "seal.json"
    require(sha(seal) == expected, "Seal identity")
    data = json.loads(seal.read_text()); rows = data["members"]
    require(len(rows) == count and sum(r["bytes"] for r in rows) == size, "Packet totals")
    seen = set()
    for row in rows:
        p = base / row["path"]
        require(p.resolve().is_relative_to(base.resolve()) and not p.is_symlink() and row["path"] not in seen, "Member path")
        seen.add(row["path"])
        require(p.stat().st_size == row["bytes"] and sha(p) == row["sha256"], row["path"])
    packets.append({"path": str(seal.relative_to(ROOT)), "sha256": expected, "members_verified": count, "bytes": size})
ind = ROOT / "verification/swift-cache-state-scalar-cursor-implementation-independent"
decision_path = ind / "final-decision.json"
require(sha(decision_path) == "89406604c3eac7d2943040e6ba591cdf7137d5e7dced74c552e3f1b4b17aaa86", "Decision identity")
d = json.loads(decision_path.read_text())
require(d["implementation_component_accepted"] and not d["canonical_integration_selected"], "Decision scope")
source = ROOT / "verification/swift-cache-state-scalar-cursor-implementation/source/library/cache_state.rs"
require(sha(source) == d["source_sha256"] == "f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b", "Selected source")
require(sha(HERE / "scalar-cursor-selection.json") == "2011535ad73055d52b8a11e8e2625f67c4c3d6b8e063cf2da69d2e497bfce024", "Conditional source proof")
require(d["producer_custody"]["final_methods_per_mode"] == [84, 108, 98] and d["producer_custody"]["distinct_methods_per_mode"] == 122, "Coverage")
require(d["full_Debug_60s_timeout_remains_failed"] and not d["performance_equivalence_claimed"], "Timing limitation")
require(d["combined_groups"] == 7048 and d["whole_role_union"] == 29344 and d["all_caps_unchanged"], "Proof bounds")
receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "argv": sys.argv, "python": sys.version, "selector_sha256": sha(pathlib.Path(__file__)), "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "packets": packets, "source_sha256": sha(source), "independent_decision_sha256": sha(decision_path), "decision": "Accept isolated exact-source Rust1.99.0 macOS arm64 host component; select separate closed standalone fixture CI pack/runner candidate", "producer_custody_and_results": d["producer_custody"], "independent_actual_controls": d["independent_actual_controls"], "complete_source_groups": d["work_groups"], "combined_groups": 7048, "whole_logical_union": 29344, "conditional_source_and_lifetime_proof_inherited_only": True, "general_public_File_admission_qualified": False, "canonical_runtime_or_full_target_integration_selected": False, "native_or_GA_qualified": False, "next_owned_scope": "verification/swift-cache-state-ci-preparation/** only; isolated deterministic pack and runner candidate using unchanged exact source, complete host/API/File/layout inventories and explicit bounded named Debug groups; independently review before canonical CI integration", "next_execution_authorized": "Bounded actual-host candidate runner checks, fixed source inventory and negative controls; no new compiler installation, arbitrary caller pack/hash overrides or old evidence writes. Preserve per-child60s and select explicit global deadline in proposed contract before execution.", "next_limits": ["Rust1.98.1 CI qualification pending; local Rust1.99.0 only accepted", "Native runtime/UI/capture/phones remain paused", "Historical selected comments remain explanatory limitations; no silent source hash normalization", "Original full Debug60s timeout remains failed; grouped coverage is not performance equivalence", "No source-work/runtime/ABI/RSS inference beyond exact conditional model", "No live VM/target, public release, signing/store, operational or separate-repository FieldLog qualification"]}
target.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"path": str(target.relative_to(ROOT)), "sha256": sha(target), "members_verified": 1767, "decision": receipt["decision"]}))

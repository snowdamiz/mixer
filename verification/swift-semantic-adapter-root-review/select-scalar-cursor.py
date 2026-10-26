"""Select exact source proof and authorize isolated compiler qualification once."""
import datetime, hashlib, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok, message):
    if not ok: raise ValueError(message)
target = HERE / "scalar-cursor-selection.json"
require(not target.exists(), "Selection already exists")
packets = []
for name, expected, count, size in [
    ("swift-cache-state-scalar-cursor-proposal", "3779a6ee9e8b38c2558e54ea4c8ae2e730ceb163b3ab154e7ee4003ef997475d", 41, 3437955),
    ("swift-cache-state-scalar-cursor-independent", "008dfbb9099d8a59bed142b6e578d96adf99e9b011120370de034bf728ed1aee", 54, 1351466),
]:
    base = ROOT / "verification" / name
    index = base / "seal.json"
    require(sha(index) == expected, "Seal identity")
    data = json.loads(index.read_text())
    require(data["member_base"] == "packet-relative", "Member base")
    rows = data["members"]
    require(len(rows) == count and sum(x["bytes"] for x in rows) == size, "Totals")
    seen = set()
    for row in rows:
        p = base / row["path"]
        require(p.resolve().is_relative_to(base.resolve()) and row["path"] not in seen and not p.is_symlink(), "Member path")
        seen.add(row["path"])
        require(p.stat().st_size == row["bytes"] and sha(p) == row["sha256"], row["path"])
    packets.append({"path": str(index.relative_to(ROOT)), "sha256": expected, "members_verified": count, "bytes": size})
ind = ROOT / "verification/swift-cache-state-scalar-cursor-independent"
decision = json.loads((ind / "final-decision.json").read_text())
source = ROOT / "verification/swift-cache-state-scalar-cursor-proposal/source/cache_state.rs.txt"
require(sha(source) == decision["source_sha256"] == "f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b", "Source")
caps = {"G3": 2568, "G4": 768, "G5": 640}
for group, expected in {"G3": (33799, 395, 2508), "G4": (10677, 33, 701), "G5": (7915, 66, 561)}.items():
    row = decision["bounds"][group]
    require((row["scalars"], row["copies"], row["groups"]) == expected, "Upper identity")
    require((row["scalars"] + 15) // 16 + row["copies"] == row["groups"] <= caps[group], "Unchanged cap")
anchors = {}
for name, expected in {
    "row-probe-G2-selection.json": "80d78642b67d9e8164532868e56bfc2bdbeb3fcd3b2756bd9b4580c06e0123bf",
    "G6-correction3-accounting-selection.json": "ea00518ce5033b4651460763f1c92533d024fee32a73b182d1684afa65ef80e1",
    "C3-lifetime-selection.json": "ab2e74fa3fa7a6ff967a5c0d000d46336cc42dc5654c6b38fdce008fcafedaf4",
    "C3-remaining-work-selection.json": "de4c117290000e9a71a5168f46cc184350bf37aa64c5714b9152bf888a08a67c",
}.items():
    require(sha(HERE / name) == expected, "Inherited selection")
    anchors[str((HERE / name).relative_to(ROOT))] = expected
niche = json.loads((ind / "inherited-niche-reconciliation.json").read_text())
for row in niche["scoped_selected_template_custody"]:
    require(sha(ROOT / row["path"]) == row["sha256"], "Inherited template custody")
command_file = ind / decision["final_command_receipt"]
command_receipt = json.loads(command_file.read_text())
require(command_receipt["all_passed"] and len(command_receipt["commands"]) == 2, "Final review executions")
for row in command_receipt["commands"]:
    require(row["exit"] == 0, "Review exit")
    for stream in ["stdout", "stderr"]:
        require(sha(command_file.parent / (row["name"] + "." + stream)) == row[stream + "_sha256"], "Review output")
require(decision["selected_niche_grammar_preserved"] and not decision["exact_once_actual_source_event_claim"], "Niche convention")
whole = {"Control": 1250, "Wire": 152, "Setup": 160, "Report": 2688}
allowances = {"Control": 1280, "Wire": 256, "Setup": 256, "Report": 2896}
require(decision["whole_added_peaks"] == whole and all(whole[k] <= allowances[k] for k in whole), "Whole lifetime")
require(24656 + sum(allowances.values()) == decision["whole_role_union"] == 29344, "Whole union")
groups = {"G1": 94, "G2": 2494, "G3": 2508, "G4": 701, "G5": 561, "G6": 512, "G7": 178}
require(sum(groups.values()) == decision["combined_production_G1_to_G7"] == 7048 <= 7680 and 7680 + 471 == 8151 <= 8192, "Combined cap")
receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "argv": sys.argv, "python": sys.version, "selector_sha256": sha(pathlib.Path(__file__)), "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "packets": packets, "source_sha256": sha(source), "independent_decision_sha256": sha(ind / "final-decision.json"), "inherited_selections": anchors, "niche_reconciliation_sha256": sha(ind / "inherited-niche-reconciliation.json"), "decision": "Accept exact conditional universal source argument, conservative work upper and scoped logical lifetime union; authorize isolated Rust host implementation qualification", "complete_bounds": decision["bounds"], "all_production_groups": groups, "combined_groups": 7048, "whole_added_peaks": whole, "whole_allowances": allowances, "whole_role_union": 29344, "retained_review_commands": str(command_file.relative_to(ROOT)), "retained_checks_each_mode": 6135941, "finite_merge_cases": 10486, "finite_prefix_comparisons": 9256, "negative_controls": 14, "producer_exact_totals_selected": False, "optional_duplicate_niche_copy_charges": 21, "selected_niche_scalar_grammar_changed": False, "canonical_integration_selected": False, "full_target_retry_selected": False, "Rust_compiler_or_implementation_accepted": False, "native_or_public_File_or_GA_accepted": False, "next": "Copy frozen C3 closure to new owned packet; replace only cache_state.rs with exact selected source; execute existing actual Rust Debug/-O host/regression/API/layout/File controls plus justified changed-source controls; independently review before any canonical integration", "limits": "Logical role inventory within selected caller boundary; no machine stack, ABI, library allocator/RSS or arbitrary-depth forwarding bound. Conditional G2 arena stability and public File reachability remain separate."}
target.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"path": str(target.relative_to(ROOT)), "sha256": sha(target), "members_verified": 95, "groups": groups, "whole_union": 29344}))

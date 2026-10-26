#!/usr/bin/env python3
"""Independent design/custody checks; NO product or candidate execution."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
EXPECTED = ("clean", "terminal-at-entry", "terminal-before-return", "dirty-at-entry",
            "dirty-before-return", "ordinary-throw-after-callback", "fatal-throw-after-callback")


def load(name):
    return json.loads((HERE / name).read_text())


def main():
    assertions = 0
    def check(value, message):
        nonlocal assertions
        assertions += 1
        if not value:
            raise AssertionError(message)
    custody = load("input-custody.json")
    check(custody["candidate_access"] is False, "candidate access attestation")
    check(custody["native_runtime_or_capture_started"] is False, "pause attestation")
    check(custody["process_discovery"] is False, "no process discovery attestation")
    check(custody["baseline_revision"] == "0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c", "baseline")
    bypath = {}
    for item in custody["allowed_inputs"]:
        path = HERE / item["snapshot"]
        check(path.is_relative_to(HERE), "input remains under owned snapshot")
        b = path.read_bytes()
        check(len(b) == item["bytes"] and hashlib.sha256(b).hexdigest() == item["sha256"], item["path"])
        bypath[item["path"]] = item
    selection_path = "verification/android-private-owner-effect-integration-root-review/implementation-selection.json"
    check(bypath[selection_path]["sha256"] == "d698ad2ca8ed0706038a652a5b665bb8818fdc4388ffaf34194a73bec11ab6aa", "exact selection")
    s = load("inputs/" + selection_path)
    check((len(s["packets"]), s["unique_members"], s["unique_bytes"]) == (7, 303, 5595445), "accepted packet counts")
    check(s["profile_id_selected"] == "mixer.android-source-pair.3" and not s["profile_hashes_selected"], "profile root hash gate")
    roster_path = "verification/android-private-owner-effect-roster-amendment/required-host-roster.json"
    r = load("inputs/" + roster_path)
    m = load("inputs/verification/android-private-owner-effect-roster-amendment/manifest.json")
    admitted_m = next(x for x in s["packets"] if x["manifest"] == "verification/android-private-owner-effect-roster-amendment/manifest.json")
    check(bypath[admitted_m["manifest"]]["sha256"] == admitted_m["sha256"], "amendment manifest selection")
    check(m["files"][roster_path] == {"bytes": bypath[roster_path]["bytes"], "sha256": bypath[roster_path]["sha256"]}, "roster manifest membership")
    check(len(r["baseline_callback_barriers"]) == 184 and len(r["v1_compile_baseline_only"]) == 5, "184 plus five")
    b_closure = r["closures"]["B-concrete-renderer-views"]
    check(len(b_closure["actual_production_sources"]) == 14, "14 actual subjects")
    check(len(b_closure["substitutes"]) == 73 and len({x["fqcn"] for x in b_closure["substitutes"]}) == 73, "73 concrete leaves")
    check(len(r["closures"]["A-orchestration"]["actual_production_sources"]) == 10, "actual orchestration closure")
    corepath = "native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java"
    check(bypath[corepath]["sha256"] == "4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6", "exact core baseline")
    site_map = load("site-input-map.json")
    check(site_map["new_candidate_sites"] is None and site_map["candidate_subject_hashes"] is None, "candidate facts intentionally unknown")
    check(site_map["leaf_reuse_admitted"] is False, "no premature leaf reuse")
    snapshots = {x.get("candidate_path", x["path"]): x for x in custody["allowed_inputs"] if x["source"] == "git-object-accepted-baseline"}
    all_ids = []
    for label, source_rows in [("v2_baseline_sites", r["baseline_callback_barriers"]), ("v1_baselines", r["v1_compile_baseline_only"])]:
        rows = site_map[label]
        check(len(rows) == len(source_rows), "site count " + label)
        for row, frozen in zip(rows, source_rows, strict=True):
            all_ids.append(row["id"])
            for key, value in frozen.items():
                check(row[key] == value, "immutable roster field " + row["id"] + "/" + key)
            source = (HERE / snapshots[row["source"]]["snapshot"]).read_bytes()
            lines = source.decode().splitlines(keepends=True)
            line = lines[row["line"] - 1].rstrip("\r\n")
            check(line.strip() == row["source_line"], "source line anchor")
            check(line[row["column"] - 1:].startswith(row["expression"]), "source column anchor")
            check(source[row["baseline_byte_offset"]:].startswith(row["expression"].encode()), "source byte offset anchor")
            check(row["baseline_source_sha256"] == hashlib.sha256(source).hexdigest(), "complete baseline bytes")
            check(row["candidate_binding"] is None and row["binding_status"] == "pending-root-candidate-admission", "no inferred candidate binding")
            if label == "v2_baseline_sites":
                check(tuple(row["required_cases"]) == EXPECTED, "all seven cases")
                check(row["independent_case_ids"] == [row["id"] + "/" + x for x in EXPECTED], "all seven generated rows")
            else:
                check(row["V2_semantic_requirements"] == [], "V1 not semantically V2")
    check(len(set(all_ids)) == 189, "unique complete baseline identities")
    cases = load("cases.json")
    check(cases["actual_candidate_access"] is False, "independent design attestation")
    matrix = cases["baseline_v2_matrix"]
    check(len(matrix) == 1288 and len({x["id"] for x in matrix}) == 1288, "1288 unique baseline rows")
    for row in site_map["v2_baseline_sites"]:
        variants = [x["variant"] for x in matrix if x["site_id"] == row["id"]]
        check(tuple(variants) == EXPECTED, "per-site case completeness")
    check(len(cases["positive_v1"]) == 5, "five positive V1 rows")
    subject_names = {Path(x).stem for x in b_closure["actual_production_sources"]}
    observed_subjects = set()
    check(len(cases["families"]) == 30, "independently authored family count")
    check(len({x["id"] for x in cases["families"]}) == 30, "family identities unique")
    for family in cases["families"]:
        check(family["execution_status"] == "not-run-preaccess-design", "honest family status")
        check(bool(family["setup"] and family["stimulus"] and family["observe"] and family["forbidden"] and family["positive_control"]), "concrete case design fields")
        check(set(family["actual_subjects"]) <= subject_names, "actual subjects within closure")
        observed_subjects.update(family["actual_subjects"])
    check(observed_subjects == subject_names, "all14 have planned actual body witnesses")
    opinion = load("clarification-opinion.json")
    check(opinion["sha256"] == bypath[opinion["path"]]["sha256"], "exact clarification bytes")
    check(opinion["sha256"] == "2a1574cea4d94b21bbf5d59b64484700ca7dcdf8d94fd3822fdf8fb63c5f0fa4", "reviewed clarification")
    check(opinion["opinion"] == "acceptable-as-mandatory-clarification" and not opinion["implementation_acceptance"] and opinion["root_selection_required"], "contract-only opinion")
    commands = load("commands.json")
    check(len(commands["now"]) == 4, "four now commands")
    check(commands["limits"]["concurrent_children"] == 1 and commands["limits"]["wall_seconds"] == 120, "bounded runner")
    check(set(commands["env_remove"]) == {"JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH"}, "implicit JVM options stripped")
    packet = load("packet-witness.json")
    nodes = []
    def visit(node):
        nodes.append(node)
        for child in node["children"]:
            visit(child)
    visit(packet["document"]["root"])
    check(len({x["id"] for x in nodes}) == len(nodes) == len(packet["identities"]), "independent witness identity structure only")
    check({x["kind"] for x in nodes} == {"navigation", "list", "section", "text", "textField", "toggle", "button"}, "positive witness planned kinds")
    plan = REPO / "docs/android-private-owner-implementation-review-plan.md"
    check(plan.is_file(), "owned review plan exists")
    check("no candidate" in plan.read_text() and "1,288" in plan.read_text(), "plan status and complete matrix")
    result = dict(status="passed-design-custody-only", assertions=assertions,
                  families=30, actual_subjects_planned=14, mechanical_leaves_pending_audit=73,
                  baseline_v2_sites=184, baseline_case_rows=1288, separate_v1_positive_rows=5,
                  multiple_selected_sites_on_one_line=sum(x["same_line_selected_count"] > 1 for x in site_map["v2_baseline_sites"]),
                  candidate_source_or_test_or_leaf_or_probe_access=False, product_tests_run=0,
                  candidate_mapping_new_sites_host_tests_crossbuild_profile_native_GA="pending",
                  tool=dict(python=sys.version), scope="independent preaccess design structural checks only")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

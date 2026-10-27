#!/usr/bin/env python3
"""Data-only final archive custody review; never execute archived code."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
Q = "verification/android-editor-membership-compiled-boundary-qualification"
STATE = Q + "/state-qualification"
ARCHIVE = REPO / (Q + "/selected-v4-composed-replay-review")
SEAL_SHA = "c06e384c26568f50be149a819bdf08259c03ab3e65ce867f1dc8477933bf8423"
RELEASE = "verification/android-editor-boundary-root-review/final-composed-archive-release.json"
RELEASE_SHA = "be6aed2c75d051b61deb46295cfab1cfdb60a1f22e08f06f068a7e0d9616b2ec"
ACCEPTANCE = "verification/android-editor-boundary-root-review/finite-observation-consistency-acceptance.json"
ACCEPTANCE_SHA = "65c6d0a51a21ef10a4ea9c814ab9c4223f2fc7ca79157fcec673555ed41dcd85"
FORBIDDEN = ("execution-closure-v5", "execution_closure_v5", "catalog-inspector", "authority-driver", "rejectedworkerv2", "broadhostedharness")
STATES = {"clean", "terminal-at-entry", "terminal-before-return", "dirty-at-entry", "dirty-before-return", "ordinary-throw-after-callback", "fatal-throw-after-callback"}

def need(condition, message):
    if not condition:
        raise ValueError(message)

def identity(path):
    size = 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(data)
            digest.update(data)
    return {"bytes": size, "sha256": digest.hexdigest()}

def same(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(same(a[key], b[key]) for key in a)
    if type(a) is list:
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b

def load(path):
    return json.loads(path.read_bytes())

def screen(name):
    need(type(name) is str and not Path(name).is_absolute() and ".." not in Path(name).parts and str(Path(name)) == name and not any(word in name.lower() for word in FORBIDDEN), "forbidden or unbounded archive path")

def verify_archive():
    need(identity(ARCHIVE / "seal.json")["sha256"] == SEAL_SHA, "root-selected exact final archive seal")
    seal = load(ARCHIVE / "seal.json")
    members = seal["members"]
    for member in members:
        screen(member["path"])
        need(type(member["bytes"]) is int and member["bytes"] >= 0, "exact member byte count")
    expected = {item["path"] for item in members}
    need(len(expected) == len(members) == seal["member_count"] == 3339 and sum(item["bytes"] for item in members) == seal["member_bytes"] == 446053962, "exact3339 archive member/count/bytes")
    nodes = list(ARCHIVE.rglob("*"))
    need(not ARCHIVE.is_symlink() and not any(path.is_symlink() for path in nodes), "no archive symlink")
    need({str(path.relative_to(ARCHIVE)) for path in nodes if path.is_file()} == expected | {"seal.json"}, "closed exact archive filesystem pathset")
    for member in members:
        need(identity(ARCHIVE / member["path"]) == {key: member[key] for key in ("bytes", "sha256")}, "archive member identity: " + member["path"])
    manifest = load(ARCHIVE / "MANIFEST.json")
    need(identity(ARCHIVE / "MANIFEST.json")["sha256"] == seal["manifest_sha256"], "manifest hash bound by external seal")
    need(same(manifest["members"], [item for item in members if item["path"] != "MANIFEST.json"]) and manifest["member_count"] == 3338 and manifest["member_bytes"] == 445049039, "manifest and seal exact member mapping")
    need(seal["canonical_native_OTA_GA_accepted"] is False, "archive grants no runtime acceptance")
    return seal

def main():
    started = time.monotonic()
    need(not (OUT / "review-seal.json").exists(), "review lane already frozen")
    prior_files = {str(path.relative_to(OUT)): identity(path) for path in OUT.rglob("*") if path.is_file()}
    need(identity(REPO / RELEASE)["sha256"] == RELEASE_SHA and identity(REPO / ACCEPTANCE)["sha256"] == ACCEPTANCE_SHA, "exact root custody and finite-scope selections")
    acceptance = load(REPO / ACCEPTANCE)
    finite_receipt = OUT / "canonical84-composition-independent-review.json"
    need(identity(finite_receipt) == {key: acceptance["independent_receipt"][key] for key in ("bytes", "sha256")}, "prior independent finite receipt unchanged")
    seal = verify_archive()
    member_map = {item["path"]: {key: item[key] for key in ("bytes", "sha256")} for item in seal["members"]}
    refs = {name[len("reference-tree/"):]: value for name, value in member_map.items() if name.startswith("reference-tree/")}
    need(len(refs) == 3331 and sum(item["bytes"] for item in refs.values()) == 443046702, "exact3331 source-path reference mapping")
    def archived(relative):
        need(relative in refs, "missing exact archived source path: " + relative)
        return ARCHIVE / "reference-tree" / relative
    packet_seals = {
        "offline-reconciler-v3": acceptance["source_v3_seal"],
        "offline-reconciler-run3": acceptance["output_v3_seal"],
        "canonical-query-offline-addendum-v1": acceptance["canonical_query_source_seal"],
        "canonical-query-offline-run1": acceptance["canonical_query_output_seal"],
        "original98-offline-join-addendum-v1": acceptance["original98_source_seal"],
        "original98-offline-join-run1": acceptance["original98_output_seal"],
    }
    mapped_packet_members = 0
    mapped_manifest_inputs = 0
    for packet, expected_sha in packet_seals.items():
        base = STATE + "/" + packet
        need(refs[base + "/seal.json"]["sha256"] == expected_sha, "composed source/output exact accepted seal")
        document = load(archived(base + "/seal.json"))
        for member in document["members"]:
            name = base + "/" + member["path"]
            need(refs[name] == {key: member[key] for key in ("bytes", "sha256")}, "composed packet's member path maps exactly")
            mapped_packet_members += 1
        manifest_name = base + "/input-manifest.json"
        if manifest_name in refs:
            for member in load(archived(manifest_name))["files"]:
                screen(member["path"])
                need(refs[member["path"]] == {key: member[key] for key in ("bytes", "sha256")}, "archived exact utility/data manifest path maps without substitution")
                mapped_manifest_inputs += 1
    staged = load(ARCHIVE / "staged-input-copy-custody.json")
    need(len(staged["files_source_map"]) == staged["files"] == 3305 and sum(item["bytes"] for item in staged["files_source_map"]) == staged["member_bytes"] == 411990143, "staged historical copy mapping")
    for member in staged["files_source_map"]:
        need(refs[member["path"]] == {key: member[key] for key in ("bytes", "sha256")}, "all staged copies retained unchanged")
    ledger_name = STATE + "/offline-reconciler-run3/complete-proved-unresolved-ledger.json"
    need(refs[ledger_name]["sha256"] == "e14e2fbeed50a822584f0c1a6e2418a300712c31df431789548e31ce84f4e85e", "exact previously reviewed complete v3 ledger")
    ledger = load(archived(ledger_name))
    query_name = STATE + "/canonical-query-offline-run1/canonical84-query-join.json"
    original_name = STATE + "/original98-offline-join-run1/original98-joined.json"
    need(identity(OUT / "canonical84-independent-join.json") == refs[query_name] and identity(OUT / "original98-copied-fresh-join.json") == refs[original_name], "archived composed outputs byte-equal independent fresh results")
    query, original98 = load(archived(query_name)), load(archived(original_name))
    need(original98["unique_actual_commands"] == 98 and original98["historical_passed_aliases"] == 99 and original98["qualified"] is False, "original98/99 remains receipt/data scope")
    baseline_name = Q + "/semantic-review-candidate-v1/active-semantic-obligations.json"
    history_name = Q + "/semantic-review-candidate-v1/historical189-current-bindings.json"
    need(refs[baseline_name]["sha256"] == "8f6ec3cf034c3b07361bcb1f17a7a1ba38344d951803c625d03be67cbc14f112", "original280 authority identity")
    baseline, history = load(archived(baseline_name)), load(archived(history_name))
    bysubject = {item["id"]: item for item in baseline["subjects"]}
    byhistory = {item["historical_id"]: item for item in history["records"]}
    need(len(bysubject) == len(ledger["subjects"]) == 280 and len(byhistory) == len(ledger["historical189"]) == 189, "exact original whole inventory cardinality")
    pending = load(ARCHIVE / "complete-unresolved-ledger.json")
    summary = load(ARCHIVE / "summary.json")
    missing = load(ARCHIVE / "missing-selected-native-completions.json")
    projected_subjects = []
    for subject in ledger["subjects"]:
        record = subject["original_subject"]
        need(same(record, bysubject[record["id"]]) and same(subject["original_required_cases_retained"], record["required_semantic_cases"]), "all original subject fields/cases/instructions preserved")
        need(subject["qualification_status"] == "pending-source-specific-required-case-and-outcome-review", "original subject never promoted")
        projected_subjects.append({"subject_id": record["id"], "class": record["class"], "method": record["method"], "descriptor": record["descriptor"], "original_categories": record["categories"], "source_sha256": record["source_sha256"], "class_sha256": record["class_sha256"], "original_case_obligations": [{"case_id": case, "status": "pending-source-specific-applicability-oracle-and-complete-outcome-join"} for case in record["required_semantic_cases"]], "finite_facet_count": len(subject["finite_facets"]), "actual_native_caller_observation_count": len(subject["actual_native_caller_observations"]), "actual_enclosing_frame_observation_count": len(subject["actual_frame_observations"]), "complete_semantic_qualification": False})
    need(same(projected_subjects, pending["subjects"]) and pending["original_case_count"] == sum(len(item["required_semantic_cases"]) for item in bysubject.values()) == 2705, "exact complete pending280/2705 projection")
    projected_history = []
    for record in ledger["historical189"]:
        need(same(record["original_binding"], byhistory[record["historical_id"]]), "all189 whole original history bindings unchanged")
        observed = [item["state"] for item in record["actual_state_observations"]]
        need(len(observed) == 7 and set(observed) == STATES and record["status"] == "pending-disposition-and-outcome-review", "each original historical ID has seven exact unresolved states")
        projected_history.append({"historical_id": record["historical_id"], "observed_canonical_states": observed, "exact_seven_observations": True, "full_disposition_and_outcome_qualification": "pending"})
    need(same(projected_history, pending["historical189"]), "historical unresolved projection does not borrow qualification")
    raw_rows = [(file, index, row) for file in ledger["files"] for index, row in enumerate(file.get("rows", []), 1)]
    projected_missing = []
    for file, index, row in raw_rows:
        expected_missing = row["selected_events"] > 0 and row["selected_native_completions"] == 0
        need(type(row["missing_selected_native_completion"]) is bool and row["missing_selected_native_completion"] == expected_missing, "every selected missing-completion flag reflects actual recorded absence")
        if expected_missing:
            need(row["actual_selected_native_typed_outcomes"] == [], "missing native completion has no invented typed outcome")
            projected_missing.append({"file": file["file"], "row": index, "state": row["state"], "historical_id": row["historical_id"], "family": row["family"], "selected_events": row["selected_events"], "status": "no selected recorded native completion; exact result/body outcome pending"})
    need(same(projected_missing, missing["rows"]) and len(projected_missing) == missing["missing_selected_native_completion_rows"] == 844, "all844 precise missing-completion row identities retained")
    need(sum(row["selected_events"] > 0 for file, index, row in raw_rows) == missing["selected_event_rows"] == 1503, "selected event row count is separate from completions")
    need(sum(row["selected_native_completions"] for file, index, row in raw_rows) == 665, "recorded typed observations counted separately")
    rawfiles = {file["file"]: file for file in ledger["files"] if "rows" in file}
    for row in query["rows"]:
        report = rawfiles[row["file"]]["rows"][row["row"] - 1]
        need(row["state"] == report["state"] and row["selected_events"] == report["selected_events"] and row["v3_report_unchanged"] is True, "canonical gate points to exact unchanged ledger row")
        if row["selected_events"] == 0:
            need(report["selected_native_completions"] == 0 and report["actual_selected_native_typed_outcomes"] == [], "zero-selected query row receives no native completion credit")
    parent = load(archived(STATE + "/full-candidate-v1/run-33/receipt.json"))
    recovery = load(archived(STATE + "/run33-single-state-recovery/receipt.json"))
    need(len(parent["commands"]) == 327 and parent["all_commands_passed"] is False and [item["label"] for item in parent["commands"] if item["exit"] != 0 or item["timeout"]] == ["boundary-019"], "original parent timeout retained")
    need("boundary-019.rows.jsonl.gz" not in rawfiles and ledger["bounded_recovery"]["failed_parent_retained"] is True and len(ledger["bounded_recovery"]["excluded_partial_files"]) == 1, "entire failed partial excluded from selected rows")
    need(len(recovery["commands"]) == 10 and recovery["failed_parent_promoted"] is False and recovery["all_commands_passed"] is True, "ten separate bounded recovery commands, no parent promotion")
    expected_counts = {"product_sources": 16, "product_classes": 209, "actual_parent_compiled_sources": 143, "actual_parent_emitted_classes": 464, "separate_frozen_Focus_classes": 5, "additional_recovery_driver_classes": 1, "parent_commands": 327, "parent_passed_commands": 326, "actual_original_commands": 98, "passed_historical_original_aliases": 99, "raw_compact_files": len(rawfiles), "raw_compact_rows": len(raw_rows), "finite_files": sum("finite_invocations" in item for item in ledger["files"]), "finite_invocations": sum(item.get("finite_invocations", 0) for item in ledger["files"]), "selected_external_field_observation_invocations": 56, "separate_V1_sites": len(ledger["separate_five_V1_positives"]), "exact38_compiled_descriptor_bindings": len(ledger["exact38_compiled_bindings"]), "historical_V2_ids": 189, "historical_V2_state_observations": 1323, "missing_selected_native_completion_rows": 844, "canonical_query_rows": query["actual_query_rows"], "canonical_query_selected_event_rows": query["selected_event_rows"], "canonical_query_zero_selected_rows": query["zero_selected_event_rows"]}
    for key, value in expected_counts.items():
        need(type(summary[key]) is int and summary[key] == value, "summary count derived independently: " + key)
    need(summary["failed_parent_promoted"] is False and summary["source_integration_default_matrix_CI_native_OTA_GA_accepted"] is False and pending["qualified"] is False and missing["qualified"] is False, "summary and detailed outputs retain nonqualification")
    need(same(pending["unresolved_checker_obligations"], ledger["unresolved_checker_obligations"]) and len(pending["additional_required_limits"]) == 7, "all generic descriptor, semantic and runtime gaps retained")
    readme = (ARCHIVE / "README.md").read_text()
    need("moving that utility to another root requires an explicitly reviewed path mapping" in readme and "not an approved portable runtime/bootstrap" in readme, "original98 relocation boundary stated plainly")
    compile_command = next(item for item in parent["commands"] if item["label"] == "compile")
    recorded_compile_sources = {item for item in compile_command["argv"] if item.endswith(".java")}
    freeze = load(archived(STATE + "/full-candidate-v1/run-33/source-freeze.json"))
    need(recorded_compile_sources == {str(REPO / item["path"]) for item in freeze["sources"]}, "original98 absolute compile-root authority preserved")
    relocated_root = ARCHIVE / "reference-tree"
    need(recorded_compile_sources != {str(relocated_root / item["path"]) for item in freeze["sources"]}, "archive relocation is not silently treated as original execution paths")
    source_freeze = identity(Path(__file__))
    verify_archive()
    for name, expected in prior_files.items():
        need(identity(OUT / name) == expected, "prior independent review file changed: " + name)
    result = {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "accepted-final-archive-byte-custody-and-finite-data-consistency-only; full-matrix-unqualified", "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version, "platform": platform.platform(), "source_revision_context": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip(), "review_script": source_freeze,
        "archive": {"path": str(ARCHIVE.relative_to(REPO)), "seal_sha256": SEAL_SHA, "member_count": 3339, "member_bytes": 446053962, "reference_tree_paths": 3331, "manifest_and_closed_pathset_equal": True, "entry_exit_all_members_verified": True, "all_paths_screened_before_member_reads": True, "forbidden_paths": [], "symlinks": []},
        "root_release_sha256": RELEASE_SHA, "finite_root_acceptance_sha256": ACCEPTANCE_SHA, "six_composed_packets_exact": packet_seals, "composed_packet_member_mappings": mapped_packet_members, "composed_input_manifest_mappings_including_overlap": mapped_manifest_inputs, "staged_historical_copy_mappings": 3305, "prior_finite_independent_receipt": identity(finite_receipt), "all_prior_independent_files_unchanged": True, "prior_independent_file_count": len(prior_files),
        "exact_preservation": {"whole_original_subjects": 280, "all_pending_original_cases": 2705, "whole_original_historical_bindings": 189, "exact_historical_state_keys": 1323, "separate_V1_sites": 5, "original_java_invocations": 98, "historical_passing_aliases": 99, "product_context": summary["product_context_id"], "exact_product_sources": 16, "exact_product_classes": 209},
        "derived_counts": expected_counts, "missing_completions": {"rows": 844, "all_row_state_family_historical_identities_reconstructed": True, "all_actual_selected_typed_outcomes_empty": True, "selected_event_rows": 1503, "recorded_selected_typed_observations": 665, "missing_body_results_never_inferred": True},
        "original98_path_relocation": {"recorded_original_root": str(REPO), "archive_reference_root": str(relocated_root), "recorded_compile_source_paths": len(recorded_compile_sources), "original_root_compile_mapping_matches": True, "archive_root_compile_mapping_matches": False, "scope": "Evidence byte custody only. Archived original98 source derives the archive reference-tree as REPO while argv retain original absolute paths. Running or relocating it requires an explicitly reviewed path mapping; no archived code was executed and no standalone execution closure is accepted."},
        "pending": pending["unresolved_checker_obligations"] + pending["additional_required_limits"], "limits": ["Finite observation/receiver/serialization/alias data consistency and archive byte custody only; all2705 original required cases remain pending.", "Generic public-result/public-descriptor and native-completion/compiled-callee descriptor work belongs to a separate active lane and was not accessed.", "Retained failed parent, superseded v1/v2 and mixed-authoring outputs remain historical; no passing status is borrowed.", "Complete execution closure, canonical integration/default matrix/CI, native runtime, OTA and GA remain unaccepted. Stopped experiment and latest child-cleanup uncertainty remain uninvestigated.", "No archived code, product/Java corpus, native/UI/capture or process inventory was executed in this final review."], "archived_code_executed": False, "Java_or_native_execution": False, "full225_file_replay": False, "children_started": 0, "elapsed_seconds": time.monotonic() - started, "blocking_archive_findings": [], "full_matrix_accepted": False, "qualified": False,
    }
    (OUT / "final-archive-independent-review.json").write_text(json.dumps(result, indent=2) + "\n")
    (OUT / "FINAL_REVIEW.md").write_text("Accepted the exact 3,339-member final archive for byte custody and the already reviewed finite observation-data consistency composition. All 280 whole original subjects, 2,705 pending cases, 189 whole historical bindings across seven states, 98 invocations/99 aliases, and five separate V1 sites are retained. All 844 missing selected-completion rows are reconstructed exactly and receive no invented typed outcomes. The failed parent remains failed; its partial gzip is excluded.\n\nThe archive preserves exact v3, canonical84 and original98 outputs and their immutable source/input identities. Original98 recorded compile paths remain absolute to the original repository. The archive reference tree is an evidence copy; relocation or execution requires an explicitly reviewed path mapping. No archived code was run.\n\nThere are no blocking archive-custody findings. Generic public-result/callee descriptor joins, original semantic/body/helper/enclosing/allocation outcomes, execution closure, canonical integration/default matrix/CI, native runtime, OTA and GA remain pending. This is not full matrix qualification. The separate active descriptor lane was not accessed.\n")
    members = [{"path": str(path.relative_to(OUT)), **identity(path)} for path in sorted(OUT.rglob("*")) if path.is_file()]
    need(identity(Path(__file__)) == source_freeze, "independent review source unchanged")
    review_seal = {"schema": 1, "status": "frozen-independent-final-archive-custody-and-finite-consistency-review; not-qualified", "archive_seal_sha256": SEAL_SHA, "members": members, "member_count": len(members), "member_bytes": sum(item["bytes"] for item in members), "all_prior_receipts_retained_unchanged": True, "full_matrix_canonical_native_OTA_GA_accepted": False}
    (OUT / "review-seal.json").write_text(json.dumps(review_seal, indent=2) + "\n")
    print(json.dumps({"archive_members": 3339, "archive_bytes": 446053962, "whole_original_subjects": 280, "pending_cases": 2705, "historical_state_keys": 1323, "exact_missing_completion_rows": 844, "blocking_archive_findings": 0, "review_members": len(members), "review_seal": identity(OUT / "review-seal.json"), "qualified": False}))

if __name__ == "__main__":
    main()

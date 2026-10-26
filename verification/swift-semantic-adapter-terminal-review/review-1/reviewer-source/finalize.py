"""Seal only reviewer-owned evidence; producer source is never executed."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[2]
PRE = OUT.parent / "preaccess"


def sha(data): return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    if (OUT / "seal.json").exists(): raise RuntimeError("Review already sealed")
    normal = json.loads((OUT / "results/normal/result.json").read_text())
    optimized = json.loads((OUT / "results/optimized/result.json").read_text())
    if {k:v for k,v in normal.items() if k != "mode"} != {k:v for k,v in optimized.items() if k != "mode"}:
        raise RuntimeError("Normal and optimized results differ")
    commands = OUT / "commands/finalization"
    commands.mkdir(parents=True, exist_ok=True)
    for name, argv in [("python-version", [sys.executable, "--version"]),
                       ("git-version", ["git", "--version"]),
                       ("revision", ["git", "rev-parse", "HEAD"]),
                       ("producer-classifier-text-read", ["cat", "verification/swift-semantic-adapter-terminal-correction/classifier.py"])]:
        r = subprocess.run(argv, cwd=ROOT, capture_output=True)
        (commands / (name + ".stdout")).write_bytes(r.stdout)
        (commands / (name + ".stderr")).write_bytes(r.stderr)
        dump(commands / (name + ".json"), {"argv":argv, "cwd":str(ROOT), "exit_code":r.returncode,
             "stdout_sha256":sha(r.stdout), "stderr_sha256":sha(r.stderr)})
        if r.returncode: raise RuntimeError((name, r.returncode))
    cleanup = []
    cache = OUT / "reviewer-source/__pycache__"
    if cache.exists():
        for p in cache.iterdir():
            if not p.is_file() or p.suffix != ".pyc": raise RuntimeError("Unexpected owned scratch " + str(p))
            cleanup.append({"path":str(p.relative_to(OUT)), "bytes":p.stat().st_size, "sha256":sha(p.read_bytes())})
            p.unlink()
        cache.rmdir()
    dump(OUT / "cleanup.json", {"removed_owned_python_bytecode":cleanup,
         "native_capture_processes_started_or_queried":False, "other_project_processes_queried_or_changed":False,
         "persistent_review_processes":0})
    fields = json.loads((OUT / "results/normal/field-coverage.json").read_text())
    schema = json.loads((PRE / "cases.json").read_text())["word_order"]
    expressions = ["selected boundary", "selected reason", "coherent framing N", "pre-terminal supported M", "selected terminal stop",
        "last checked sequence M", "Q work", "Q instructions", "stage-active op else0", "stage-active function elseMAX",
        "Q resident count", "Q resident bytes", "Q held pins", "Q next nonce", "stage>=3 functionmod512 elseMAX",
        "stage>=6 selected else0", "stage>=6 taken else0", "stage>=6 committed else0", "stage7/8 pending elseMAX",
        "planned and feasible destination elseMAX", "first Failure stop else0", "actual paid D", "actual setup-paid SS", "actual finish-paid SF",
        "visible1 or suppressed0", "selected visible tail or suppressed0", "literal false", "literal false", "literal false", "literal false", "reserved zero", "reserved zero"]
    dump(OUT / "coverage-map.json", {
        "source_normalization":"results/normal/source-normalization.json",
        "terminal_rows":"results/normal/terminal-coverage.json",
        "snapshot_header_guards":"results/normal/malformed-controls.json",
        "preaccess_scenarios":"results/normal/preaccess-disposition.json",
        "exact_error_sites":"results/normal/exact-error-partition.json",
        "paid_and_pending_source_controls":"results/normal/funding-latch-controls.json",
        "fields":[{"word":i, "name":name, "independent_expression":expressions[i], "witnesses":fields["all32words"][name],
                   "correction_reference":"docs/swift-semantic-adapter-terminal-correction.md:169-216",
                   "actual_semantic_snapshot_provenance":"pending implementation"} for i,name in enumerate(schema)],
        "all16_rows":True, "all32_fields":True, "all11_stages":True, "all13_child_source_branches":True,
        "full_semantic_transition_matrix_executed":False})
    obligations = {
        "C01":"Exact original/correction/preaccess bytes and actual accepted child sources bound; current live VM relation unavailable.",
        "C02":"Original additive safe-File/private loan/old API-report isolation retained as contract; future executable regression/provenance proof pending.",
        "C03":"R1 resolved for source-contract scope by ordered16row table, all32word projection, exact caught/outer error partition and absorbing/read guards.",
        "C04":"Closed field design retained; exhaustive semantic field/transition mutation and actual-File evidence remains unrun.",
        "C05":"Successful copied-source resident/token/plan/victim rules unchanged; row-semantic proof is not supplied by terminal shape guards.",
        "C06":"Single Candidate cleanup/restore and both-leaf poison policy unchanged; actual Rust borrow/all-exit proof pending.",
        "C07":"All global/work declarations unchanged; exact new Rust/caller/Result/debit ledger unproved.",
        "C08":"All memory/layout predictions unchanged; fresh layouts, simultaneous lifetime/move/source-destination/caller proof unproved.",
        "C09":"All authority false; real adapters and historical invalid-sidecar upgrades unavailable.",
        "C10":"Separate independent source/finite review provided; root acceptance/selection and implementation acceptance remain separate."}
    dump(OUT / "findings.json", {
        "schema":1, "verdict":"recommend bounded R1 source-contract acceptance with original combined constraints",
        "blocking_findings":[], "R1_status":"resolved in reviewed source-contract scope", "original_combined_obligations":obligations,
        "implementation_selection":False, "implementation_acceptance":False, "source_work_layout_lifetime_proved":False,
        "conditions_before_implementation_acceptance":[
            "exact private framing/envelope/debit-audited loan provenance and config/arena borrow arrangement",
            "actual paid receipt construction and tag/latch/call invariants; private paid-domain exclusions are not runtime passes",
            "complete independent semantic field/transition and actual-File controls from empty construction",
            "single Candidate2048 all-exit in-place clear/12word restore and both-leaf poison proof",
            "exact combined source-work, error/report/caller/Result accounting within unchanged ceilings",
            "fresh compiler layouts and simultaneous lexical lifetime/source-destination/caller ownership inventory"],
        "method_limitations":[
            "finite handwritten source/contract models, not Rust or product execution",
            "producer literals compared as data; producer classifier never imported/executed",
            "initial admitted document display preceded full snapshot; all members verified before substantive model work; preaccess already sealed",
            "existing envelope CI reported by root is separate and does not qualify new semantics"],
        "Rust_product_tests":0, "native_device_GA":False})
    doc = ROOT / "docs/swift-semantic-adapter-terminal-review.md"
    (OUT / "review.md").write_bytes(doc.read_bytes())
    sources = [{"path":str(p.relative_to(OUT)), "bytes":p.stat().st_size, "sha256":sha(p.read_bytes())}
               for p in sorted((OUT / "reviewer-source").glob("*.py"))]
    source_tree = sha("".join(r["path"] + "\0" + r["sha256"] + "\n" for r in sources).encode())
    input_tree = sha((OUT / "candidate-snapshot-manifest.json").read_bytes() + (OUT / "candidate-seal.json").read_bytes()
                     + (PRE / "seal.json").read_bytes() + (OUT / "root-admission.json").read_bytes())
    dump(OUT / "source-manifest.json", {"sources":sources, "source_tree_sha256":source_tree, "input_tree_digest_sha256":input_tree})
    dump(OUT / "final-receipt.json", {
        "schema":1, "at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status":"independent source-contract acceptance recommendation; root decision pending",
        "model":"gpt-6.1-sol", "reasoning_effort":"xhigh", "fresh_context":True,
        "command":["python3", "-B", "verification/swift-semantic-adapter-terminal-review/review-1/reviewer-source/finalize.py"],
        "source_tree_sha256":source_tree, "input_tree_digest_sha256":input_tree, "review_document_sha256":sha(doc.read_bytes()),
        "preaccess_seal_sha256":"b71097292535a76631d787121c60e315f91343ed6da8c71fec9303cf9328e681",
        "correction_seal_sha256":"efa9288096a692780e195ac519ffb7ed0be1280a974e830d80fc9932d194aef7",
        "methods_per_mode":normal["methods_passed"], "checks_per_mode":normal["checks_passed"], "normal_optimized_equal":True,
        "counts_include_source_custody_checks":True, "raw_child_source_finite_cases_per_mode":19635, "terminal_cartesian_cases_per_mode":3360,
        "all16rows_all32fields_all13childbranches":True, "frozen_preaccess_scenarios":114, "finite_contract_instantiations":111,
        "typed_private_paid_domain_exclusions":3, "frozen_projection_fixtures":7, "frozen_full32_counterexamples":64,
        "independent_source_ranges":24, "exact_source_error_sites":28, "producer_literals_read_only":{"projection":56,"normalization":41},
        "Rust_product_tests":0, "native_device_GA":False, "producer_model_execution":False, "old_harness_execution":False,
        "live_VM_read_or_run":False, "process_discovery_UI_capture_native_calls":0,
        "product_profile_dependency_CI_root_metadata_git_index_commit_push_changes":False,
        "remaining_proofs":"source-work/layout/caller/lifetime/actual semantic behavior and full product qualification pending",
        "preserved_attempts":["commands/run-1", "commands/run-2", "commands/authoring-failure-1.json"],
        "authoring_failures":1, "verification_failures":0})
    inspected = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.relative_to(OUT).parts[0] in {"candidate-snapshot", "commands"}: continue
        try: text = path.read_text()
        except UnicodeDecodeError: continue
        bad = [i for i,line in enumerate(text.splitlines(),1) if line.rstrip(" \t") != line]
        if bad: raise RuntimeError((str(path),bad))
        inspected.append(str(path.relative_to(OUT)))
    dump(OUT / "whitespace.json", {"explicit_owned_files_checked":inspected, "trailing_whitespace_findings":0})
    members = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path in {OUT / "seal.json", OUT / "seal.sha256"}: continue
        data = path.read_bytes()
        members.append({"path":str(path.relative_to(OUT)), "bytes":len(data), "sha256":sha(data)})
    seal = {"schema":1, "scope":"independent R1 source-contract review only; no implementation acceptance",
            "excluded":["seal.json", "seal.sha256"], "member_count":len(members), "member_bytes":sum(r["bytes"] for r in members),
            "preaccess_seal_sha256":"b71097292535a76631d787121c60e315f91343ed6da8c71fec9303cf9328e681",
            "candidate_seal_sha256":"efa9288096a692780e195ac519ffb7ed0be1280a974e830d80fc9932d194aef7", "members":members}
    raw = (json.dumps(seal, indent=2, sort_keys=True) + "\n").encode()
    (OUT / "seal.json").write_bytes(raw)
    (OUT / "seal.sha256").write_text(sha(raw) + "  seal.json\n")
    print(json.dumps({"review_seal_sha256":sha(raw), "members":len(members), "member_bytes":seal["member_bytes"],
          "review_document_sha256":sha(doc.read_bytes()), "methods_per_mode":normal["methods_passed"],
          "checks_per_mode":normal["checks_passed"], "R1":"source-contract acceptance recommended",
          "Rust_product_tests":0, "root_selection":False}, indent=2))


if __name__ == "__main__": main()

"""Freeze only this independent review; recheck released immutable members."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def ident(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": sha(raw)}

def write(name, value):
    (OWN / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def main():
    assert not (OWN / "review-seal.json").exists(), "frozen review must not be rewritten"
    before = json.loads((OWN / "preparation-custody.json").read_bytes())
    after = []
    for packet in before["packets"]:
        path = ROOT / packet["path"]
        assert ident(path)["sha256"] == packet["sha256"]
        members = json.loads(path.read_bytes())["members"]
        assert len(members) == packet["members"]
        assert sum(m["bytes"] for m in members) == packet["member_bytes"]
        for item in members:
            member = path.parent / item["path"]
            assert not member.is_symlink()
            assert ident(member) == {k: item[k] for k in ("bytes", "sha256")}
        after.append({**packet, "postexecution_manifest_match": True})
    release = ROOT / "verification/android-editor-boundary-root-review/generic-descriptor-correction-independent-release.json"
    assert ident(release)["sha256"] == "b014e89e900634716e6c80f20c8fea95f63f45c2490d0a7e312377e80b505fe2"
    plan = ident(OWN / "frozen-independent-controls.json")
    assert plan["sha256"] == before["controls_sha256"]
    utility = ROOT / "verification/android-editor-generic-descriptor-correction/check_descriptor_joins.py"
    assert ident(utility)["sha256"] == "40e7a4c40b5b11a7147666fb1257f184d8a786ab5dd31804b7dada7d3d62e34e"
    tree = ast.parse(utility.read_bytes())
    callsites = []
    def visit(node, scope="module"):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scope = node.name
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("descriptor", "descriptor_context"):
            callsites.append({"line": node.lineno, "scope": scope, "callee": node.func.id,
                              "keywords": [k.arg for k in node.keywords]})
        for child in ast.iter_child_nodes(node):
            visit(child, scope)
    visit(tree)
    write("source-context-callsite-review.json", {"utility": {"path": str(utility.relative_to(ROOT)), **ident(utility)},
          "callsites": sorted(callsites, key=lambda c: c["line"]),
          "semantic_review": {
              "declarations": "Joiner construction uses retained access on every parsed declaration before storing methods",
              "public": "public_contract checks public concrete instance flags and contextual descriptor; row's receiver1 parsing follows that exact binding",
              "compiled_call": "Exact retained caller/BCI lookup precedes caller access context; supported opcode set and resolved retained declaration precede access/opcode context",
              "completion": "compiled_call governs all paths; symbolic/resolved/caller contexts are retained before joined status; resolved dynamic instance method rejects static/abstract; special pair uses retained inner declaration already checked at construction",
              "grammar_only": "value validates synthetic class/type text; completion/row extracts return types after earlier contextual checks; these calls provide no method qualification",
              "unsupported": "Only helper-only absent/unknown context returns unresolved; qualifying join paths supply parsed access and explicitly supported opcode; executable negative controls confirm unsupported/contradictory metadata cannot label joined"},
          "syntax_analysis_is_not_release_authority": True})
    write("jvms17-independent-source-check.json", {"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "source": "https://docs.oracle.com/javase/specs/jvms/se17/html/jvms-4.html", "sections": ["4.2.1", "4.2.2", "4.3.2", "4.3.3"],
          "names": "Internal class segments use the unqualified-name rules: nonempty, no period/semicolon/left-bracket/slash within a segment. Parentheses and ASCII whitespace remain legal.",
          "budget": "Method parameter width is at most255 including receiver where applicable. Long/double use2, arrays and other parameters1. Context is required to enforce receiver width.",
          "scope": "Official specification corroboration only; no runtime or release authority"})
    controls = json.loads((OWN / "focused-independent-results.json").read_bytes())
    original119 = json.loads((OWN / "original119-fresh-results.json").read_bytes())
    compact = json.loads((OWN / "compact214-fresh-results.json").read_bytes())
    original24 = json.loads((OWN / "unchanged24.json").read_bytes())
    migrated24 = json.loads((OWN / "migrated24.json").read_bytes())
    assert controls["count"] == controls["passed"] == 72
    assert original119["count"] == original119["passed"] == 119
    assert original24["run"] == 24 and original24["failures"] == 1 and original24["errors"] == 0
    assert migrated24["run"] == 24 and migrated24["failures"] == migrated24["errors"] == 0
    assert len(compact["known_findings"]) == 2 and not compact["delivered_row_differences"]
    assert ident(OWN / "run_review-attempt1.py")["sha256"] == json.loads((OWN / "controls-command-receipt-failure.json").read_bytes())["source_sha256"]
    summary = {"schema": 1, "status": "selected-F1-F2-F3-addressed; no-new-actionable-utility-findings; same-two-inner-return-findings-retained",
               "candidate_seal_sha256": before["packets"][0]["sha256"], "corrected_utility_sha256": ident(utility)["sha256"],
               "frozen_controls_sha256": plan["sha256"], "original119": {"count": 119, "passed": 119, "definitions_unchanged": True},
               "independent_controls": {"descriptor_context": 72, "coherent_hook_receiver": 2, "normal_unknown_receiver": 1, "passed": True},
               "retained_context": {"declarations": controls["retained_declarations_context_passed"], "public_bindings": controls["public_bindings_context_passed"]},
               "producer_tests": {"unchanged24": "one-exact-selected-stale-assertion-failure", "migrated24": "24-passed"},
               "compact": {"full_passes": 1, "counts": compact["counts"], "known_findings": 2, "delivered_row_differences": 0},
               "whole_records": compact["whole_record_preservation"],
               "review_harness_failures": ["preparation optional seal summary-key mismatch retained and corrected", "control evaluator extraction trailing-newline mismatch retained and corrected; completed24 suites not rerun"],
               "utility_findings": [], "remaining_known_findings": ["boundary162 row3 innerView cannot prove outerSwitch/TextView return", "boundary162 row5 innerView cannot prove outerSwitch/TextView return"],
               "native_runtime_UI_capture_or_process_inventory_performed": False, "no_preexisting_candidate_bytecode_cache_import_or_mutation": True,
               "scratch_cleanup": "In-memory only; no new native instances, cache artifacts or spawned child processes during controls/compact; existing project processes preserved",
               "accepted_scope": "Host Python source/data correction only", "native_physical_signing_store_customer_operational_OTA_GA": "pending-or-outside-scope", "qualification": False}
    write("review-summary.json", summary)
    write("postexecution-custody.json", {"schema": 1, "packets": after,
          "root_review_release": {"path": str(release.relative_to(ROOT)), **ident(release)}, "frozen_controls": plan,
          "source_revision": before["git_head"], "scope": "Manifest/data verification only; no utility reexecution or compact replay"})
    write("finalization-command-receipt.json", {"command": "python3 -I -B verification/android-generic-descriptor-correction-independent/finalize_review.py",
          "python": sys.version, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source_sha256": ident(Path(__file__))["sha256"],
          "source_revision": before["git_head"], "status": "passed", "output": "All pinned input members preserved; own review frozen", "scope": "Source/data custody only", "cleanup": "No scratch or runtimes created"})
    members = []
    for path in sorted(OWN.rglob("*")):
        assert not path.is_symlink()
        if path.is_file():
            assert "__pycache__" not in path.parts and path.suffix != ".pyc"
            members.append({"path": str(path.relative_to(OWN)), **ident(path)})
    tree_digest = sha(json.dumps(members, sort_keys=True, separators=(",", ":")).encode())
    write("review-seal.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "status": summary["status"], "member_count": len(members), "member_bytes": sum(m["bytes"] for m in members),
          "tree_digest_sha256": tree_digest, "members": members, "qualification": False,
          "candidate_correction_seal_sha256": summary["candidate_seal_sha256"]})
    print(json.dumps({"seal": str((OWN / "review-seal.json").relative_to(ROOT)), **ident(OWN / "review-seal.json"),
          "members": len(members), "member_bytes": sum(m["bytes"] for m in members), "status": summary["status"]}))

if __name__ == "__main__":
    main()

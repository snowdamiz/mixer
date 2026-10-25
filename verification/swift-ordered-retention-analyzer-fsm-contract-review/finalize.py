"""Finalize only this independently owned review packet, then seal it."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from run_review import ROOT, OWN, UPSTREAM, sha, verify


def main():
    assert sys.dont_write_bytecode
    assert not (OWN / "seal.json").exists()
    run2 = json.loads((OWN / "commands/run-2/result.json").read_bytes())
    correction = json.loads((OWN / "commands/amendment-controls/result.json").read_bytes())
    assert run2["expected_exits_match"] and correction["passed"]
    methods = {}
    for name in ("independent-oracle", "frozen-producer", "independent-cross-checks"):
        raw = (OWN / "commands/run-2" / (name + ".stderr")).read_text()
        methods[name] = int(re.search(r"Ran (\d+) tests", raw)[1])
        assert raw.rstrip().endswith("OK")
    raw = (OWN / "commands/amendment-controls/controls.stderr").read_text()
    methods["independent-amendment"] = int(re.search(r"Ran (\d+) tests", raw)[1])
    assert raw.rstrip().endswith("OK")
    assert methods == {"independent-oracle": 18, "frozen-producer": 24,
                       "independent-cross-checks": 12, "independent-amendment": 8}
    upstream = [verify(ROOT, *entry) for entry in UPSTREAM]
    producer = verify(ROOT, "swift-ordered-retention-analyzer-fsm-contract",
                      "bde96e5f4f1b0ad5bc6366fee79a47f7a375247959191b206d8e7799ed4da193", 245)
    for name, expected in (("preparation-seal.json", "316040e19aa5d029ef1d885d59ba23f6557debce719f9f79125a227718250649"),
                           ("findings-freeze1-seal.json", "31460ea35508acfc5b0093f5f32874b1baa69f4377285ce4060c503f98d765e6")):
        assert sha(OWN / name) == expected
        for row in json.loads((OWN / name).read_bytes())["members"]:
            p = ROOT / row["path"]
            assert p.stat().st_size == row["bytes"] and sha(p) == row["sha256"]
    library_seal = ROOT / "verification/swift-ordered-retention-analyzer-library/seal.json"
    assert sha(library_seal) == "777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63"
    library = {r["path"]: r for r in json.loads(library_seal.read_bytes())["members"]}
    selected = ("docs/swift-ordered-retention-analyzer-library.md",
                "verification/swift-ordered-retention-analyzer-library/src/analyzer.rs",
                "verification/swift-ordered-retention-analyzer-library/logical-inventory.md")
    library_matches = []
    for path in selected:
        snapshot = OWN / "inputs" / path.replace("/", "__")
        assert snapshot.stat().st_size == library[path]["bytes"] and sha(snapshot) == library[path]["sha256"]
        assert sha(ROOT / path) == library[path]["sha256"]
        library_matches.append(library[path])
    assert not list(OWN.rglob("__pycache__"))
    final_commands = OWN / "commands/finalization-2"
    final_commands.mkdir(parents=True, exist_ok=False)
    checks = []
    sources = [p for p in OWN.glob("*.py")]
    for source in sources:
        compile(source.read_bytes(), str(source), "exec")
    text_paths = [ROOT / "docs/swift-ordered-retention-analyzer-fsm-contract-review.md",
                  OWN / "README.md", *sources]
    for i, path in enumerate(text_paths):
        argv = ["git", "diff", "--no-index", "--check", "--", "/dev/null", str(path)]
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
        (final_commands / f"{i}.stdout").write_bytes(p.stdout)
        (final_commands / f"{i}.stderr").write_bytes(p.stderr)
        assert p.returncode in (0, 1) and not p.stdout and not p.stderr, (path, p.stdout, p.stderr)
        checks.append({"argv": argv, "exit": p.returncode, "new_file_difference_exit_allowed": True,
                       "stdout_sha256": sha(final_commands / f"{i}.stdout"),
                       "stderr_sha256": sha(final_commands / f"{i}.stderr")})
    source_rows = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)}
                   for p in sorted(text_paths)]
    source_digest = hashlib.sha256(json.dumps(source_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.UTC).isoformat(),
               "verdict": "accept-corrected-bounded-fixture-envelope-contract-only",
               "source_revision_context": (OWN / "commands/run-2/revision.stdout").read_text().strip(),
               "producer": producer, "upstream": upstream,
               "selected_accepted_framing_source_matches": library_matches,
               "preparation_seal_sha256": "316040e19aa5d029ef1d885d59ba23f6557debce719f9f79125a227718250649",
               "findings_seal_sha256": "31460ea35508acfc5b0093f5f32874b1baa69f4377285ce4060c503f98d765e6",
               "findings": {"R1": "source u32 width restored; selected profile join unavailable",
                            "R2": "explicit retained candidate ownership/init/borrow/move/drop/debit contract",
                            "R3": "poison propagated before CAP/nonCAP finish and subsequent records"},
               "methods": methods, "total_methods": sum(methods.values()),
               "independent_methods": 38, "differential_comparisons": 5390,
               "baseline_state_kind_vectors": 154,
               "run_receipts": ["commands/run-2/result.json", "commands/amendment-controls/result.json"],
               "archive_member_checks": [139, 210],
               "inventory": {"init_proposed_roles": 4728, "call_proposed_roles": 4536,
                             "reserved_roles": 5120, "candidate_bytes": 2048,
                             "candidate_payload_bytes": 96, "setup_debit": 534,
                             "record_debit": 128, "arena_cap": 8388608,
                             "transient_cap": 65536, "step_cap": 268435456,
                             "Rust_report_bytes": 49152, "aggregate_report_cap": 65536,
                             "actual_Rust_lifetimes_qualified": False,
                             "combined_8192_preflight_qualified": False},
               "agent_configuration": {"requested_model": "gpt-6.1-sol",
                                       "requested_reasoning_effort": "xhigh",
                                       "fresh_context": True, "controlling_model_changed": False},
               "python": run2["python"], "rustc": run2["rustc"],
               "source_rows": source_rows, "source_tree_sha256": source_digest,
               "syntax_compile_count": len(sources), "diff_checks": checks,
               "remaining_contract_blockers_to_preparing_Rust_integration": [],
               "implementation_selection": False,
               "implementation_acceptance_gates": ["review separate named orchestrator/typed observation proposal, absent/unavailable handling and complete Result/caller moves before dependent changes; preserve existing framing ABI/report/behavior",
                   "private internal framed/profile coupling and late refusal propagation",
                   "sole arena/candidate/coordinate owners with complete source/Result/move/lifetime inventory",
                   "safe atomic checked writes, poison/error/output behavior",
                   "actual combined source debit mapping and retained8192 reservation proof under unchanged caps"],
               "storedPrefixValidated": False, "fullReplayAccepted": False,
               "semantic_counters_valid": False, "actual_GA_or_reviewer_promotions": 0,
               "pending": ["resident/token/plan/victim policy and semantic metrics",
                   "failure code/kind/resource/stage/cursor applicability",
                   "real profile/selection/original-result/ledger/crypto/custody",
                   "CLI/source preparer/driver/full target",
                   "native/device/compiler/signing/store/customer/operations/published FieldLog/GA"],
               "cleanup": {"disposable_scratch_created": False, "synchronous_children_reaped": True,
                           "bytecode_created": False, "layout_binaries_retained": True,
                           "native_capture_target_or_unrelated_processes_started_or_queried": False}}
    (OWN / "final-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    rows = []
    for p in sorted([ROOT / "docs/swift-ordered-retention-analyzer-fsm-contract-review.md", *OWN.rglob("*")]):
        if p.is_file():
            rows.append({"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)})
    excluded = [str((OWN / name).relative_to(ROOT)) for name in ("seal.json", "seal.sha256")]
    seal = {"schema": 1, "at": datetime.datetime.now(datetime.UTC).isoformat(),
            "excluded": excluded, "members": rows}
    (OWN / "seal.json").write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
    seal_digest = sha(OWN / "seal.json")
    (OWN / "seal.sha256").write_text(seal_digest + "\n")
    print(json.dumps({"verdict": receipt["verdict"], "seal_sha256": seal_digest,
                      "members": len(rows), "bytes": sum(row["bytes"] for row in rows),
                      "total_methods": 62, "source_tree_sha256": source_digest}, sort_keys=True))


if __name__ == "__main__":
    main()

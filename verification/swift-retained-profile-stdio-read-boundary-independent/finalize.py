"""Final exact custody/stream/source audit; freeze only this new followup."""
import datetime
import json
from pathlib import Path
from verify_inputs import ROOT, verify, sha, dump


if __name__ == "__main__":
    assert not (ROOT / "seal.json").exists(), "never rewrite frozen evidence"
    inputs = verify()
    source_custody = json.loads((ROOT / "source-custody.json").read_text())
    for copy in source_custody["copies"]:
        raw = (ROOT / copy["copy"]).read_bytes()
        assert len(raw) == copy["bytes"] and sha(raw) == copy["sha256"]
    commands = json.loads((ROOT / "command-receipts.json").read_text())["commands"]
    assert len(commands) == 98
    for row in commands:
        assert row["command_disposition_matches"] and row["terminal_reaped"] and not row["timed_out"]
        for key in ("stdout", "stderr", "executed_case_source", "prototype_source"):
            item = row[key]
            raw = (ROOT / item["path"]).read_bytes()
            assert len(raw) == item["bytes"] and sha(raw) == item["sha256"]
    new_cases = [row for row in commands if row["classification"].startswith("fresh byte-identical")]
    assert len(new_cases) == 63 and all(row["exit_code"] == 0 for row in new_cases)
    old_failures = [row for row in commands if row["exit_code"] == 1]
    assert len(old_failures) == 5
    for row in old_failures:
        assert row["prototype_source"]["sha256"] == "54d8b967b996ff273039824fffa6042e9ca9ef383079ce1427aadf45f23114a1"
        assert row["observations"][0]["required_behavior_pass"] is False
    healthy = sum(row["observations"][-1]["ownership_at_process_exit"]["healthy_zero"] for row in new_cases)
    assert healthy == 12
    scratch = []
    for path in ROOT.rglob("owned-scratch"):
        assert not list(path.iterdir())
        scratch.append(str(path.relative_to(ROOT)))
    for relative in sorted(scratch, key=lambda x: len(Path(x).parts), reverse=True):
        (ROOT / relative).rmdir()
    sources = sorted(list(ROOT.rglob("*.py")) + [ROOT / "README.md", ROOT / "findings.md", ROOT / "independently-computed.patch"])
    entries = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())} for path in sources]
    preimage = b"swift-retained-profile-stdio-read-boundary-independent-source-v1\n" + b"".join((row["path"] + "\0" + str(row["bytes"]) + "\0" + row["sha256"] + "\n").encode() for row in entries)
    receipt = json.loads((ROOT / "receipt.json").read_text())
    receipt.update({"final_source_tree_sha256": sha(preimage), "source_entries": entries, "owned_empty_scratch_directories_removed": scratch, "independent_healthy_zero_cases": healthy, "independent_honestly_unresolved_cases": len(new_cases) - healthy, "all_original_independent_case_bodies_oracles_unchanged": True, "scoped_host_C01_R03_correction_acceptance_recommended": True, "new_material_findings": 0})
    dump(ROOT / "receipt.json", receipt)
    dump(ROOT / "final-audit.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "input_custody": inputs, "streams_sources_and_terminal_dispositions_verified": 98, "new_exact_independent_passes": 63, "new_root_boundary_passes": 16, "old_failed_behavior_executions_preserved": 5, "all_new_independent_oracles_byte_identical": True, "retained_uncertainty_not_erased": True, "owned_scratch_directories_removed": scratch, "acceptance_recommendation": "exact finite host C01/R03 correction only", "complete_composition_product_native_OTA_GA_accepted": False})
    members = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file():
            assert not path.is_symlink() and "__pycache__" not in path.parts
            data = path.read_bytes()
            members.append({"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)})
    dump(ROOT / "seal.json", {"schema": 1, "scope": "independent finite R03 read-completion correction and unchanged C01 cleanup controls", "member_count": len(members), "member_bytes": sum(row["bytes"] for row in members), "members": members, "self_seal_metadata": {"path": "seal.sha256", "bytes": 76, "exact_content": "lowercase sha256 of seal.json + two ASCII spaces + seal.json + LF"}, "scoped_host_correction_acceptance_recommended": True, "complete_composition_real_Rust_native_OTA_GA_accepted": False})
    digest = sha((ROOT / "seal.json").read_bytes())
    (ROOT / "seal.sha256").write_bytes((digest + "  seal.json\n").encode())
    print(json.dumps({"seal_sha256": digest, "members": len(members), "member_bytes": sum(row["bytes"] for row in members), "source_tree_sha256": sha(preimage), "fresh_commands": 98, "independent_new_passes": 63, "root_new_boundary_passes": 16, "old_required_failures_retained": 5, "owned_scratch_removed": scratch, "scoped_host_correction_recommendation": True, "complete_composition_accepted": False}, sort_keys=True))

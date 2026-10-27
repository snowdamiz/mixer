"""Freeze only this independent review after final immutable-input/stream audit."""
import datetime
import hashlib
import json
from pathlib import Path
from verify_inputs import ROOT, verify, sha


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    assert not (ROOT / "seal.json").exists(), "never rewrite an existing frozen review"
    custody = verify()
    for member in json.loads((ROOT / "source-custody.json").read_text())["exact_copies"]:
        file = ROOT / member["copy"]
        assert len(file.read_bytes()) == member["bytes"] and sha(file.read_bytes()) == member["sha256"]
    for prefix, count in ((ROOT, 77), (ROOT / "preliminary", 75)):
        commands = json.loads((prefix / "command-receipts.json").read_text())["commands"]
        assert len(commands) == count
        for row in commands:
            assert row["command_disposition_matches"] and row["terminal_reaped"] and not row["timed_out"]
            for stream in ("stdout", "stderr"):
                file = prefix / row[stream]
                data = file.read_bytes()
                assert len(data) == row[stream + "_bytes"] and sha(data) == row[stream + "_sha256"]
    final_commands = json.loads((ROOT / "command-receipts.json").read_text())["commands"]
    required = [x for x in final_commands if x["classification"] == "required R03 read-boundary failure retained"]
    assert len(required) == 2
    for row in required:
        assert row["exit_code"] == 1
        assert row["observations"][0]["required_behavior_pass"] is False
        assert row["observations"][-1]["ownership_after_stack_and_fixture_cleanup"]["healthy_zero"]
        assert row["observations"][-1]["scratch_entries_remaining"] == 0
    results = json.loads((ROOT / "results.json").read_text())
    assert results["new_independent_cases"] == 63
    assert results["new_independent_behavior_passes"] == 61 and results["new_independent_required_failures"] == 2
    scratch = []
    for path in ROOT.rglob("owned-scratch"):
        assert not list(path.iterdir())
        scratch.append(str(path.relative_to(ROOT)))
    for relative in sorted(scratch, key=lambda x: len(Path(x).parts), reverse=True):
        (ROOT / relative).rmdir()
    sources = sorted(list(ROOT.rglob("*.py")) + [ROOT / "README.md", ROOT / "findings.md"])
    source_entries = [{"path": str(x.relative_to(ROOT)), "bytes": len(x.read_bytes()), "sha256": sha(x.read_bytes())} for x in sources]
    preimage = b"swift-retained-profile-stdio-independent-source-v1\n" + b"".join((x["path"] + "\0" + str(x["bytes"]) + "\0" + x["sha256"] + "\n").encode() for x in source_entries)
    receipt = json.loads((ROOT / "receipt.json").read_text())
    receipt["final_source_tree_sha256"] = sha(preimage)
    receipt["final_source_entries"] = source_entries
    receipt["owned_empty_scratch_directories_removed"] = scratch
    receipt["preliminary_recorded_commands_excluded_from_final77"] = 75
    receipt["preliminary_wrong_child_expectation_explicitly_corrected"] = True
    receipt["C01_host_ownership_requirements_pass"] = True
    receipt["R03_required_failure_retained"] = True
    receipt["new_corrected_root_R03_packet_reviewed_or_included"] = False
    dump(ROOT / "receipt.json", receipt)
    dump(ROOT / "final-audit.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "immutable_inputs_verified": custody, "final_recorded_commands_audited": 77, "preliminary_recorded_commands_audited": 75, "all_stream_byte_lengths_and_sha256_verified": True, "C01_scoped_positive": True, "R03_required_failures": 2, "complete_composition_accepted": False, "owned_empty_scratch_directories_removed": scratch, "uncertain_saved_numbers_retried_or_ledger_erased": False, "new_root_R03_correction_blended": False})
    members = []
    for file in sorted(ROOT.rglob("*")):
        if file.is_file():
            assert not file.is_symlink() and "__pycache__" not in file.parts
            data = file.read_bytes()
            members.append({"path": str(file.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)})
    dump(ROOT / "seal.json", {"schema": 1, "scope": "independent finite raw-stdio C01 positive review with two required R03 read-completion failures retained", "member_count": len(members), "members": members, "self_seal_metadata": {"path": "seal.sha256", "bytes": 76, "exact_content": "lowercase sha256 of seal.json + two ASCII spaces + seal.json + LF"}, "product_real_Rust_native_OTA_GA_accepted": False, "complete_composition_accepted": False})
    digest = sha((ROOT / "seal.json").read_bytes())
    (ROOT / "seal.sha256").write_bytes((digest + "  seal.json\n").encode())
    print(json.dumps({"seal_sha256": digest, "members": len(members), "member_bytes": sum(x["bytes"] for x in members), "source_tree_sha256": sha(preimage), "final_recorded_commands": 77, "preliminary_recorded_commands": 75, "new_independent_behavior_passes": 61, "required_R03_failures": 2, "owned_scratch_removed": scratch, "complete_composition_accepted": False}, sort_keys=True))

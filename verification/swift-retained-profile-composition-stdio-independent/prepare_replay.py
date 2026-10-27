"""Copy verified exact inputs into this lane; never invoke a producer builder."""
import json
from pathlib import Path
from verify_inputs import ROOT, REPO, verify, sha


if __name__ == "__main__":
    verify()
    base = REPO / "verification/swift-retained-profile-composition-stdio-correction"
    copies = []
    for variant in ("old", "new"):
        for name in ("prototype.py", "schema.py", "consumer.py", "test_preparation.py"):
            source = base / variant / "replay/corrected/replay" / name
            target = ROOT / variant / "replay/corrected/replay" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            assert not target.exists()
            target.write_bytes(source.read_bytes())
            copies.append({"source": str(source.relative_to(REPO)), "copy": str(target.relative_to(ROOT)), "sha256": sha(target.read_bytes()), "bytes": target.stat().st_size})
        source = base / variant / "independent_case.py"
        target = ROOT / variant / "independent_case.py"
        assert not target.exists()
        target.write_bytes(source.read_bytes())
        copies.append({"source": str(source.relative_to(REPO)), "copy": str(target.relative_to(ROOT)), "sha256": sha(target.read_bytes()), "bytes": target.stat().st_size})
    (ROOT / "source-custody.json").write_text(json.dumps({"schema": 1, "exact_copies": copies}, indent=2, sort_keys=True) + "\n")
    commands = json.loads((base / "command-receipts.json").read_text())["commands"]
    for command in commands:
        assert command["terminal_reaped"] and command["exit_code"] == command["expected_exit"]
        for stream in ("stdout", "stderr"):
            assert sha((base / command[stream]).read_bytes()) == command[stream + "_sha256"]
    results = json.loads((base / "results.json").read_text())
    assert len(commands) == 213
    assert len(results["regression"]) == 142 and len(results["stdio"]) == 57
    assert sum(x["cleanup_kind"] == "healthy-zero" for x in results["stdio"]) == 5
    for variant in results["producer"]:
        row = variant["result"]
        assert row["methods"] == 26 and row["failures"] == row["errors"] == row["skips"] == 0
        assert any(x.get("snapshot_leaf_mutations") == 307 for x in row["observations"])
    (ROOT / "retained-evidence-audit.json").write_text(json.dumps({"schema": 1, "commands_with_terminal_dispositions_and_stream_hashes_audited": len(commands), "producer_methods_each": 26, "snapshot_leaf_mutations_each": 307, "unchanged_lifecycle_cases_audited": 142, "stdio_cases_audited": 57, "stdio_healthy_zero_audited": 5, "stdio_unresolved_audited": 52, "classification": "offline retained evidence audit, not fresh independent execution"}, indent=2, sort_keys=True) + "\n")
    print("Copied ten verified exact source members; audited 213 retained commands,142 lifecycle and57 stdio case records.")

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKET = ROOT.parent / "swift-retained-profile-composition-correction"
receipt = json.loads((PACKET / "receipt.json").read_bytes())
entries = receipt["source_entries"]
assert [e["path"] for e in entries] == sorted(e["path"] for e in entries)
preimage = b"retained-profile-correction-source-v1\n"
for e in entries:
    raw = (PACKET / e["path"]).read_bytes()
    assert len(raw) == e["bytes"] and hashlib.sha256(raw).hexdigest() == e["sha256"]
    preimage += (e["path"] + "\0" + str(e["bytes"]) + "\0" + e["sha256"] + "\n").encode()
assert hashlib.sha256(preimage).hexdigest() == receipt["source_tree_sha256"] == "3b78a8a719ab18856919ca5c201a403ccfb6223cbd012e6c1a39c5c11d3cacd6"
replay = ROOT / "replay"
copied = []
for variant in ("old", "corrected"):
    for name in ("prototype.py", "consumer.py", "schema.py", "test_preparation.py", "../test_independent.py"):
        relative = (Path(variant) / "replay" / name)
        source = (PACKET / relative).resolve()
        relative = source.relative_to(PACKET)
        target = replay / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        target.write_bytes(raw)
        copied.append({"path": relative.as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
(replay / "run_unchanged_witness.py").write_bytes((PACKET / "run_unchanged_witness.py").read_bytes())
(replay / "raw-witnesses").mkdir(exist_ok=True)
for variant in ("old", "corrected"):
    assert (replay / variant / "test_independent.py").read_bytes() == (replay / "old/test_independent.py").read_bytes()
for name in ("consumer.py", "schema.py", "test_preparation.py"):
    assert (replay / "old/replay" / name).read_bytes() == (replay / "corrected/replay" / name).read_bytes()
(ROOT / "source-custody.json").write_text(json.dumps({"source_tree_sha256": receipt["source_tree_sha256"], "all_source_members_verified": True, "copies": copied, "raw_runner_sha256": hashlib.sha256((replay / "run_unchanged_witness.py").read_bytes()).hexdigest(), "only_variant_prototype_changed": True}, indent=2, sort_keys=True) + "\n")
results = json.loads((PACKET / "results.json").read_bytes())
commands = json.loads((PACKET / "command-receipts.json").read_bytes())["commands"]
assert len(commands) == 150 and results["targeted_case_count"] == 142
for record in commands:
    for stream in ("stdout", "stderr"):
        assert hashlib.sha256((PACKET / record[stream]).read_bytes()).hexdigest() == record[stream + "_sha256"]
    assert record["exit_code"] == record["expected_exit"] and record["terminal_reaped"]
faults = results["fault_cases"]
assert len(faults) == 142
assert sum(x["cleanup_kind"] == "healthy-zero" for x in faults) == 5
assert sum(x["cleanup_kind"].startswith("synthetic-known-fault") for x in faults) == 136
assert sum(x["case"] == "nonterminal-child-model" for x in faults) == 1
for x in faults:
    assert not any(x["authority"].values()) and not x["uncertain_os_close_resolution_qualified"]
    assert x["ownership_at_child_terminal_exit"]["healthy_zero"] == (x["cleanup_kind"] == "healthy-zero")
(ROOT / "retained-evidence-audit.json").write_text(json.dumps({"retained_commands": 150, "all_stream_hashes_verified": True, "targeted_results": 142, "healthy_results": 5, "uncertain_results": 136, "modeled_nonterminal_results": 1, "actual_OS_close_resolution": False}, indent=2, sort_keys=True) + "\n")
print("verified correction source tree, exact copied controls,150 retained command streams and142 result dispositions")

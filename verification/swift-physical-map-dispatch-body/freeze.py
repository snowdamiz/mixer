#!/usr/bin/env python3
"""Freeze derived offline mapping evidence; no compiler or runtime invocation."""
from pathlib import Path
import datetime, hashlib, json, signal, sys, time

START = time.monotonic()
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("55 second command bound")))
signal.alarm(50)
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
def sha(raw): return hashlib.sha256(raw).hexdigest()
def current(path):
    raw = (ROOT / path).read_bytes()
    return {"path": path, "bytes": len(raw), "sha256": sha(raw)}
index = json.loads((OUT / "index-candidates.json").read_bytes())
mapping = json.loads((OUT / "mapping.json").read_bytes())
assert mapping["status"] == "INCOMPLETE"
assert len(mapping["targets"]) == 2
assert all(target["unique_LLVM_definition"] is None and target["native_assembly_function"] is None for target in mapping["targets"])
rechecked = []
for item in index["inputs"] + [artifact["input"] for artifact in index["artifacts"]]:
    observed = current(item["path"])
    assert observed == item, (observed, item)
    rechecked.append(observed)
members = []
for path in sorted(OUT.rglob("*")):
    if not path.is_file() or path.name == "seal.json": continue
    assert not path.is_symlink()
    raw = path.read_bytes()
    members.append({"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": sha(raw)})
derived_bytes = sum(member["bytes"] for member in members)
assert derived_bytes < 8 * 1024 * 1024
seal = {"schema": 1, "status": "FROZEN_INCOMPLETE_DISPATCH_BODY_MAPPING", "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "command": ["python3", "verification/swift-physical-map-dispatch-body/freeze.py"], "tool_version": sys.version, "source_revision": index["source_revision"], "source146_tree_sha256_from_accepted_frontier": index["source146_tree_sha256_from_accepted_frontier"], "inputs_rechecked_unchanged_at_freeze": rechecked, "derived_members": members, "derived_bytes_excluding_seal": derived_bytes, "raw_unique_artifact_bytes": index["raw_artifact_unique_bytes"], "elapsed_seconds": time.monotonic()-START, "whole_function_mapping_complete": False, "unresolved_targets": ["Dispatch", "Body"], "actual_verifier_input_run_released": False, "physical_peak_accepted": False, "frontier_complete": False, "product_GA_accepted": False, "raw_artifacts_preserved": True, "changed_scope": "new verification/swift-physical-map-dispatch-body/ only", "native_or_compiler_processes_started": 0, "holds_preserved": ["local-custody", "UnitA", "UI-and-screen-capture", "native-runtime", "physical-devices"]}
(OUT / "seal.json").write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": seal["status"], "elapsed_seconds": time.monotonic()-START, "derived_files_excluding_seal": len(members), "derived_bytes_excluding_seal": derived_bytes, "seal_sha256": sha((OUT / "seal.json").read_bytes())}, indent=2))

#!/usr/bin/env python3
"""Freeze the new implementation packet only, after all owned children return."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DOC=HERE.parent/"implementation.md"
assert not (HERE/"seal.json").exists(),"Frozen implementation is immutable"
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def desc(p):
    return {"path":str(p.relative_to(ROOT)),"bytes":p.stat().st_size,"sha256":sha(p)}
def load(p):
    return json.loads(p.read_text())
def save(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
final=load(HERE/"final-receipt.json")
assert final["status"]=="host-producer-controls-passed-independent-behavior-acceptance-pending"
assert final["candidate_source_sha256"]=="2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef"
for namespace in ["run-1","run-2"]:
    r=load(HERE/namespace/"receipt.json")
    assert r["all_children_reaped"] and r["owned_scratch_removed"] and r["source_and_frozen_inputs_preserved"]
    for c in r["commands"]:
        assert c["child_reaped"] and not c["timed_out"]
        assert sha(HERE/namespace/c["stdout"])==c["stdout_sha256"]
        assert sha(HERE/namespace/c["stderr"])==c["stderr_sha256"]
    for item in r["direct_immutable_inputs_after"]+r["compiled_owned_inputs_after"]:
        assert desc(ROOT/item["path"])==item,item["path"]
for p in HERE.rglob("*"):
    assert not p.is_symlink(),str(p)
finalizer=load(HERE/"finalization-command/receipt.json")
assert finalizer["returncode"]==0 and finalizer["child_reaped"] and not finalizer["timed_out"]
assert finalizer["finalizer_sha256_before"]==finalizer["finalizer_sha256_after"]==sha(HERE/"finalization-command/executed-finalizer.py")
assert sha(HERE/"finalization-command/stdout.bin")==finalizer["stdout_sha256"]
assert sha(HERE/"finalization-command/stderr.bin")==finalizer["stderr_sha256"]
proposal=HERE.parent/"proposal-1/seal.json"
assert sha(proposal)=="3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c"
for m in load(proposal)["members"]:assert desc(ROOT/m["path"])==m
save("freeze-command.json",{"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "argv":[sys.executable,"-B",str(Path(__file__).resolve())],"cwd":str(ROOT),"python":sys.version,
    "source_sha256":sha(Path(__file__)),"scope":"standard-library offline custody/hash freeze only; no candidate or native execution",
    "qualification_owned_children_reaped":27,"offline_finalizer_owned_child_reaped":1,
    "all_owned_child_commands_reaped":28,"child_timeouts":0,
    "result":"stream/input/proposal/finalization hashes and cleanup verified before freeze"})
members=[desc(p) for p in sorted(HERE.rglob("*")) if p.is_file() and p.name not in {"seal.json","seal.sha256"}]
members.append(desc(DOC));members.sort(key=lambda m:m["path"])
seal={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope":"Only new implementation/** and implementation.md; proposal/historical evidence referenced and immutable. Isolated host producer evidence, independent behavior/final acceptance pending.",
    "status":"frozen-host-producer-evidence-independent-behavior-pending",
    "candidate_source_sha256":final["candidate_source_sha256"],
    "parent_source_sha256":final["parent_source_sha256"],
    "final_receipt":desc(HERE/"final-receipt.json"),
    "source_test_model_binding":desc(HERE/"source-test-model-binding.json"),
    "cleanup":desc(HERE/"cleanup.json"),
    "members":members,"member_count":len(members),"total_bytes":sum(m["bytes"] for m in members),
    "qualification_methods_passed_across_receipts":78,"fresh_candidate_oracle_comparisons":21714,
    "first_test_failure_and_exact_test_only_repair_preserved":True,
    "all_owned_child_commands_reaped":28,"owned_scratch_binaries_and_temporary_links_cleaned":True,
    "implementation_accepted":False,"independent_behavior_accepted":False,
    "fullReplayAccepted":False,"storedPrefixValidated":False,"semanticMetricsValid":False,"GA_qualified":False,
    "excluded":["implementation/seal.json","implementation/seal.sha256"]}
save("seal.json",seal)
digest=sha(HERE/"seal.json");(HERE/"seal.sha256").write_text(digest+"  seal.json\n")
print(json.dumps({"seal":str((HERE/"seal.json").relative_to(ROOT)),"seal_sha256":digest,
    "member_count":seal["member_count"],"total_bytes":seal["total_bytes"],
    "candidate_source_sha256":seal["candidate_source_sha256"],
    "final_receipt":seal["final_receipt"],"source_test_model_binding":seal["source_test_model_binding"],
    "cleanup":seal["cleanup"],"attempt_receipts":[desc(HERE/"run-1/receipt.json"),desc(HERE/"run-2/receipt.json")],
    "compiled_input_trees":[load(HERE/n/"receipt.json")["compiled_input_tree_sha256"] for n in ["run-1","run-2"]]},sort_keys=True))

#!/usr/bin/env python3
"""Freeze only this new proposal and its one assigned document."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
assert not (OUT/"seal.json").exists(), "A frozen proposal is immutable; use a new proposal directory"
def sha(b):
    return hashlib.sha256(b).hexdigest()
def identity(p):
    data=p.read_bytes()
    return {"path":str(p.relative_to(ROOT)),"bytes":len(data),"sha256":sha(data)}
def save(name, data):
    (OUT/name).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
def obj(name):
    return json.loads((OUT/name).read_text())
for command in ["python-version","git-version","revision","prepare","check"]:
    r=obj("commands/"+command+"/receipt.json")
    assert r["returncode"]==0 and not r["timed_out"] and r["child_reaped"],command
check=obj("static-check-result.json")
assert check["status"]=="offline-proposal-custody-and-arithmetic-passed"
admission=obj("admission.json")
for member in admission["inputs"]:
    assert identity(ROOT/member["path"])==member,member["path"]
sources=[identity(OUT/"src/analyzer.rs"),identity(OUT/"src/envelope.rs")]
source_tree_sha256=sha(json.dumps(sources,sort_keys=True,separators=(",",":")).encode())
keys=["source-binding.json","ledger-delta.json","copy-edge-delta.json","guard-funding-proposal.json",
      "validator-truth-table.json","type-lifetime-delta.json","test-plan.json","envelope.diff"]
manifest={"schema":1,"status":"proposal-frozen-selection-required",
    "source_inputs":sources,"source_tree_sha256":source_tree_sha256,
    "contracts_and_proofs":[identity(OUT/n) for n in keys],
    "source_span_convention":"1-based start inclusive/end exclusive",
    "selected_totals_proposed_only":{"leaf":425,"W":24,"B":471,"G":112,"T":42,"finish":47,"F":42},
    "expanded_G_scope_selected":False,"candidate_compiled":False,"candidate_executed":False,
    "accounting_accepted":False,"implementation_accepted":False}
save("manifest.json",manifest)
save("closure-receipt.json",{"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status":"proposal-ready-for-independent-review-before-root-selection",
    "freeze_command":{"argv":[sys.executable,str(Path(__file__).resolve())],"cwd":str(ROOT),
        "python":sys.version,"source_sha256":sha(Path(__file__).read_bytes()),
        "scope":"standard-library proposal custody and SHA-256 freeze only; no child process"},
    "git_version":(OUT/"commands/git-version/stdout.bin").read_text().strip(),
    "python_version":(OUT/"commands/python-version/stdout.bin").read_text().strip(),
    "revision_context":(OUT/"commands/revision/stdout.bin").read_text().strip(),
    "source_tree_sha256":source_tree_sha256,
    "named_upstream_input_count":len(admission["inputs"]),
    "upstream_complete_admission":"not duplicated; root independently admits historical packets",
    "own_commands":"5 bounded child commands, all returned0 and reaped; metadata/preparation/arithmetic only",
    "runtime_or_compiler_child_started":False,"native_UI_capture_device_or_process_discovery":False,
    "forbidden_hosted_harness_read_import_execute":False,"new_dependency":False,
    "cleanup":"No executable/native/runtime scratch was created. All owned metadata/check children returned. Only assigned persistent proposal files remain; no other project/process/data was changed.",
    "failures":"No formal own command failed; historical upstream R2/final-accounting failures remain unchanged and explicitly unresolved by this unexecuted proposal.",
    "pending":["independent actual-source accounting review","root selection of exact expanded guard ownership and any numeric contract",
        "all corrected-candidate compilation/behavior/layout/API tests","independent behavior and final accounting acceptance",
        "native/UI/capture and physical-device checks paused","product/release/store/FieldLog/GA qualification"],
    "fullReplayAccepted":False,"storedPrefixValidated":False,"semanticMetricsValid":False})
doc=ROOT/"docs/swift-envelope-absent-state-correction.md"
members=[identity(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p.name not in {"seal.json","seal.sha256"}]
members.append(identity(doc))
members.sort(key=lambda p:p["path"])
seal={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope":"New unexecuted isolated absent-state fixture source/funding/validator proposal only; exact upstream packets directly referenced; independent review and root selection pending",
    "status":"proposal-frozen-not-selected-not-executed",
    "candidate_source_sha256":obj("source-binding.json")["candidate"]["sha256"],
    "parent_source_sha256":obj("source-binding.json")["parent"]["sha256"],
    "source_tree_sha256":source_tree_sha256,"members":members,
    "member_count":len(members),"total_bytes":sum(m["bytes"] for m in members),
    "excluded":["proposal-1/seal.json","proposal-1/seal.sha256"],
    "root_selection":False,"accounting_accepted":False,"implementation_accepted":False,
    "compiled_or_executed_candidate":False,"fullReplayAccepted":False,
    "storedPrefixValidated":False,"semanticMetricsValid":False,"GA_qualified":False}
save("seal.json",seal)
digest=sha((OUT/"seal.json").read_bytes())
(OUT/"seal.sha256").write_text(digest+"  seal.json\n")
print(json.dumps({"seal":str((OUT/"seal.json").relative_to(ROOT)),"seal_sha256":digest,
    "member_count":seal["member_count"],"total_bytes":seal["total_bytes"],
    "candidate_source_sha256":seal["candidate_source_sha256"],
    "source_tree_sha256":source_tree_sha256,"manifest":identity(OUT/"manifest.json"),
    "ledger_delta":identity(OUT/"ledger-delta.json"),
    "guard_proposal":identity(OUT/"guard-funding-proposal.json"),
    "validator_table":identity(OUT/"validator-truth-table.json")},sort_keys=True))

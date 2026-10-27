#!/usr/bin/env python3
"""Freeze only the owned independent review after observed successful checks."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

D=Path(__file__).resolve().parent
if (D/"seal.json").exists():raise SystemExit("already-frozen")
def write(name,value):
    (D/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
review=json.loads((D/"review.json").read_text())
controls=json.loads((D/"controls.json").read_text())
if review["status"]!="independent-offline-source-interface-review-pass-root-selection-required" or not controls["passed"]:raise SystemExit("review-not-passed")
attempts=[]
for path in sorted((D/"commands").glob("attempt-*/receipt.json")):
    data=path.read_bytes();receipt=json.loads(data)
    attempts.append({"path":str(path.relative_to(D)),"receipt_sha256":hashlib.sha256(data).hexdigest(),"argv":receipt["argv"],"returncode":receipt["returncode"]})
required=("review.py --check","controls.py --check","verify.py")
for ending in required:
    if not any(" ".join(a["argv"]).endswith(ending) and a["returncode"]==0 for a in attempts):raise SystemExit("missing-success:"+ending)
write("attempt-history.json",{"schema":1,"attempts":attempts,"review_failures_preserved":sum(a["returncode"]!=0 for a in attempts),"exploratory_read_failures_transcribed":3,"failure_dispositions":{"attempt-001":"Checker initially omitted inline-only drop adapter events. Corrected using exact released adapter dispositions, retaining resource payload imports and inherited concrete core normalization.","attempt-002":"Checker hashed full source lines including visibility/indentation. Corrected to the exact fn fragment and its pinned byte length/hash.","attempt-003":"Checker initially required generic zero-policy bb20 in selected positive-policy union. Bound concrete SnapshotAdoptionV1 and retained every selected-policy operation plus conservative shared exits.","attempt-004":"Checker assumed short Vec<u8> alias in graph layout map. Used exact fully qualified observed source146 Vec and TryReserveError layout lines.","attempt-005":"Checker expected serialized dict insertion order to remain original phase order. Canonical serialized candidate sorts keys; verified exact phase membership and original source dispatch order separately."}})
write("cleanup.json",{"schema":1,"scope":"owned independent-review lane only","waited_python_children_only":True,"owned_persistent_processes_started":0,"owned_native_instances_started":0,"owned_capture_or_UI_sessions_started":0,"scratch_created":False,"cleanup_required":False,"native_runtime_checks":"pending-paused","global_process_or_native_inventory_used":False,"other_project_processes_or_data_touched":False,"foreign_or_frozen_writes":False})
write("freeze-receipt.json",{"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"argv":sys.argv,"tool":sys.executable,"tool_version":sys.version,"tool_sha256":hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),"source_tree_sha256":review["source_tree_sha256"],"host_tree_sha256":review["host_tree_sha256"],"candidate_seal_sha256":review["candidate"]["seal_sha256"],"scope":"seal owned source/offline independent evidence only; root amendment selection and all operational grants remain absent"})
members=[]
for path in sorted(D.rglob("*")):
    if path.is_symlink():raise SystemExit("symlink-not-allowed")
    if path.is_file():
        data=path.read_bytes();members.append({"path":str(path.relative_to(D)),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
seal={"schema":1,"status":"frozen-separate-agent-source146-remaining-work-interface-review","source_tree_sha256":review["source_tree_sha256"],"host_tree_sha256":review["host_tree_sha256"],"candidate_seal_sha256":review["candidate"]["seal_sha256"],"review_sha256":hashlib.sha256((D/"review.json").read_bytes()).hexdigest(),"member_count":len(members),"bytes":sum(m["bytes"] for m in members),"members":members,"root_selected_fourteen":False,"accepted_bound":False,"operational_grant":False,"native_or_GA":False}
write("seal.json",seal)
print(json.dumps({"status":seal["status"],"seal_sha256":hashlib.sha256((D/"seal.json").read_bytes()).hexdigest(),"review_sha256":seal["review_sha256"],"members":len(members),"bytes":seal["bytes"],"operational_grant":False}))

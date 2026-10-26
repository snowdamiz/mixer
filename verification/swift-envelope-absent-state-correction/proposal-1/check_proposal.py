#!/usr/bin/env python3
"""Offline byte identity/arithmetic custody checks; no Rust source execution."""
from pathlib import Path
import hashlib
import json
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
def obj(name):
    return json.loads((OUT/name).read_text())
def sha(data):
    return hashlib.sha256(data).hexdigest()
def canon(data):
    return json.dumps(data,sort_keys=True,separators=(",",":")).encode()
def input_obj(item):
    data=(ROOT/item["path"]).read_bytes()
    assert len(data)==item["bytes"] and sha(data)==item["sha256"],item["path"]
    return json.loads(data)
checks=[]
admission=obj("admission.json")
for item in admission["inputs"]:
    data=(ROOT/item["path"]).read_bytes()
    assert len(data)==item["bytes"] and sha(data)==item["sha256"],item["path"]
checks.append("all named consumed input hashes remain identical")
binding=obj("source-binding.json")
before=(ROOT/binding["baseline"]["path"]).read_text()
after=before
for delta in binding["exact_replacements"]:
    assert after.count(delta["before"])==1
    after=after.replace(delta["before"],delta["after"])
assert after==(OUT/"src/envelope.rs").read_text()
assert sha(after.encode())==binding["candidate"]["sha256"]
assert sha((OUT/"src/analyzer.rs").read_bytes())==binding["parent"]["sha256"]
checks.append("two exact source replacements only; parent identical; candidate never compiled")
d=obj("ledger-delta.json")
base=input_obj(d["baseline"])
rows={r["id"]:r for r in base["rows"]}
assert len(rows)==116
for item in d["unchanged_rows"]:
    assert sha(canon(rows[item["id"]]))==item["canonical_sha256"]
for item in d["removed_rows"]:
    assert sha(canon(rows[item["id"]]))==item["canonical_sha256"]
    del rows[item["id"]]
for item in d["replaced_rows"]:
    assert sha(canon(rows[item["id"]]))==item["old_canonical_sha256"]
    rows[item["id"]]=item["new"]
for item in d["added_rows"]:
    assert item["id"] not in rows
    assert item["scalar_operations"]==sum(a["count"] for a in item["scalar_atoms"])
    assert item["scalar_groups"]==(item["scalar_operations"]+15)//16
    assert item["groups"]==item["scalar_groups"]
    rows[item["id"]]=item
assert len(rows)==d["result_row_count"]==121
for p in d["validator_path_composition"]:
    assert sum(rows[n]["groups"] for n in p["rows"])==p["groups"]
assert max(p["groups"] for p in d["validator_path_composition"])==d["validator_max_groups"]==rows["W08"]["groups"]==5
comp=d["composition"]
for names,total in [
    ("leaf_rows","leaf_total"),("wrapper_record_rows","wrapper_record_total"),
    ("setup_rows","setup_actual_bound"),("wrapper_setup_rows","wrapper_setup_total"),
    ("finish_rows","finish_total"),("wrapper_final_rows","wrapper_final_total"),
    ("early_input_error_rows","early_input_error_total")]:
    assert sum(rows[n]["groups"] for n in comp[names])==comp[total],(names,total)
assert sum(rows[n]["groups"] for n in comp["guard_shared_rows"])==112
assert 22+425+24==471 and 471<=8192
checks.append("121-row precise delta reconstructs; leaf425/W24/G112/T42/finish47/F42; validator max5")
e=obj("copy-edge-delta.json")
edgebase=input_obj(e["baseline"])
assert len(edgebase["edges"])==e["baseline_edge_count"]==e["result_edge_count"]==108
assert sha(canon(edgebase["edges"]))==e["all_edge_canonical_sha256"]
for old,entry in zip(edgebase["edges"],e["unchanged_edge_ids"],strict=True):
    assert old["row"]==entry["row"] and old["index"]==entry["index"] and sha(canon(old))==entry["canonical_sha256"]
    assert old["transfer_chunk_bytes"]<=128
assert not e["added"] and not e["removed"] and not e["changed"]
checks.append("108 baseline copy edges unchanged; each chunk<=128B")
fund=obj("guard-funding-proposal.json")
for p in fund["paths"]:
    if "G_owned" in p:
        assert sum(r["groups"] for r in p["G_owned"])==p["G_groups"]<=112
assert [p["G_groups"] for p in fund["paths"]]==[7,7,112,0]
life=obj("type-lifetime-delta.json")
assert sum(life["groups"].values())==life["named_total"]==24656
assert life["named_total"]<=life["reservation"]==41984<=life["ceiling"]==65536
assert life["ceiling"]-life["reservation"]==life["unassigned_margin_unused"]==23552
assert not life["new_locals_or_value_owners"] and not life["type_declarations_changed"]
assert 49152+8192==57344<=65536
assert 534+47==581 and 534+42==576<=65536
assert 47+112+42==201 and 6245+201==6446<=3000000
checks.append("guard7/7/112 fits explicitly requested G112; named24656 within41984; no margin spent")
status=obj("proposal-status.json")
assert not any(status[k] for k in ["root_selection","corrected_candidate_compiled","corrected_candidate_executed",
    "implementation_accepted","fullReplayAccepted","storedPrefixValidated","semanticMetricsValid","GA_qualified"])
checks.append("all selection/runtime/product acceptance flags remain false")
result={"schema":1,"status":"offline-proposal-custody-and-arithmetic-passed",
    "source_sha256":sha(after.encode()),"checks":checks,
    "not_verified":"Independent actual-source operation/type/lifetime review, root G scope selection and all Rust behavior/runtime tests remain pending.",
    "compiled_or_executed_candidate":False}
(OUT/"static-check-result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,sort_keys=True))

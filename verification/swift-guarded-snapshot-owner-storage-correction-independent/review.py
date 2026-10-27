"""Independent correction comparison and mutations; imports no producer code."""
from pathlib import Path
from collections import Counter,defaultdict
import copy,datetime,hashlib,json,platform,re,sys

HERE=Path(__file__).resolve().parent
V=HERE.parent
P=V/"swift-guarded-snapshot-owner-storage-closure"
C=V/"swift-guarded-snapshot-owner-storage-alias-correction"
R=V/"swift-guarded-snapshot-owner-storage-independent/actual-review"
NEW=V/"swift-guarded-snapshot-scope-authority-correction/source/vm/src"
OLD=V/"swift-guarded-snapshot-encoder-implementation/source/vm/src"
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_text())
MAX=(1<<64)-1


def sealed(directory,digest,count,name="seal.json"):
    b=(directory/name).read_bytes();assert sha(b)==digest
    s=json.loads(b);assert len(s["members"])==count
    assert len({m["path"] for m in s["members"]})==count
    for m in s["members"]:
        p=directory/m["path"];assert p.resolve().is_relative_to(directory.resolve())
        b=p.read_bytes();assert (len(b),sha(b))==(m["bytes"],m["sha256"])
    return dict(seal_sha256=digest,members=count,bytes=sum(m["bytes"] for m in s["members"]),all_members_verified=True)


def checked(values):
    total=0
    for n in values:
        assert type(n)is int and 0<=n<=MAX-total
        total+=n
    return total


def source(context,base):
    s=context["source"];ls=(base/s["path"]).read_text().splitlines()[s["start_line"]-1:s["end_line"]]
    if len(ls)==1:return ls[0][s["start_column"]-1:s["end_column"]-1]
    ls[0]=ls[0][s["start_column"]-1:];ls[-1]=ls[-1][:s["end_column"]-1]
    return "\n".join(ls)


def main():
    assert not (HERE/"seal.json").exists(),"frozen review must not be overwritten"
    inputs=[sealed(HERE,"f33fc604a48cf31dbbd2da947f663ef851e1021767269a902ec3d919f17abb34",2,"preaccess-seal.json"),sealed(C,"cd6e7596559b604a0915353c694526ba02d6fd05d4ad2baddf92a4f3bea523ee",75),sealed(P,"afd33c1df35e4072e582789a38c14372f9a8efc4c6243301df4399e4899f2e4b",113),sealed(R,"f5083b7a2cf24d2e8e0ede20b287e5e88c62febb56b053f3d66276cb535f38ed",37),sealed(V/"swift-guarded-snapshot-scope-authority-correction","351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c",225)]
    release=V/"swift-semantic-adapter-root-review/guarded-snapshot-owner-storage-correction-independent-release.json"
    assert sha(release.read_bytes())=="7dfc754484fc88e26e2e4ae808a747923b9d3b5d430c707b6e904d3d00a26e4f"
    prep=read(HERE/"preaccess-expectations.json")
    expected_map={a["new_id"]:a["old_id"] for a in prep["expected_aliases"]}
    candidate=read(C/"inherited-aliases.json")
    aliases=candidate["aliases"];actual_map={a["new_id"]:a["old_id"] for a in aliases}
    def check_map(mapping):
        assert mapping==expected_map
        assert len(mapping)==len(set(mapping.values()))==356
    check_map(actual_map);assert len(aliases)==356 and not candidate["new_legacy_credits_selected"]
    inv=read(P/"inventory.json");raw=read(P/"raw-inventory.json")
    rows={r["id"]:r for r in inv["roles"]}
    rawrows={r["id"]:r for f in raw["functions"]+raw["baseline_functions"] for r in f["roles"]}
    baseline_ids={r["id"] for f in raw["baseline_functions"] for r in f["roles"]}
    assert set(candidate["retained_unused_legacy_ids"])==baseline_ids-set(actual_map.values())
    assert len(candidate["retained_unused_legacy_ids"])==65
    source_contexts=0
    for a in aliases:
        for side,base in [("new",NEW),("old",OLD)]:
            r=rawrows[a[side+"_id"]]
            assert a[side+"_source"]==r["source"]
            assert a[side+"_source_text"]==r["source_text"]
            assert a[side+"_source_member_sha256"]==r["source_member_sha256"]
            assert a[side+"_uses"]==r["uses"]
            assert sha((base/r["source"]["path"]).read_bytes())==r["source_member_sha256"]
            for context in a[side+"_material_use_source_contexts"]:
                assert source(context,base)==context["text"]
                source_contexts+=1
    old_unused={r["id"] for r in read(P/"inherited-aliases.json")["retained_unused_legacy_slots"]}
    assert old_unused<=set(candidate["retained_unused_legacy_ids"])
    assert len(set(candidate["retained_unused_legacy_ids"])-old_unused)==1
    funding=read(C/"funding.json");funding_rows={r["id"]:r for r in funding["roles"]}
    assert len(funding_rows)==len(funding["roles"])==len(rows)==3115
    assert set(funding_rows)==set(rows)
    classes={f["id"]:f["funding_class"] for f in raw["functions"]}
    expected_funding={};totals=Counter();function_totals=defaultdict(Counter)
    for identity,r in rows.items():
        cls=classes[r["template"]];charge={"common-extra":0,"selected-unconditional":0,"admitted-only":0}
        if cls.startswith("shared-"):
            ob=max(a["bytes"] for a in r["actual_variants"] if a["profile"]=="original")
            sb=max(a["bytes"] for a in r["actual_variants"] if a["profile"]=="selected")
            charge["common-extra"]=0 if identity in expected_map else ob
            charge["selected-unconditional"]=max(0,sb-ob)
        elif cls=="common":charge["common-extra"]=0 if identity in expected_map else r["bytes"]
        else:charge[cls]=r["bytes"]
        assert funding_rows[identity]["funding"]==charge
        assert funding_rows[identity]["inherited_old_id"]==expected_map.get(identity)
        expected_funding[identity]=charge;totals.update(charge);function_totals[r["template"]].update(charge)
    assert dict(totals)==prep["expected_owner_only_funding"]
    assert funding["owner_only_formulas"]==dict(totals)
    assert funding["encoder_join"]==inv["encoder_join"]
    joined=dict(totals);joined["selected-unconditional"]+=256;joined["admitted-only"]+=40275
    assert funding["formulas"]==joined=={k:v for k,v in prep["expected_joined_funding"].items() if k!="host-caller"}
    assert funding["host_caller_bytes"]==81327
    assert joined["common-extra"]-inv["formulas"]["common-extra"]==1096
    optional=read(C/"optional-credits-unselected.json");assert optional["selected"]is False
    assert len(optional["correspondences"])==2
    for opt in optional["correspondences"]:
        identity=opt["new_id"]
        assert identity not in actual_map
        assert funding_rows[identity]["funding"]==rows[identity]["funding"]
        assert funding_rows[identity]["funding"]["common-extra"]==1096
    full=read(R/"complete-calls-and-callbacks.json");calls=read(C/"call-boundaries.json")
    callkey=lambda r:(r["caller"],r["call_result_role"],r["target"],r["source_statement"])
    expected_calls=Counter(map(callkey,full["calls"]))
    def check_calls(data):assert Counter(map(callkey,data))==expected_calls
    check_calls(calls["calls"]);assert len(calls["calls"])==627
    expected_callbacks=Counter((e["from"],e["to"],e["result"]) for e in full["actual_owned_callback_edges"])
    actual_callbacks=Counter((r["caller"],callee,r["call_result_role"]) for r in calls["calls"] for callee in r["owned_callbacks"])
    def check_callbacks(data):assert data==expected_callbacks
    check_callbacks(actual_callbacks);assert sum(actual_callbacks.values())==18
    assert calls["inherited_callees"]==read(P/"call-boundaries.json")["inherited_callees"]
    assert not calls["unresolved"]
    graph=defaultdict(set)
    for edge in calls["edges"]:graph[edge["from"]].add(edge["to"])
    active=set();done=set()
    def visit(node):
        assert node not in active
        if node in done:return
        active.add(node)
        for child in graph[node]:visit(child)
        active.remove(node);done.add(node)
    for node in list(graph):visit(node)
    delta=read(C/"call-delta.json");assert delta["complete_target_changes"]==107 and len(delta["added_owned_callback_edges"])==2
    constants=(C/"checked-recipe-constants.rs").read_text()
    computed_constants={}
    for name,cls,extra in [("COMMON_EXTRA","common-extra",0),("SELECTED_UNCONDITIONAL","selected-unconditional",256),("ADMITTED_ONLY","admitted-only",40275)]:
        match=re.search(r"pub const "+name+r":u64=0u64(.*?);",constants,re.S);assert match
        terms=[int(n) for n in re.findall(r"\.checked_add\((\d+)\)",match[1])]
        assert checked(terms)==checked([costs[cls] for costs in function_totals.values()]+[extra])==joined[cls]
        computed_constants[name]=checked(terms)
    assert checked([*joined.values(),81327])==1531209
    # Focused finite mutations use actual frozen identities and call occurrences.
    controls=[]
    def reject(name,fn):
        try:fn()
        except AssertionError:controls.append({"name":name,"rejected":True})
        else:raise AssertionError("control accepted: "+name)
    original_map={a["new_id"]:a["old_id"] for a in read(P/"inherited-aliases.json")["aliases"]}
    for identity in prep["affected_original_aliases"]:
        bad=dict(expected_map);bad[identity]=original_map[identity]
        reject("original alias restored: "+identity,lambda bad=bad:check_map(bad))
    for n,d in enumerate(full["target_display_differences"]):
        bad=copy.deepcopy(calls["calls"])
        row=next(r for r in bad if r["caller"]==d["caller"] and r["call_result_role"]==d["result"] and r["target"]==d["complete_target"])
        row["target"]=d["truncated_target"]
        reject("target truncation occurrence "+str(n),lambda bad=bad:check_calls(bad))
    for e in full["actual_owned_callback_edges"]:
        if not e["producer_callback_present"]:
            bad=actual_callbacks.copy();bad[(e["from"],e["to"],e["result"]) ]-=1
            reject("missing callback: "+e["from"],lambda bad=bad:check_callbacks(bad))
    for opt in optional["correspondences"]:
        identity=opt["new_id"];bad=copy.deepcopy(funding_rows[identity]["funding"]);bad["common-extra"]=0
        reject("unselected optional credit: "+identity,lambda bad=bad,identity=identity:(_ for _ in ()).throw(AssertionError()) if bad!=expected_funding[identity] else None)
    failure=read(R/"failure-boundary-finding.json")["current_role"]["id"]
    assert expected_funding[failure]["common-extra"]==1096
    reject("u64 overflow",lambda:checked([MAX,1]))
    reject("duplicate role identity",lambda:(_ for _ in ()).throw(AssertionError()) if len(list(rows)+[next(iter(rows))])!=len(set(list(rows)+[next(iter(rows))])) else None)
    reject("omitted role identity",lambda:(_ for _ in ()).throw(AssertionError()) if set(list(rows)[1:])!=set(rows) else None)
    (HERE/"controls.json").write_text(json.dumps({"schema":1,"count":len(controls),"all_rejected":True,"controls":controls,"scope":"actual source/evidence identity and arithmetic mutation checks; no engine execution"},indent=2)+"\n")
    report=dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status="accepted-bounded-correction-evidence-pending-root-acceptance",command=[sys.executable,str(Path(__file__).resolve())],python_version=platform.python_version(),inputs=inputs,source_tree_sha256=prep["source_tree_sha256"],unchanged_original_producer=True,aliases=356,retained_unused_legacy_roles=65,all29findings_reconciled=True,material_use_source_contexts_verified=source_contexts,roles=3115,templates=81,common_extra=78240,selected_unconditional=941467,admitted_only=430175,host_caller=81327,common_delta=1096,optional_credit2192_selected=False,owner_only_recomputed=dict(totals),constants_recomputed=computed_constants,call_statements=627,full_targets_repaired=107,callback_edges_repaired=2,owned_callback_edges=18,complete_graph_acyclic=True,targeted_negative_controls=len(controls),new_compiler_builds=0,compiler_scope="Reused exact frozen independent production/unit/baseline MIR and independently decoded raw compiler layout provenance; no unchanged-source rebuild needed",runtime_executions=0,paused_surface_or_process_inventory_executions=0,canonical_or_git_mutations=False,emission_helper_read=False,complete_operational_floor_selected=False,production_caller_accepted=False,healthy_cleanup_accepted=False,GA_gates_verified=0)
    (HERE/"review.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ["status","aliases","retained_unused_legacy_roles","common_extra","selected_unconditional","admitted_only","host_caller","targeted_negative_controls"]}))


if __name__=="__main__":main()

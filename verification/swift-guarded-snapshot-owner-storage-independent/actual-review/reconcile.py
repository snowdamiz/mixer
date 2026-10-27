"""Independent fresh MIR declaration/source/call reconciliation; no producer imports."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, re, datetime, platform

HERE=Path(__file__).resolve().parent
V=HERE.parents[1]
P=V/"swift-guarded-snapshot-owner-storage-closure"
SOURCE=V/"swift-guarded-snapshot-scope-authority-correction/source/vm"
BASE=str(SOURCE/"src")+"/"
sha=lambda x:hashlib.sha256(x).hexdigest()
read=lambda p:json.loads(p.read_text())


def bodies(text):
    out=defaultdict(list)
    for m in re.finditer(r"(?m)^fn [^\n]*\n.*?^}",text,re.S|re.M):
        body=m[0].replace(BASE,"source/")
        header=body.splitlines()[0]
        out[header].append(body)
    return out


def parameters(text):
    parts=[];stack=[];at=0
    for i,c in enumerate(text):
        if c in "<([{":stack.append(c)
        elif c in ">)]}" and not(c==">" and i and text[i-1]=="-"):stack.pop()
        elif c=="," and not stack:parts.append(text[at:i].strip());at=i+1
    parts.append(text[at:].strip())
    return dict(s.split(": ",1) for s in parts if s)


def declarations(body):
    header=body.splitlines()[0]
    args=parameters(header[header.index("(")+1:header.rindex(") ->")])
    decl=dict(args)
    for m in re.finditer(r"(?m)^\s+let (?:mut )?(_\d+): (.*?);\s*//",body):
        assert m[1] not in decl
        decl[m[1]]=m[2]
    return decl,args


def source_text(role,vm):
    s=role["source"];b=(vm/"src"/s["path"]).read_bytes()
    assert sha(b)==role["source_member_sha256"]
    lines=b.decode().splitlines()[s["start_line"]-1:s["end_line"]]
    if len(lines)==1:return lines[0][s["start_column"]-1:s["end_column"]-1]
    lines[0]=lines[0][s["start_column"]-1:];lines[-1]=lines[-1][:s["end_column"]-1]
    return "\n".join(lines)


def calls(body):
    out=[]
    for line in body.splitlines():
        code=line.strip().split("; //",1)[0]
        if not re.match(r"_\d+ = ",code) or ") -> [" not in code:continue
        dest,expr=code.split(" = ",1);last=expr.rindex(") -> [");depth=1;i=last-1
        while i>=0:
            if expr[i]==")":depth+=1
            elif expr[i]=="(":
                depth-=1
                if depth==0:break
            i-=1
        assert i>=0
        out.append((dest,expr[:i],line.strip()))
    return out


def main():
    raw=read(P/"raw-inventory.json");inv=read(P/"inventory.json")
    fresh={ctx:bodies((HERE/"owned-work"/(ctx+".mir")).read_text()) for ctx in ["production","unit"]}
    supplied=bodies((P/"function-bodies.mir").read_text())
    invroles={r["id"]:r for r in inv["roles"]}
    assert len(invroIes:=invroles)==len(inv["roles"])
    unit_by_origin=defaultdict(list)
    for rows in fresh["unit"].values():
        for body in rows:
            origin=re.search(r"// return place in scope \d+ at source/([^:]+):(\d+):",body)
            if origin:unit_by_origin[(origin[1],int(origin[2]))].append(body)
    summaries=[];call_rows=[];slot_count=0;macro_fallback=[]
    selected_text=[]
    for f in raw["functions"]:
        header=f["header"];matches=fresh["production"][header]
        assert len(matches)==1,(header,len(matches))
        body=matches[0]
        assert supplied[header]==[body],f["id"]
        declared,args=declarations(body)
        assert declared=={r["mir_local"]:r["compiler_type"] for r in f["roles"]},f["id"]
        for r in f["roles"]:
            assert source_text(r,SOURCE)==r["source_text"],r["id"]
            assert r["id"] in invroles and invroles[r["id"]]["multiplicity"]==1
            assert all(invroIes[r["id"]][k]==r[k] for k in ["compiler_type","source","source_text","kind","mir_local"])
            if not r["product_source_span_found"] and r["kind"] not in ["parameter"]:macro_fallback.append(r["id"])
        for dest,target,line in calls(body):call_rows.append(dict(caller=f["id"],call_result_role=f["id"]+"::"+dest,target=target,source_statement=line))
        unit=unit_by_origin[(f["source"]["path"],f["source"]["return_line"])]
        assert len(unit)==1,("unit",header,len(unit))
        unitdecl,_=declarations(unit[0])
        summaries.append(dict(id=f["id"],roles=len(declared),parameters=len(args),fresh_body_sha256=sha(body.encode()),unit_roles=len(unitdecl)))
        selected_text.append(body);slot_count+=len(declared)
    assert len(invroles)==slot_count
    assert {r["id"] for f in raw["functions"] for r in f["roles"]}==set(invroles)
    expected=read(P/"call-boundaries.json")
    simple=lambda r:(r["caller"],r["call_result_role"],r["target"],r["source_statement"])
    actual_calls=Counter(map(simple,call_rows));expected_calls=Counter(map(simple,expected["calls"]))
    call_difference={"fresh_only":[list(k) for k in (actual_calls-expected_calls)],"producer_only":[list(k) for k in (expected_calls-actual_calls)]}
    (HERE/"call-target-differences.json").write_text(json.dumps(call_difference,indent=2)+"\n")
    site=lambda r:(r["caller"],r["call_result_role"],r["source_statement"])
    assert Counter(map(site,call_rows))==Counter(map(site,expected["calls"]))
    by_site={site(r):r for r in call_rows}
    target_display_differences=[];callback_edges=[]
    callback_types={}
    for f in raw["functions"]:
        if "{closure#" in f["id"]:
            typ=re.search(r"\{closure@source/[^}]+\}",f["header"])
            assert typ
            callback_types[typ[0]]=f["id"]
    graph=defaultdict(set)
    for r in expected["calls"]:
        fresh_call=by_site[site(r)]
        if fresh_call["target"]!=r["target"]:
            assert fresh_call["target"].startswith(r["target"])
            target_display_differences.append({"caller":r["caller"],"result":r["call_result_role"],"complete_target":fresh_call["target"],"truncated_target":r["target"]})
        for callee in r.get("callee_role_templates",[]):graph[r["caller"]].add(callee)
        for typ,callee in callback_types.items():
            if typ in fresh_call["target"]:
                graph[r["caller"]].add(callee)
                callback_edges.append({"from":r["caller"],"to":callee,"result":r["call_result_role"],"producer_callback_present":callee in r["owned_callbacks"]})
    active=set();done=set()
    def visit(node):
        assert node not in active,("recursive owner template",node)
        if node in done:return
        active.add(node)
        for child in graph[node]:visit(child)
        active.remove(node);done.add(node)
    for node in list(graph):visit(node)
    (HERE/"complete-calls-and-callbacks.json").write_text(json.dumps({"schema":1,"calls":call_rows,"target_display_differences":target_display_differences,"actual_owned_callback_edges":callback_edges,"acyclic_after_complete_callback_reconstruction":True},indent=2)+"\n")
    host=read(P/"host-caller.json")["function"]
    assert len(fresh["unit"][host["header"]])==1
    hbody=fresh["unit"][host["header"]][0]
    assert (P/"host-caller.mir").read_text().strip()==hbody
    hd,_=declarations(hbody)
    assert hd=={r["mir_local"]:r["compiler_type"] for r in host["roles"]}
    for r in host["roles"]:assert source_text(r,SOURCE)==r["source_text"]
    hc=calls(hbody)
    getter=[c for c in hc if c[1].endswith("::outer_v1")]
    assert len(getter)==1
    # Explicit independent caller boundary, including conservative claim-literal
    # and match-discriminant roles beyond the 16 preaccess expression seeds.
    product_slots={0,1,3,*range(4,14),*range(29,38),*range(70,94),*range(125,129),167,168,215}
    actual_slots={int(r["mir_local"][1:]) for r in host["roles"] if r["funding_class"]=="host-caller"}
    assert actual_slots==product_slots,(actual_slots^product_slots)
    assert len(product_slots)==53 and len(hd)==216
    htotal=sum(r["bytes"] for r in host["roles"] if r["funding_class"]=="host-caller")
    # Independent arithmetic from per-role actual generic alternatives and alias
    # status. This does not approve the alias identities or select a floor.
    classes={f["id"]:f["funding_class"] for f in raw["functions"]}
    totals=Counter();generic_counts=Counter()
    for r in inv["roles"]:
        alts=r["actual_variants"]
        assert r["bytes"]==max(a["bytes"] for a in alts)
        for a in alts:
            if a["unit"]:assert a["bytes"]==max(a["production"]["bytes"],a["unit"]["bytes"])
            else:assert a["bytes"]==a["production"]["bytes"]
        cls=classes[r["template"]];charge=Counter()
        if cls.startswith("shared-"):
            original=max(a["bytes"] for a in alts if a["profile"]=="original")
            selected=max(a["bytes"] for a in alts if a["profile"]=="selected")
            charge["common-extra"]=0 if r["inherited_alias"] else original
            charge["selected-unconditional"]=max(0,selected-original)
            assert {a["profile"] for a in alts}=={"original","selected"}
        elif cls=="common":charge["common-extra"]=0 if r["inherited_alias"] else r["bytes"]
        else:charge[cls]=r["bytes"]
        assert all(r["funding"][k]==charge[k] for k in r["funding"])
        totals.update(charge)
        if "::io_result" in r["template"]:assert {a["T"] for a in alts}=={"std::fs::Metadata","u64"}
        if "::encode_result" in r["template"]:assert {a["T"] for a in alts}=={"SnapshotViewV2<'_>","SnapshotCursorV2<'_>","Option<SnapshotBlockV2<'_>>"}
    aliases=read(P/"inherited-aliases.json")["aliases"]
    assert len({a["new_id"] for a in aliases})==len(aliases)==len({a["old_id"] for a in aliases})
    # All actual direct block/transfer/storage types are source-derived; None
    # slots carry their full measured inline representation and never A funding.
    refusal=[]
    for r in inv["roles"]:
        if "SnapshotPhaseStorageV1" in r["compiler_type"] and not r["compiler_type"].startswith("&"):
            assert r["funding"]["admitted-only"]==0
            refusal.append(r["id"])
    report=dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),python_version=platform.python_version(),source_tree_sha256="575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896",fresh_production_and_unit_MIR=True,functions=len(summaries),roles=slot_count,materialized_declarations_complete=True,source_spans_verified=slot_count,compiler_macro_origin_fallbacks=macro_fallback,call_sites=len(call_rows),call_statements_exactly_reproduced=True,truncated_target_displays=len(target_display_differences),callback_edges_missing_from_producer=sum(not e["producer_callback_present"] for e in callback_edges),complete_owner_callback_graph_acyclic=True,host_roles=len(hd),host_product_roles=53,host_external_harness_roles=163,host_bytes_recomputed=htotal,outer_getter_calls=1,owner_only_recomputed=dict(totals),aliases_unique_but_source_identity_finding_open=True,full_phase_storage_roles_before_admission=refusal,function_summaries=summaries,acceptance=False)
    (HERE/"reconciliation.json").write_text(json.dumps(report,indent=2)+"\n")
    (HERE/"fresh-owner-bodies.mir").write_text("\n\n".join(selected_text)+"\n")
    (HERE/"fresh-host-caller.mir").write_text(hbody+"\n")
    print(json.dumps({k:report[k] for k in ["functions","roles","call_sites","host_bytes_recomputed","owner_only_recomputed","acceptance"]}))


if __name__=="__main__":main()

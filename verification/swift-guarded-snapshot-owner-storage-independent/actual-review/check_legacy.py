"""Fresh old/current declaration custody and legacy callee verification."""
from pathlib import Path
import hashlib,json,re
from reconcile import bodies,declarations,HERE,P,SOURCE,BASE,source_text

OLD=HERE.parents[1]/"swift-guarded-snapshot-encoder-implementation/source/vm"
OLD_BASE=str(OLD/"src")+"/"
read=lambda p:json.loads(p.read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()


def catalog(text):
    out={}
    for rows in bodies(text).values():
        for body in rows:
            m=re.search(r"// return place in scope \d+ at source/([^:]+):(\d+):",body)
            if m:out.setdefault((m[1],int(m[2])),[]).append(body)
    return out


def closure(text,vm):
    def sub(m):
        lines=(vm/"src"/m[1]).read_text().splitlines()[int(m[2])-1:int(m[4])]
        if len(lines)==1:s=lines[0][int(m[3])-1:int(m[5])-1]
        else:lines[0]=lines[0][int(m[3])-1:];lines[-1]=lines[-1][:int(m[5])-1];s="\n".join(lines)
        return "{closure-source:"+sha(re.sub(r"\s+","",s).encode())+"}"
    return re.sub(r"\{closure@source/([^:]+):(\d+):(\d+): (\d+):(\d+)\}",sub,text)


def semantic(body,vm):
    body="\n".join(line.split("//",1)[0].rstrip() for line in body.splitlines())
    body=re.sub(r"<impl at [^>]+>","<same-source-impl>",body)
    body=closure(body,vm)
    return re.sub(r"alloc[0-9]+","same-immutable-allocation-identity",body)


def main():
    oldtext=(HERE/"owned-work/baseline.mir").read_text().replace(OLD_BASE,"source/")
    newtext=(HERE/"owned-work/production.mir").read_text().replace(BASE,"source/")
    oldb=bodies(oldtext);oldcat=catalog(oldtext);newcat=catalog(newtext)
    raw=read(P/"raw-inventory.json")
    baseline_roles=0
    for f in raw["baseline_functions"]:
        matches=oldb[f["header"]];assert len(matches)==1
        decl,_=declarations(matches[0]);assert decl=={r["mir_local"]:r["compiler_type"] for r in f["roles"]}
        for r in f["roles"]:assert source_text(r,OLD)==r["source_text"]
        baseline_roles+=len(decl)
    retained=[];old_bodies=[];new_bodies=[]
    for c in read(P/"call-boundaries.json")["inherited_callees"]:
        n,o=c["current"],c["accepted_old"]
        ns=newcat[(n["path"],n["return_line"])];os=oldcat[(o["path"],o["return_line"])]
        nh=[sha(semantic(b,SOURCE).encode()) for b in ns];oh=[sha(semantic(b,OLD).encode()) for b in os]
        assert n["logical_mir_sha256"] in nh and o["logical_mir_sha256"] in oh
        assert n["logical_mir_sha256"]==o["logical_mir_sha256"]
        new_bodies.append(ns[nh.index(n["logical_mir_sha256"])])
        old_bodies.append(os[oh.index(o["logical_mir_sha256"])])
        retained.append(dict(current=n,baseline=o,independently_reproduced=True))
    result=dict(schema=1,fresh_baseline_source_members=144,baseline_tree_sha256="447719d8fef2928674d9d196266408ca72c70ce152cf0251807d2c3bcd7e7c43",baseline_templates=9,baseline_roles=baseline_roles,fresh_legacy_callee_fingerprints=len(retained),legacy_callees=retained,scope="Exact fresh old/current MIR plus source spans; declared source aliases still fail independent occurrence identity review",acceptance=False)
    (HERE/"legacy-reproduction.json").write_text(json.dumps(result,indent=2)+"\n")
    (HERE/"fresh-legacy-current.mir").write_text("\n\n".join(new_bodies)+"\n")
    (HERE/"fresh-legacy-baseline.mir").write_text("\n\n".join(old_bodies)+"\n")
    print(json.dumps({k:result[k] for k in ["baseline_templates","baseline_roles","fresh_legacy_callee_fingerprints"]}))


if __name__=="__main__":main()

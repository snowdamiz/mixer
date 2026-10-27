"""Freeze only this independent correction review; performs no product action."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not (HERE/"seal.json").exists()
r=json.loads((HERE/"review.json").read_text())
assert r["status"]=="accepted-bounded-correction-evidence-pending-root-acceptance"
assert r["targeted_negative_controls"]==143 and r["common_delta"]==1096
assert r["runtime_executions"]==r["new_compiler_builds"]==r["GA_gates_verified"]==0
members=[]
for p in sorted(HERE.rglob("*")):
    if p.is_file():
        b=p.read_bytes();members.append({"path":str(p.relative_to(HERE)),"bytes":len(b),"sha256":sha(b)})
s={"schema":1,"member_count":len(members),"total_bytes":sum(m["bytes"] for m in members),"members":members,"scope":"Independent bounded owner-storage correction evidence passed; root acceptance pending; no source integration/runtime/floor/GA grant"}
(HERE/"seal.json").write_text(json.dumps(s,indent=2)+"\n")
print(json.dumps({"seal_sha256":sha((HERE/"seal.json").read_bytes()),"members":len(members),"bytes":s["total_bytes"]}))

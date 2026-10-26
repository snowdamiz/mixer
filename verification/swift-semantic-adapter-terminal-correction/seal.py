"""Seal only the new R1 correction after its bounded checks and old custody."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

import prepare

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]

def sha(raw):return hashlib.sha256(raw).hexdigest()

def dump(path,value):
    with path.open("x") as output:
        json.dump(value,output,indent=2,sort_keys=True);output.write("\n")

def main():
    if (BASE/"seal.json").exists() or (BASE/"final-receipt.json").exists():
        raise SystemExit("Refuse to overwrite final evidence")
    attempts=sorted((BASE/"attempts").glob("run-*/receipt.json"),key=lambda p:int(p.parent.name.split("-")[1]))
    latest=attempts[-1];result=json.loads(latest.read_text())
    if not result["passed"] or not result["authored_source_before_equal_after"]:
        raise SystemExit("Latest contract/source check attempt did not pass")
    for row in json.loads((latest.parent/"source-before.json").read_text()):
        raw=(ROOT/row["path"]).read_bytes()
        if len(raw)!=row["bytes"] or sha(raw)!=row["sha256"]:
            raise SystemExit("Authored source drift: "+row["path"])
    for path in latest.parent.glob("*.json"):
        if path.name in {"receipt.json","source-before.json","source-after.json"}:continue
        command=json.loads(path.read_text())
        for suffix in ["stdout","stderr"]:
            raw=path.with_suffix("."+suffix).read_bytes()
            if len(raw)!=command[suffix+"_bytes"] or sha(raw)!=command[suffix+"_sha256"]:
                raise SystemExit("Command stream drift: "+str(path))
    old=prepare.check_old();inputs=json.loads((BASE/"input-manifest.json").read_text())
    if old!=inputs["old_seals_before"]:raise SystemExit("Old custody changed")
    receipt={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "status":"sealed bounded R1 terminal contract correction; independent review and root selection pending",
      "scope":"new correction document/directory only; no product or old packet changes",
      "argv":sys.argv,"context_revision":inputs["context_revision"],
      "consulted_tree_sha256":inputs["consulted_tree_sha256"],
      "task_contract":{"model":"gpt-6.1-sol","reasoning_effort":"xhigh","context":"bounded continuation"},
      "qualification_receipt":str(latest.relative_to(ROOT)),"qualification_receipt_sha256":sha(latest.read_bytes()),
      "methods_per_normal_and_optimized_mode":12,"literal_projection_cases":56,"literal_normalization_cases":41,
      "cartesian_cases_per_mode":10560,"all16rows_exercised":True,"Rust_product_tests":0,
      "old_seals_before_and_after_equal":True,"old_seals_after":old,
      "outerErr_has_observation":False,"all_four_authority_getters":False,
      "new_debit_layout_lifetime_bounds":"unchanged provisional ceilings; actual Rust proof pending",
      "preserved_attempts":["preparation-failure-1.json"]+[str(p.parent.relative_to(BASE)) for p in attempts],
      "cleanup":result["cleanup"],"old_source_model_or_harness_execution":False,
      "product_profile_dependency_CI_root_metadata_changes":False,"commit_or_push":False,
      "pending":["independent correction review and root contract acceptance","root implementation selection","actual Rust source, combined source/move/debit/lifetime/layout and independent actual-File tests","real authority adapters and target/native/device/full product gates"]}
    dump(BASE/"final-receipt.json",receipt)
    paths=[ROOT/"docs/swift-semantic-adapter-terminal-correction.md"]
    paths += [p for p in BASE.rglob("*") if p.is_file() and p.name not in {"seal.json","seal.sha256"}]
    rows=[]
    for path in sorted(paths):
        raw=path.read_bytes();rows.append({"path":str(path.relative_to(ROOT)),"bytes":len(raw),"sha256":sha(raw)})
    seal={"schema":1,"scope":"only owned R1 correction document/directory","members":rows,
          "member_count":len(rows),"member_bytes":sum(r["bytes"] for r in rows),
          "excluded":[str((BASE/"seal.json").relative_to(ROOT)),str((BASE/"seal.sha256").relative_to(ROOT))]}
    dump(BASE/"seal.json",seal);value=sha((BASE/"seal.json").read_bytes())
    (BASE/"seal.sha256").write_text(value+"  "+str((BASE/"seal.json").relative_to(ROOT))+"\n")
    print(json.dumps({"seal_sha256":value,"members":len(rows),"bytes":seal["member_bytes"],
       "document_sha256":sha((ROOT/"docs/swift-semantic-adapter-terminal-correction.md").read_bytes()),
       "contract_sha256":sha((BASE/"terminal-contract.json").read_bytes()),
       "model_sha256":sha((BASE/"classifier.py").read_bytes()),
       "expected_sha256":sha((BASE/"expected-cases.json").read_bytes()),
       "final_receipt_sha256":sha((BASE/"final-receipt.json").read_bytes())}))

if __name__=="__main__":main()

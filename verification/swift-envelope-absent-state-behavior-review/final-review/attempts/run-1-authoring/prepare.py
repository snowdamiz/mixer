#!/usr/bin/env python3
"""Admit selected inputs and make byte-identical source copies for own tests."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PROPOSAL = ROOT / "verification/swift-envelope-absent-state-correction/proposal-1"
PINS = {
 "verification/swift-ordered-retention-analyzer-envelope-root-review/absence-correction-selection.json": "ae90b289519d0588a27cae4db0a7ce4a74ce3016c9c2f790fd962775ec4fd2e0",
 "verification/swift-envelope-absent-state-correction/proposal-1/seal.json": "3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c",
 "verification/swift-envelope-absent-state-accounting-review/seal.json": "c9191a26ed0c5081e9c2ad97082fc61cee3f6eeb94ea49c4be5028b0f54536e4",
 "verification/swift-envelope-absent-state-behavior-review/preaccess-seal.json": "e24d3bd09fd5bf07e5df86a03df2ca285eaea5837245666b3718c33b15fc56a4",
 "verification/swift-envelope-absent-state-behavior-review/preaccess-correction/seal.json": "485346537ab2c34bfeb14ff630c07bb9be7cd7fe3a9a7bceae59dcb1679debfd",
}

def info(path):
 b=path.read_bytes(); return {"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)}

def main():
 verified=[]
 for name, expected in PINS.items():
  path=ROOT/name; assert info(path)["sha256"]==expected,name
  value=json.loads(path.read_text())
  if "members" in value:
   members=value["members"]
   if isinstance(members,dict): members=[{"path":k,**v} for k,v in members.items()]
   for m in members:
    assert info(ROOT/m["path"])=={"sha256":m["sha256"],"bytes":m["bytes"]},m["path"]
   verified.append({"seal":name,"sha256":expected,"members":len(members)})
 source_pins={"analyzer.rs":"1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b","envelope.rs":"2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef"}
 for name,expected in source_pins.items():
  source=PROPOSAL/"src"/name; assert info(source)["sha256"]==expected
  dest=OUT/"source"/name; dest.parent.mkdir(exist_ok=True); dest.write_bytes(source.read_bytes())
  assert info(dest)==info(source)
 (OUT/"tests").mkdir(exist_ok=True)
 (OUT/"tests/fixture_tests.rs").write_text("// Intentionally empty: no producer test module is copied or run.\n")
 (OUT/"tests/correction_tests.rs").write_text("// All independently authored controls are in envelope_tests.rs.\n")
 supplement=json.loads((OUT.parent/"preaccess-correction/contract-supplement.json").read_text())
 lines=["// Generated only from the independently frozen corrected preaccess table.","const CALLER_CASES: &[(&str,u64,u64,u64,u64,u64,bool)] = &["]
 for row in supplement["poststate_vectors"]:
  shape=row.get("shape","")
  status,reason=(3,15) if "status3-reason15" in shape else (2,1) if "status2-reason1" in shape else (1,1) if "status1-reason1" in shape else (1,0)
  values=[str(row[k]).lower() for k in ["remaining","spent","debit"]]
  lines.append(' ("'+row["id"]+'",'+','.join(values)+f',{status},{reason},'+str(row["correction_expected"]).lower()+'),')
 lines.append("];\n")
 (OUT/"tests/caller_cases.rs").write_text("\n".join(lines))
 report={"schema":1,"admitted_packets":verified,"exact_source_copies":{name:info(OUT/"source"/name) for name in source_pins},"producer_scripts_or_tests_executed":False,"original10members_unchanged":True,"generated_caller_vectors":len(supplement["poststate_vectors"])}
 (OUT/"source-admission.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 print(json.dumps(report,sort_keys=True))

if __name__=="__main__": main()

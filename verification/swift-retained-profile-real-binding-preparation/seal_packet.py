"""One-shot closure for this new preparation packet, not an input producer."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent

def main():
    assert not (HERE/"seal.json").exists(),"packet already frozen"
    members=[]
    for file in sorted(HERE.rglob("*")):
        assert not file.is_symlink(),file
        if not file.is_file():continue
        data=file.read_bytes()
        members.append({"path":str(file.relative_to(HERE)),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
    seal={"schema":1,"status":"closed-source-backed-real-binding-contract-proposal-awaiting-root-selection","member_count":len(members),"member_bytes":sum(m["bytes"] for m in members),"members":members,"source_revision_context":json.loads((HERE/"receipt.json").read_text())["source_revision"],"actual_product_engine_behavior_executed":False,"canonical_real_binding_native_FieldLog_OTA_GA_accepted":False,"self_seal":"seal.json excluded; no sidecar declared"}
    data=(json.dumps(seal,indent=2)+"\n").encode()
    (HERE/"seal.json").write_bytes(data)
    print(json.dumps({"seal_sha256":hashlib.sha256(data).hexdigest(),"members":len(members),"bytes":seal["member_bytes"]}))

if __name__=="__main__":main()

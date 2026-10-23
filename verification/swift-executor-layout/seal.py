#!/usr/bin/env python3
"""Seal the bounded lane's exact review inputs; never claim root acceptance."""
from pathlib import Path
import hashlib,json,shutil,subprocess
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    receipt=json.loads((OUT/'receipt.json').read_text())
    assert receipt['status']=='complete' and receipt['input_bytes_unchanged']
    files=receipt['owned_source_sha256']
    for p,digest in files.items():
        assert sha(ROOT/p)==digest,(p,'source changed after collection')
        q=OUT/'source-freeze'/p;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,q)
    # Existing tracked source remains root-owned; only the exact integration
    # patch is frozen here. Source at the recorded baseline plus these four
    # files and measurement overlay reconstructs the compiled source tree.
    assert not subprocess.check_output(['git','diff','--name-only','--','vm'],cwd=ROOT,text=True).strip(),'existing VM source changed; new exact collection required'
    artifacts={}
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or any(x in {'tree','build','__pycache__'} for x in p.relative_to(OUT).parts):continue
        if p.name in {'source-freeze.json','receipt.partial.json'}:continue
        artifacts[str(p.relative_to(ROOT))]=sha(p)
    artifacts['docs/swift-executor-layout.md']=sha(ROOT/'docs/swift-executor-layout.md')
    payload={'schema':'mixer.swift-executor-layout-source-freeze.v1','revision':receipt['revision'],'owned_source':files,'artifacts':artifacts,'working_existing_vm_bytes_unchanged':True,'root_wiring_integrated':False,'prerequisite_accepted':False,'executor_implementation_accepted':False,'foundation_final_boundary_accepted':False,'pending':'Independent root-owned complete final-boundary foundation inventory/correction and review. No implementation, target, device or GA acceptance.'}
    (OUT/'source-freeze.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({'owned_files':len(files),'artifact_bindings':len(artifacts),'status':'sealed review input; root acceptance pending'}))
if __name__=='__main__':main()

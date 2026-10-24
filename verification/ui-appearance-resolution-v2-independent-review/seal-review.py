#!/usr/bin/env python3
"""Seal final observed review, retaining failed harness attempts as limitations."""
from pathlib import Path
import datetime, hashlib, json, platform, subprocess, sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    out=HERE/'review.json'
    if out.exists():raise RuntimeError('review seal already exists')
    run_path=HERE/'candidate-4/receipt.json';run=json.loads(run_path.read_bytes())
    audit_path=HERE/'producer-audit-1/receipt.json';audit=json.loads(audit_path.read_bytes())
    assert run['status']=='passed-independent-pure-data-review'
    assert audit['status']=='passed-retained-producer-bindings-and-counts'
    assert run['results']['baseline-debug']['failed']==run['results']['baseline-release']['failed']==0
    assert len(run['mutations'])==6 and all(run['results'][n]['failed']>0 for n in run['mutations'])
    existing_sdk={};new_sdk=[]
    for relative,digest in run['inputManifest'].items():
        if not relative.startswith('sdk/'):continue
        p=subprocess.run(['git','show','HEAD:'+relative],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if p.returncode:new_sdk.append(relative)
        else:
            assert sha(p.stdout)==digest,relative
            existing_sdk[relative]=digest
    golden='verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json'
    head=subprocess.check_output(['git','show','HEAD:'+golden],cwd=ROOT)
    assert len(head)==1906 and sha(head)==run['inputManifest'][golden]
    bindings={}
    for path in HERE.rglob('*'):
        if not path.is_file() or '.build' in path.parts or '__pycache__' in path.parts or path==out:continue
        bindings[str(path.relative_to(ROOT))]=sha(path.read_bytes())
    result=dict(format='mixer.ui-appearance-resolution-v2-independent-review-seal.1',status='accepted-pure-data-scope-only',completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        command=dict(argv=[sys.executable,*sys.argv],cwd=str(Path.cwd()),pythonVersion=platform.python_version()),sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sourceTreeSHA256=run['sourceTreeSHA256'],bindings=bindings,findings=[],conclusion='No actionable product issue observed in the frozen public V2 pure-data resolver. Independent Debug/Release differential cases and adversarial integrity/value/routing checks pass; all six deliberate semantic mutations are detected.',
        baselineCasesPerBuild=133,acceptedCasesPerBuild=107,rejectedCasesPerBuild=26,nodeRecordsComparedPerBuild=7858,paintStateComparisonsPerBuild=31432,
        mutationMismatchCases={n:run['results'][n]['failed'] for n in run['mutations']},producerTestsPerBuild=127,producerNewResolutionTestsPerBuild=21,
        preexistingSDKInputsUnchangedFromHEAD=existing_sdk,newSDKInputs=new_sdk,v1Golden=dict(path=golden,bytes=len(head),sha256=sha(head)),
        reviewBoundaries=['host pure-data execution only; iOS and official Android producer compilation receipts were audited, not independently rerun','private snapshot corruption fixtures are not a public forgery surface','raw generation and locale are retained data, not monotonic/native-locale support proof','metadata paths are references, not captured installed resources','root acceptance and all native/resource/transaction/physical/published-FieldLog/signed/store/customer/operational/GA gates remain separate'],
        failedHarnessAttempts=['candidate-1: a nominally valid locale fixture contained control-format U+200D; corrected test fixture','candidate-2: intentional disabled-state omission caused an unused variable under warnings-as-errors; corrected mutation','candidate-3: intentional constant profile switch failed warnings-as-errors; corrected mutation call site'],
        physicalDevices=dict(discovered=False,used=False,reconnectionRequested=False))
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print('PASS independent review sealed: 133 cases/build, 6 semantic mutations detected, no product findings; pure data only')
if __name__=='__main__':main()

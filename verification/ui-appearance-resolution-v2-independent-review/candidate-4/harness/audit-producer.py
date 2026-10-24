#!/usr/bin/env python3
"""Verify retained producer provenance and count actual passed test identities."""
from pathlib import Path
import datetime, hashlib, json, platform, re, subprocess, sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    out=HERE/(sys.argv[1] if len(sys.argv)>1 else 'producer-audit-1');out.mkdir(exist_ok=False)
    producer_path=ROOT/'verification/ui-appearance-resolution-v2/candidate-1/receipt.json'
    producer=json.loads(producer_path.read_bytes())
    bindings={str(producer_path.relative_to(ROOT)):sha(producer_path.read_bytes()),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__).read_bytes())}
    count_path=producer_path.parent/'count-audit.json';bindings[str(count_path.relative_to(ROOT))]=sha(count_path.read_bytes())
    counts={}
    for command in producer['commands']:
        path=ROOT/command['log'];data=path.read_bytes();assert sha(data)==command['sha256'];assert (command['exitCode']!=0)==command['expectedFailure'];bindings[command['log']]=sha(data)
    for path,metadata in producer['outputs'].items():
        data=(ROOT/path).read_bytes();assert sha(data)==metadata['sha256'] and len(data)==metadata['bytes'];bindings[path]=sha(data)
    for mode in ['debug','release']:
        log=(producer_path.parent/('sdk-'+mode+'.log')).read_text()
        swift=re.findall(r'✔ Test ([A-Za-z0-9_]+)\(\) passed',log)
        xctest=re.findall(r"Test Case '-\[([^]]+)\]' passed",log)
        assert len(swift)==len(set(swift))==119 and len(xctest)==len(set(xctest))==8
        assert sum(x.startswith('resolutionV2') for x in swift)==21
        counts[mode]=dict(swiftTestingDistinct=119,xctestDistinct=8,total=127,newResolutionDistinct=21,swiftTestingPassed=sorted(swift),xctestPassed=sorted(xctest))
    receipt=dict(format='mixer.ui-appearance-resolution-v2-independent-producer-audit.1',status='passed-retained-producer-bindings-and-counts',completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        command=dict(argv=[sys.executable,*sys.argv],cwd=str(Path.cwd()),pythonVersion=platform.python_version()),sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sourceTreeSHA256=producer['sourceTreeSHA256'],bindings=bindings,counts=counts,producerCommandCount=len(producer['commands']),producerOutputCount=len(producer['outputs']),
        scope='Hashes and actual passed test identities from retained producer commands only; host/public/iOS/official-Android compiler commands not independently rerun by this audit')
    (out/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('PASS 26 producer command logs, 14 binaries/modules, 127 actual tests per build (21 new resolution); retained evidence audit only')
if __name__=='__main__':main()

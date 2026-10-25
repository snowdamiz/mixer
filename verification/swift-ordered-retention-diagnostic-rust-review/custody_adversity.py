"""Small untrusted-input controls; never claims these are Rust-produced receipts."""
from pathlib import Path
import hashlib, json, os, sys, types
P=Path(__file__).resolve().parent;F=P.parent/'swift-ordered-retention-diagnostic-rust'
m=types.ModuleType('frozen_finite_custody');m.__file__=str(F/'capture_finite.py');exec(compile((F/'capture_finite.py').read_bytes(),m.__file__,'exec'),m.__dict__)
D=P/'custody-controls-attempt2';D.mkdir(exist_ok=False)
raw=(F/'streams/candidate-final-finite/ordered-5.bin').read_bytes();assert len(raw)==1280
assert int.from_bytes(raw[-512+72:-512+80],'little')==1
with __import__('tarfile').open(F/'raw-fixtures.tar.gz','r:gz') as t:
    names=[n for n in t.getnames() if n=='tmp-candidate/candidate-final-finite/ordered-5.original.txt'];assert len(names)==1;original=t.extractfile(names[0]).read()
results=[]
for label,offset in [('valid-cap',None),('bad-header-version',8),('bad-first-sequence',512),('bad-footer-count',len(raw)-512+16)]:
    case=D/label;case.mkdir();source=case/'input.bin';destination=case/'copy.bin'
    fd=os.open(source,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    initial=m.metadata(os.fstat(fd));data=bytearray(raw)
    if offset is not None:data[offset]^=1
    assert os.write(fd,data)==len(data);final=m.metadata(os.fstat(fd));os.close(fd)
    source.with_suffix('.initial.json').write_text(json.dumps(initial));source.with_suffix('.final.json').write_text(json.dumps(final));source.with_suffix('.original.txt').write_bytes(original)
    observation=m.capture(source,destination);sidecar=json.loads(destination.with_suffix('.sidecar.json').read_bytes())
    assert sidecar['status']=='truncated-prefix' and sidecar['failure']==0
    results.append({'case':label,'expectedIndependentClassification':'truncated-prefix' if offset is None else 'invalid','actualClassification':sidecar['status'],'failure':sidecar['failure'],'mutationByteOffset':offset,'sourceSHA256':hashlib.sha256(data).hexdigest(),'copySHA256':sidecar['copy_sha256'],'custodyMetadataActualForOwnedInput':True,'originalResultBytesCopiedFromFrozenRawFixture':True,'fullReplayAccepted':observation['fullReplayAccepted']})
(P/'custody-adversity.json').write_text(json.dumps({'scope':'untrusted framed input controls with actual owned-file metadata, not producer Rust executions','inputScriptSHA256':hashlib.sha256((F/'capture_finite.py').read_bytes()).hexdigest(),'cases':results,'falseValidMalformedCases':3,'boundedInputBytesEach':1280,'atMostTwoCopyDescriptors':True},indent=2,sort_keys=True)+'\n')
print(json.dumps(results,indent=2))

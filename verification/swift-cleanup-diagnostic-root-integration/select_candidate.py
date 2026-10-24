"""Bind a frozen independent review for exact root integration; no live writes."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()

def main():
    assert not(HERE/'review-selection.json').exists()
    bindings={}
    for directory,expected in [
        ('swift-cleanup-diagnostic','19d9040a10275bfc7968966853adc6541fb2b9855201c4448e226d4eeb0488a1'),
        ('swift-cleanup-diagnostic-review','2b17ffc4fcdb77c7d97bc784544a1d093e6d3945b43d4206c4d472be28bda7e1'),
    ]:
        base=ROOT/'verification'/directory;seal=base/'seal.json';assert sha(seal)==expected
        s=read(seal)
        assert {str(p.relative_to(base))for p in base.rglob('*')if p.is_file()and p!=seal}==set(s['files'])
        for name,digest in s['files'].items():
            path=base/name;assert not path.is_symlink()and sha(path)==digest,name
            bindings[str(path.relative_to(ROOT))]=digest
        for name,digest in s['externalBindings'].items():
            assert sha(ROOT/name)==digest,name;bindings[name]=digest
        bindings[str(seal.relative_to(ROOT))]=expected
    review=read(ROOT/'verification/swift-cleanup-diagnostic-review/receipt.json')
    assert review['recommendation']=='accept-exact-candidate-for-root-integration'and not review['findings']
    assert not review['liveIntegrated']and not review['gaAccepted']
    base=read(ROOT/'verification/swift-cleanup-diagnostic/baseline-source-manifest.json')
    candidate=read(ROOT/'verification/swift-cleanup-diagnostic/candidate-source-manifest.json')
    vm=ROOT/'vm';paths=[vm/'Cargo.toml',vm/'Cargo.lock']+[p for f in ['src','tests','include']for p in(vm/f).rglob('*')if p.is_file()]
    assert {str(p.relative_to(vm)):sha(p)for p in paths}==base
    changed=sorted(n for n in candidate if candidate[n]!=base.get(n));assert len(changed)==12 and set(base)==set(candidate)
    assert hashlib.sha256(enc(base)).hexdigest()=='7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329'
    assert hashlib.sha256(enc(candidate)).hexdigest()=='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c'
    result={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'rootSelectedForIntegration':True,'baselineSourceClosure':hashlib.sha256(enc(base)).hexdigest(),
            'reviewedSourceClosure':hashlib.sha256(enc(candidate)).hexdigest(),
            'changedRelativeFiles':changed,'bindings':dict(sorted(bindings.items())),
            'reviewVerifierCommand':[sys.executable,'-B','verification/swift-cleanup-diagnostic-review/verify.py'],
            'normalization':'None; apply exact reviewed bytes after producer/reviewer replay.',
            'scope':'Private contextual active-invocation attribution only; unchanged cursorless cleanup and first-failure authority. Full G08/Swift/native/public/GA remain pending.'}
    (HERE/'review-selection.json').write_bytes(enc(result))
    (HERE/'accepted-input-bindings.json').write_bytes(enc(dict(sorted(bindings.items()))))
    print(json.dumps({'selected':True,'bindings':len(bindings),'changedFiles':len(changed),'liveIntegrated':False}))

if __name__=='__main__':main()

"""Freeze only independent review ownership; immutable producer dependencies are reused."""
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
PRODUCER=ROOT/'verification/apple-focus-reference-runtime-v5'
HANDOFF=BASE/'handoff.json'
DOC=ROOT/'docs/apple-focus-reference-runtime-v5-independent-review.md'
EXPECTED='3d22fa59106d6bc6c585ed53d720b31f1bbe50f8e811cf528758b274918ac02b'
sha=lambda b:hashlib.sha256(b).hexdigest()
stable=lambda v:(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def row(p):
    info=p.lstat();assert stat.S_ISREG(info.st_mode) and not p.is_symlink()
    b=p.read_bytes();return {'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':len(b),'sha256':sha(b)}
def producer():
    assert sha((PRODUCER/'handoff.json').read_bytes())==EXPECTED
    h=json.loads((PRODUCER/'handoff.json').read_bytes())
    for n,v in h['members'].items():assert row(ROOT/n)==v,n
    assert sha(stable(h['members']))==h['memberTreeSHA256']
    return {'handoffSHA256':EXPECTED,'memberCount':len(h['members']),'memberTreeSHA256':h['memberTreeSHA256'],
            'packetSHA256':h['packetSHA256'],'hostReceiptSHA256':h['hostReceiptSHA256']}
def members():
    files=[p for p in BASE.rglob('*') if p.is_file() and p!=HANDOFF]+[DOC]
    assert not any(p.name.startswith('.scratch') for p in BASE.iterdir())
    return {str(p.relative_to(ROOT)):row(p) for p in sorted(files)}
def main(action):
    dependency=producer();observed=members()
    if action=='freeze':
        assert not HANDOFF.exists()
        result=json.loads((BASE/'attempt-2/independent-adversaries/receipt.json').read_bytes())
        replay=json.loads((BASE/'attempt-1/retained-replay-receipt.json').read_bytes())
        assert result['controlsPassed'] and result['testsRun']==19 and replay['passed']
        h={'schema':'mixer.apple-focus-reference-runtime-v5-independent-review-handoff.1',
           'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve()),'freeze'],
           'python':sys.version,'producer':dependency,'members':observed,'memberTreeSHA256':sha(stable(observed)),
           'conclusion':'rejected-for-fresh-native-selection','acceptedForFreshNativeSelection':False,
           'findings':result['findings'],'independentControls':{'passed':19,'run':19,'adapterAttempts':23,'actualSummaryCalls':18},
           'failedAuthoredHarnessAttemptPreserved':True,'retainedHistoricalMalformedFixture':{'passed':32,'run':33},
           'cleanup':{'ownedScratchAbsent':True,'producerClosureUnchanged':True,'nativeCommandsInvoked':0,'servicesStarted':0,'otherProjectsTouched':False},
           'nativeExecuted':False,'runtimeSelected':False,'gitMutationPerformed':False,'uiOrCapturePerformed':False,
           'physicalPhones':'disconnected-deferred','gaAccepted':False}
        HANDOFF.write_bytes(stable(h))
    else:
        h=json.loads(HANDOFF.read_bytes());assert h['producer']==dependency and h['members']==observed
        assert h['memberTreeSHA256']==sha(stable(observed))
    print(json.dumps({'verified':True,'handoffSHA256':sha(HANDOFF.read_bytes()),'members':len(observed),'conclusion':h['conclusion']},indent=2))

if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ['freeze','verify'];main(sys.argv[1])

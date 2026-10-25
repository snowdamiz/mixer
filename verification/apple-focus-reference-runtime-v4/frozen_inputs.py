"""Data-only verification of the frozen V3 producer and rejected independent review."""
import hashlib
import json
from pathlib import Path
import stat

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
V3=ROOT/'verification/apple-focus-reference-runtime-v3'
V3_REVIEW=ROOT/'verification/apple-focus-reference-runtime-v3-independent-review'
V3_HANDOFF='f50006ea6fbe274eac4a78c214a33da4b77c4249b0ef2e8a19f1e0c4200e18f1'
V3_REVIEW_HANDOFF='70f56f2e9495cf6ca18c0298fdf83300849b484298b62830a4facf744c6eebe1'
V3_PACKET='89e4b9b819bacc7ba69aee1fa2344245bf2eb26a3b8ed72a33a169f574f3fd60'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
stable=lambda value:(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()

def row(path,official_alias=False):
    assert path.resolve()==path or official_alias, 'Redirected frozen input: '+str(path)
    info=path.lstat() if not official_alias else path.resolve().lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink==1,str(path)
    raw=path.read_bytes()
    return {'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':len(raw),'sha256':sha(raw)}

def verify():
    rows={}
    for directory,expected in [(V3,V3_HANDOFF),(V3_REVIEW,V3_REVIEW_HANDOFF)]:
        path=directory/'handoff.json';assert row(path)['sha256']==expected,str(path)
        handoff=json.loads(path.read_bytes());assert sha(stable(handoff['members']))==handoff['memberTreeSHA256']
        for name,expected_row in handoff['members'].items():
            assert 'hosted' not in name and 'catalog' not in name and 'authority-driver' not in name,name
            observed=row(ROOT/name);assert observed==expected_row,name;rows[name]=observed
        rows[str(path.relative_to(ROOT))]=row(path)
    assert row(V3/'packet.json')['sha256']==V3_PACKET
    review=json.loads((V3_REVIEW/'handoff.json').read_bytes())
    assert review['producerHandoffSHA256']==V3_HANDOFF and review['packetSHA256']==V3_PACKET
    assert review['independentControls']=={'run':37,'passed':34,'failed':3,'errors':0,'skipped':0}
    for name,expected in json.loads((V3/'input-lock.json').read_bytes()).items():
        assert 'hosted' not in name and 'catalog' not in name and 'authority-driver' not in name,name
        path=Path(name) if name.startswith('/') else ROOT/name
        observed=row(path,name.endswith('/SDKSettings.json'));assert observed==expected,name;rows[name]=observed
    return rows

if __name__=='__main__':
    rows=verify();print(json.dumps({'members':len(rows),'treeSHA256':sha(stable(rows)),'nativeExecuted':False},sort_keys=True))

#!/usr/bin/env python3
"""Read-only admitted closure verification and exact owned-copy acquisition."""
from pathlib import Path
import hashlib,json,tarfile,sys,datetime

OWN=Path(__file__).resolve().parent
BASE=OWN.parent
ROOT=BASE.parents[1]
PRODUCER=ROOT/'verification/swift-ordered-retention-analyzer-envelope-correction'
PIN='4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1'
ARCHIVE='ca52e81504a95461806bec51ffb495bb57ec27456a3f7b266364cc2fa92c50e2'
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def protected():
    for sub,pin,count in [('', '582d0ab43c078caeb9142650390345eee3076c6114c35d217f1964f460e324da',39),('selected-contract-preparation','d15e11450eeb16793cd9647fb7fb4965551d2c5a66e98a2d0130a50e2794c72e',13)]:
        b=(BASE/sub/'seal.json').read_bytes();assert sha(b)==pin
        s=json.loads(b);assert len(s['members'])==count
        for m in s['members']:
            b=(ROOT/m['path']).read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256'],m['path']
def verify_producer():
    raw=(PRODUCER/'seal.json').read_bytes();assert sha(raw)==PIN
    s=json.loads(raw);assert len(s['members'])==306
    for m in s['members']:
        path=ROOT/m['path'];assert path.is_relative_to(PRODUCER)
        b=path.read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256'],m['path']
    return s
if __name__=='__main__':
    protected();s=verify_producer()
    for rel in ['seal.json','final-receipt.json','implementation-delta.json','source-test-model-manifest.json','commands/selected-run-1/receipt.json']:
        out=OWN/'admitted'/rel;out.parent.mkdir(parents=True,exist_ok=True);assert not out.exists();out.write_bytes((PRODUCER/rel).read_bytes())
    for rel in ['selected-correction-preflight.json','correction-numeric-contract-selection.json']:
        src=ROOT/'verification/swift-ordered-retention-analyzer-envelope-root-review'/rel
        out=OWN/'admitted'/rel;out.write_bytes(src.read_bytes())
    archive=PRODUCER/'selected-source-test-model.tar.gz';assert sha(archive.read_bytes())==ARCHIVE
    dest=OWN/'archive-source';dest.mkdir()
    with tarfile.open(archive,'r:gz') as t:
        entries=t.getmembers();assert len(entries)==86
        for e in entries:
            assert e.isfile() and not Path(e.name).is_absolute() and '..' not in Path(e.name).parts
            out=dest/e.name;out.parent.mkdir(parents=True,exist_ok=True)
            b=t.extractfile(e).read();assert len(b)==e.size;out.write_bytes(b)
    assert sha((dest/'src/envelope.rs').read_bytes())=='7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1'
    assert sha((dest/'src/analyzer.rs').read_bytes())=='1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b'
    selected=json.loads((OWN/'admitted/correction-numeric-contract-selection.json').read_bytes());assert selected['selected']['leaf']==425
    run=json.loads((OWN/'admitted/commands/selected-run-1/receipt.json').read_bytes())
    streams=0
    for c in run['commands']:
        for stream in ['stdout','stderr']:
            p=PRODUCER/'commands/selected-run-1'/c[stream]
            assert sha(p.read_bytes())==c[stream+'_sha256'];streams+=1
    dump(OWN/'acquisition.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).relative_to(ROOT))],'python':sys.version,'producer_seal_sha256':PIN,'members_verified':len(s['members']),'bytes_verified':sum(m['bytes'] for m in s['members']),'archive_sha256':ARCHIVE,'archive_members':86,'producer_stream_bindings_verified':streams,'protected_members_verified':52,'producer_collector_executed':False,'scope':'admitted custody and exact source acquisition only; no behavior verdict'})
    print(json.dumps({'producer_members':306,'archive_members':86,'producer_streams':streams,'protected_members':52,'source_acquired':True}))

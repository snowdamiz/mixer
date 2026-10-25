"""Record static archive comparisons and preserve exact reviewed source snapshots."""
import datetime
import json
from pathlib import Path
import tarfile
import sys
from bind_inputs import OWNED, row, sha, stable

meta=json.loads((OWNED/'input-bindings.json').read_bytes());repo=Path(meta['scratchRepo'])
def archive(name):
    with tarfile.open(repo/name,'r:gz') as handle:
        return {m.name:handle.extractfile(m).read() for m in handle.getmembers() if m.isfile()}
old=archive('verification/apple-focus-reference-runtime-v3/runtime-sources.tar.gz')
new=archive('verification/apple-focus-reference-runtime-v4/runtime-sources.tar.gz')
assert set(old)==set(new) and len(new)==31
changed={name:{'v3SHA256':sha(old[name]),'v4SHA256':sha(new[name])} for name in sorted(new) if new[name]!=old[name]}
assert set(changed)=={'selected/importer.py','selected/join_support.py'}
unchanged={name:sha(new[name]) for name in sorted(new) if new[name]==old[name]}
base=repo/'verification/apple-focus-reference-runtime-v4';snapshot=OWNED/'frozen-producer';snapshot.mkdir()
names=['handoff.json','packet.json','host-attempt-2/receipt.json','runtime-source-manifest.json','runtime-sources.tar.gz','v3-to-v4-repair.patch','namespace-adaptation.patch']
names+=list(json.loads((base/'packet.json').read_bytes())['ownedSources'])
for name in names:
    src=base/name;dst=snapshot/name;dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(src.read_bytes());dst.chmod(src.stat().st_mode & 0o777)
    assert row(dst)==row(src)
result={'schema':'mixer.apple-focus-reference-runtime-v4-independent-static-audit.1',
        'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,
        'comparedSelectedMembers':31,'changedSelectedMembers':changed,'unchangedSelectedMembers':unchanged,
        'unchangedOriginalContracts':['all original oracle sources','original reference classifier','actual Bridge','actual Session','TransactionStore','observer V2','composition.py','orchestration.py','original timings and action budget','compiled source and products'],
        'basis':'29/31 V3 selected source files identical; only importer and appended join_support adapter differ. Accepted-source and product archive trees independently bound in input-bindings.json.',
        'rootTimeFinding':{'producerLines':['importer.py:62-66','importer.py:134-138','importer.py:198-204'],
                           'selectedAtUTC':'2026-10-25T02:00:01.000000001+00:00','exactRootNS':1792893601000000001,
                           'actualDatetimeNS':1792893601000000000,'summaryStartNS':1792893601000000000,'summaryPredatesTrueRootByNS':1},
        'snapshotMembers':{str(p.relative_to(snapshot)):row(p) for p in sorted(snapshot.rglob('*')) if p.is_file()},
        'nativeExecuted':False,'compilerInvoked':False}
(OWNED/'static-audit.json').write_bytes(stable(result))
print(json.dumps({'changedSelectedMembers':list(changed),'unchangedSelectedMembers':len(unchanged),'snapshotMembers':len(result['snapshotMembers'])},sort_keys=True))

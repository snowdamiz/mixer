"""Verify rejected V4 identities before freezing an explicitly closed V5 input archive.

This action reads frozen files and tool executables as data only. Supplemental
Settings bytes come exclusively from the separately bound review archive.
"""
import datetime
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
V4 = ROOT / 'verification/apple-focus-reference-runtime-v4'
REVIEW = ROOT / 'verification/apple-focus-reference-runtime-v4-independent-review'
EXPECTED = {
    str((V4/'handoff.json').relative_to(ROOT)): '79a8a2d5070b1f9466831089be0f2f89d1e67d3785c707879414ea2edac9ca07',
    str((V4/'packet.json').relative_to(ROOT)): '4622a27a5e4c9dc9651b3eee6022e850dab1f55db3b48ac8f0daa4921b80e77a',
    str((REVIEW/'handoff.json').relative_to(ROOT)): '93c6505ba122b532aafe3fdcd65a3a09273d046fafc37d633b9ec860dd503233',
}
sha = lambda raw: hashlib.sha256(raw).hexdigest()
stable = lambda value: (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()

def row(path, alias=False):
    assert path.resolve() == path or alias, path
    info = path.resolve().stat() if alias else path.lstat()
    assert stat.S_ISREG(info.st_mode), path
    raw = path.read_bytes()
    return {'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':len(raw),'sha256':sha(raw)}

def storage(name):
    return 'external/'+name.lstrip('/') if name.startswith('/') else name

def archive(path, payloads, rows):
    with path.open('xb') as stream, gzip.GzipFile(fileobj=stream, mode='wb', mtime=0, filename='') as zipped, tarfile.open(fileobj=zipped, mode='w') as out:
        for name in sorted(payloads):
            raw = payloads[name]; member = tarfile.TarInfo(storage(name))
            member.size=len(raw); member.mode=rows[name]['mode']; member.mtime=0
            out.addfile(member, io.BytesIO(raw))

def main():
    assert not (BASE/'input-bindings.json').exists(), 'Preserve prior binding'
    for name, expected in EXPECTED.items(): assert row(ROOT/name)['sha256']==expected, name
    producer=json.loads((V4/'handoff.json').read_bytes())
    review=json.loads((REVIEW/'handoff.json').read_bytes())
    bindings=json.loads((REVIEW/'input-bindings.json').read_bytes())
    supplement=json.loads((REVIEW/'supplemental-inputs.json').read_bytes())
    assert len(producer['members'])==535 and len(review['members'])==959
    assert review['independentControls']=={'run':36,'passed':30,'failed':6,'errors':0,'skipped':0}
    assert sha(stable(producer['members']))==producer['memberTreeSHA256']
    assert sha(stable(review['members']))==review['memberTreeSHA256']
    assert sha(stable(bindings['bindings']))==bindings['bindingTreeSHA256']
    dependencies=json.loads((V4/'input-lock.json').read_bytes())
    assert len(dependencies)==621 and sha(stable(dependencies))=='30e511b5622426f8288595da7613e829e50eba34046d8351186a7d415067cca4'
    rows={};payloads={}
    def add(name, expected):
        assert not any(word in name.lower() for word in ('hosted','catalog','authority-driver','worker-transport')), name
        path=Path(name) if name.startswith('/') else ROOT/name
        observed=row(path, name.endswith('/SDKSettings.json'))
        assert observed==expected, name
        assert name not in rows or rows[name]==observed, name
        rows[name]=observed;payloads[name]=path.read_bytes()
    for collection in [producer['members'], dependencies, bindings['bindings'], review['members']]:
        for name, expected in collection.items():add(name,expected)
    for name in EXPECTED:add(name,row(ROOT/name))
    assert supplement['count']==276 and supplement['wasBoundByV4Producer'] is False
    assert sha(stable(supplement['members']))=='c5c19c9aa0520f92f904f698823a90994e89166f3693df07ced052e9e38aeb68'
    supplemental_archive=REVIEW/'supplemental-settings-journals.tar.gz'
    assert row(supplemental_archive)==supplement['archive']
    with tarfile.open(supplemental_archive,'r:gz') as tar:
        members=tar.getmembers()
        assert {m.name for m in members}==set(supplement['members']) and len(members)==276
        for member in members:
            name=member.name;assert member.isfile() and not member.issym() and not member.islnk()
            raw=tar.extractfile(member).read();expected=supplement['members'][name]
            assert {'kind':'file','mode':member.mode,'bytes':len(raw),'sha256':sha(raw)}==expected
            assert name not in rows, name
            rows[name]=expected;payloads[name]=raw
    assert all(name in rows for name in supplement['members'])
    path=BASE/'frozen-inputs.tar.gz';archive(path,payloads,rows)
    result={'schema':'mixer.apple-focus-reference-runtime-v5-input-bindings.1',
            'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'command':[sys.executable,'-B',str(Path(__file__).resolve())],
            'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),'hostUname':list(os.uname()),
            'expectedIdentities':EXPECTED,'producerMembersVerified':535,'frozenDependenciesVerified':621,'reviewMembersVerified':959,
            'retainedReviewControls':review['independentControls'],'retainedExactClosureReplay':review['exactClosureReplay'],
            'retainedSupplementalReplay':review['supplementalReplay'],
            'supplementalSettings':{'members':supplement['members'],'count':276,'bytes':sum(r['bytes'] for r in supplement['members'].values()),
                'treeSHA256':supplement['memberTreeSHA256'],'sourceManifest':row(REVIEW/'supplemental-inputs.json'),
                'sourceArchive':row(supplemental_archive),'wasBoundByV4Producer':False},
            'bindings':rows,'bindingTreeSHA256':sha(stable(rows)),'storage':{name:storage(name) for name in rows},
            'archive':row(path),'nativeExecuted':False,'excludedHostedLanesReadImportedExecuted':False}
    (BASE/'input-bindings.json').write_bytes(stable(result))
    print(json.dumps({'files':len(rows),'bytes':sum(r['bytes'] for r in rows.values()),'treeSHA256':result['bindingTreeSHA256'],'archive':result['archive'],'supplementalSettingsFiles':276},sort_keys=True))

if __name__=='__main__':main()

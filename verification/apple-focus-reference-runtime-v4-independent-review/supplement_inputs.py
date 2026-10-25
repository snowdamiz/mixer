"""Bind the precise historical Settings journal glob missing from the V4 closure."""
import datetime
import io
import json
from pathlib import Path
import tarfile
import sys
import stat
from bind_inputs import OWNED, ROOT, row, sha, stable

meta=json.loads((OWNED/'input-bindings.json').read_bytes());repo=Path(meta['scratchRepo'])
folder=ROOT/'verification/apple-focus-diagnostic-runtime-v1/runtime/captures'
paths=sorted(folder.glob('0000-settings-*.json'))
assert paths and all(str(p.relative_to(ROOT)) not in meta['bindings'] for p in paths)
rows={};identities={}
for p in paths:
    info=p.lstat();assert p.resolve()==p and stat.S_ISREG(info.st_mode)
    raw=p.read_bytes();name=str(p.relative_to(ROOT))
    rows[name]={'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':len(raw),'sha256':sha(raw)}
    identities[name]={'device':info.st_dev,'inode':info.st_ino,'links':info.st_nlink}
archive=OWNED/'supplemental-settings-journals.tar.gz'
assert not archive.exists()
with tarfile.open(archive,'w:gz') as out:
    for name,expected in rows.items():
        raw=(ROOT/name).read_bytes();dst=repo/name;dst.parent.mkdir(parents=True,exist_ok=True)
        assert not dst.exists();dst.write_bytes(raw);dst.chmod(expected['mode']);assert row(dst)==expected
        member=tarfile.TarInfo(name);member.size=len(raw);member.mode=expected['mode'];member.mtime=0
        out.addfile(member,io.BytesIO(raw))
result={'schema':'mixer.apple-focus-reference-runtime-v4-independent-supplemental-inputs.1',
        'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__).resolve())],
        'python':sys.version,'members':rows,'memberTreeSHA256':sha(stable(rows)),'count':len(rows),
        'archive':row(archive),'sourceIdentities':identities,'source':'Historical read-only Settings journals explicitly referenced by frozen host composition programs',
        'wasBoundByV4Producer':False,'copiedBeforeSupplementalReplay':True,'nativeEvidenceCredit':False}
(OWNED/'supplemental-inputs.json').write_bytes(stable(result));print(json.dumps({k:v for k,v in result.items() if k not in ('members','sourceIdentities')},sort_keys=True))

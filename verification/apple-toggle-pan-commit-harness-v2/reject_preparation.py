"""Preserve a rejected seal and every named byte before allowing preparation edits."""
import datetime
import hashlib
import io
import json
import pathlib
import sys
import tarfile

BASE=pathlib.Path(__file__).resolve().parent;ROOT=BASE.parents[1]
assert len(sys.argv)==2 and sys.argv[1].strip(),'Supply the concrete rejection reason'
seal=BASE/'packet-seal.json';raw=seal.read_bytes();value=json.loads(raw)
sha=lambda b:hashlib.sha256(b).hexdigest()
number=1
while (BASE/('rejected-preparation-'+str(number))).exists():number+=1
destination=BASE/('rejected-preparation-'+str(number));destination.mkdir()
archive_path=destination/'packet.tar.gz'
with tarfile.open(archive_path,'x:gz') as archive:
    for name,digest in {**value['files'],str(seal.relative_to(ROOT)):sha(raw)}.items():
        relative=pathlib.PurePosixPath(name)
        assert not relative.is_absolute() and '..' not in relative.parts and str(relative)==name
        path=ROOT/name;assert path.is_file() and not path.is_symlink()
        data=path.read_bytes();assert sha(data)==digest,'Changed before rejection archive: '+name
        member=tarfile.TarInfo(name);member.size=len(data);member.mode=0o644;archive.addfile(member,io.BytesIO(data))
receipt={'schema':'mixer.apple-toggle.pan-commit-harness-v2-rejected-preparation.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'reason':sys.argv[1],'priorSealSHA256':sha(raw),'archiveSHA256':sha(archive_path.read_bytes()),'archivedFiles':len(value['files'])+1,
         'nativeExecutedByThisAction':False,'status':'rejected-preparation-preserved-before-edit'}
(destination/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert seal.read_bytes()==raw
seal.unlink()
print(json.dumps(receipt,sort_keys=True))

#!/usr/bin/env python3
"""Verify and archive owned synthetic scratch before deleting it."""
import hashlib
import io
import json
import pathlib
import shutil
import stat
import tarfile
BASE=pathlib.Path(__file__).resolve().parent
SCRATCH=BASE/'.scratch'
assert not (BASE/'packet-seal.json').exists()
manifest={}
for path in sorted(SCRATCH.rglob('*')):
    assert not path.is_symlink() and (path.is_dir() or path.is_file())
    name=str(path.relative_to(SCRATCH))
    manifest[name]=dict(kind='directory' if path.is_dir() else 'file',mode=stat.S_IMODE(path.stat().st_mode))
    if path.is_file():manifest[name].update(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
attempt=len(list(BASE.glob('host-evidence*.tar.gz')))+1
label='host-evidence' if attempt==1 else 'host-evidence-'+str(attempt)
archive=BASE/(label+'.tar.gz')
assert not archive.exists()
with tarfile.open(archive,'w:gz') as stream:
    for name,entry in manifest.items():
        path=SCRATCH/name
        item=tarfile.TarInfo(name);item.mode=entry['mode']
        if entry['kind']=='directory':item.type=tarfile.DIRTYPE;stream.addfile(item)
        else:
            data=path.read_bytes();item.size=len(data);stream.addfile(item,io.BytesIO(data))
seen=set()
with tarfile.open(archive,'r:gz') as stream:
    for item in stream:
        assert item.name in manifest and item.name not in seen;seen.add(item.name)
        entry=manifest[item.name];assert item.mode==entry['mode']
        if entry['kind']=='directory':assert item.isdir()
        else:
            data=stream.extractfile(item).read();assert item.isfile() and len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
assert seen==set(manifest)
(BASE/(label+'-manifest.json')).write_text(json.dumps(dict(schema=1,syntheticHostOnly=True,archiveSHA256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=manifest,verifiedBeforeCleanup=True),sort_keys=True,indent=2)+'\n')
shutil.rmtree(SCRATCH)
(BASE/'cleanup.json').write_text(json.dumps(dict(schema=1,syntheticScratchArchivedVerifiedAndRemoved=not SCRATCH.exists(),nativeInstancesCreated=0,nativeInstancesQueried=False,nativeInstancesRemoved=0,otherProjectDataTouched=False,physicalPhones='disconnected-deferred'),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(archivedEntries=len(manifest),scratchAbsent=not SCRATCH.exists(),nativeInstancesTouched=False)))

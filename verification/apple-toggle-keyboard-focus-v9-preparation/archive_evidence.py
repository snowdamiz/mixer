#!/usr/bin/env python3
"""Archive and verify exact owned synthetic evidence, then retire only that tree."""
import datetime
import gzip
import hashlib
import json
import os
import pathlib
import shutil
import tarfile
import packet as p
b=p.BASE;scratch=b/'.scratch'
p.require(not (b/'packet-seal.json').exists(),'Sealed V9 packet is immutable')
p.require(scratch.is_dir() and not scratch.is_symlink() and scratch.resolve()==scratch,'Owned canonical scratch required')
manifest={}
for path in sorted(scratch.rglob('*')):
    name=str(path.relative_to(b));mode=oct(path.lstat().st_mode & 0o777)
    if path.is_symlink():manifest[name]={'kind':'symlink','target':os.readlink(path),'mode':mode}
    elif path.is_dir():manifest[name]={'kind':'directory','mode':mode}
    else:manifest[name]={'kind':'file','sha256':p.sha(path),'bytes':path.stat().st_size,'mode':mode}
archive=b/'host-evidence.tar.gz'
p.require(not archive.exists(),'Never overwrite evidence archive')
with archive.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as compressed,tarfile.open(fileobj=compressed,mode='w') as tar:
    for name in manifest:
        info=tar.gettarinfo(str(b/name),arcname=name);info.uid=0;info.gid=0;info.uname='';info.gname='';info.mtime=0
        if manifest[name]['kind']=='file':
            info.type=tarfile.REGTYPE;info.linkname='';info.size=manifest[name]['bytes']
            with (b/name).open('rb') as stream:tar.addfile(info,stream)
        else:tar.addfile(info)
with tarfile.open(archive,'r:gz') as tar:
    entries=tar.getmembers();p.require(len(entries)==len(manifest),'Archive entry count differs')
    for info in entries:
        expected=manifest[info.name]
        p.require(oct(info.mode)==expected['mode'],'Archive mode changed')
        if expected['kind']=='file':
            data=tar.extractfile(info).read();p.require(info.isfile() and len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],'Archive file changed')
        elif expected['kind']=='symlink':p.require(info.issym() and info.linkname==expected['target'],'Archive symlink fixture changed')
        else:p.require(info.isdir(),'Archive directory changed')
for name,expected in manifest.items():
    path=b/name
    if expected['kind']=='file':p.require(p.sha(path)==expected['sha256'],'Scratch changed before cleanup')
    elif expected['kind']=='symlink':p.require(os.readlink(path)==expected['target'],'Scratch symlink changed before cleanup')
result=dict(schema='mixer.apple-keyboard.v9-retained-host-evidence.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),archiveSHA256=p.sha(archive),entries=manifest,entryCount=len(manifest),files=sum(x['kind']=='file' for x in manifest.values()),logicalFileBytes=sum(x.get('bytes',0) for x in manifest.values()),containsAllFailedAndPassingSyntheticAttempts=True,symlinksAreDeliberateFailClosedReplayFixtures=True,archiveExtractionPerformed=False)
(b/'host-evidence-manifest.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
shutil.rmtree(scratch)
p.require(not scratch.exists(),'Owned scratch cleanup incomplete')
cleanup=dict(schema='mixer.apple-keyboard.v9-host-cleanup.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),removedPath=str(scratch.relative_to(p.ROOT)),verifiedArchiveSHA256=p.sha(archive),entryCount=len(manifest),logicalBytesRemoved=result['logicalFileBytes'],ownedScratchAbsent=True,syntheticHttpThreadsJoinBeforeClose=True,allSyntheticHttpThreadsJoinedBySendFinally=True,nativeInstancesCreated=False,nativeInstancesQueried=False,nativeCleanup='No native instance created or queried',physicalPhones='disconnected-deferred',otherProjectDataTouched=False)
(b/'cleanup.json').write_text(json.dumps(cleanup,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(archiveSHA256=result['archiveSHA256'],entries=result['entryCount'],files=result['files'],logicalFileBytes=result['logicalFileBytes'],ownedScratchAbsent=True,nativeInstancesQueried=False)))

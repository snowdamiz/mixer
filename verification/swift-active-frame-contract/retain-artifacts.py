#!/usr/bin/env python3
"""Preserve qualifying metadata/ABI binaries independently of disposable targets."""
from pathlib import Path
import hashlib, json, sys, tarfile
HERE=Path(__file__).resolve().parent
folder=Path(sys.argv[1]).resolve()
r=json.loads((folder/'receipt.json').read_text())
commands={x['name']:x for x in r['commands']}
items=[]
for entry in r['layouts']:
    label=entry['label']; run=commands[label+'-run']; path=Path(run['argv'][0])
    items.append(dict(id=label,kind='metadata',archiveMember='artifacts/metadata/'+label+'.bin',originalPath=str(path),sha256=entry['binarySHA256'],bytes=path.stat().st_size,sourceTreeSHA256=run['sourceTreeSHA256'],buildCommand=label+'-build',runCommand=label+'-run',listCommand=label+'-list' if 'unit' in label else None))
for entry in r['abi']:
    label=entry['label']; command=commands[label+'-abi-exports']; path=Path(command['argv'][-1])
    items.append(dict(id=label,kind='abi-dylib',archiveMember='artifacts/abi/'+label+'.dylib',originalPath=str(path),sha256=entry['binarySHA256'],bytes=path.stat().st_size,sourceTreeSHA256=command['sourceTreeSHA256'],buildCommand=label+'-abi-build',exportsCommand=label+'-abi-exports'))
archive=folder/'qualifying-artifacts.tar.gz'
with tarfile.open(archive,'w:gz') as t:
    for item in items:
        path=Path(item['originalPath'])
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        t.add(path,arcname=item['archiveMember'],recursive=False)
manifest=dict(schema=1,status='retained-qualifying-host-metadata-and-abi-artifacts',archive=archive.name,archiveSHA256=hashlib.sha256(archive.read_bytes()).hexdigest(),archiveBytes=archive.stat().st_size,artifacts=items,nativeRuntime=False,frameExecution=False)
(folder/'qualifying-artifacts.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(artifacts=len(items),uncompressedBytes=sum(x['bytes'] for x in items),archiveBytes=manifest['archiveBytes'],archiveSHA256=manifest['archiveSHA256']),sort_keys=True))

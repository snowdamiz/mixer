#!/usr/bin/env python3
"""Seal existing compile + pure-host output without launching any generated program."""
import hashlib
import json
import pathlib
import sys
import tarfile

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def read(name): return json.loads((OUT/name).read_text())
def write(name,value): (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
lock = read('source-lock.json')
assert all(sha(ROOT/name) == value for name,value in lock['sha256'].items()), 'source drift'
manifest = read('artifact-members.json')
archive = OUT/'compiled-artifacts.tar.gz'
with tarfile.open(archive,'r:gz') as package:
    assert {member.name for member in package.getmembers()} == set(manifest)
    for member in package.getmembers():
        assert member.isfile() and not member.issym()
        data = package.extractfile(member).read()
        assert len(data) == manifest[member.name]['bytes']
        assert hashlib.sha256(data).hexdigest() == manifest[member.name]['sha256']
write('artifact-manifest.json',dict(archive=archive.name,sha256=sha(archive),files=manifest))
pure = read('host-pure-result.json')
assert pure['passed'] and pure['sourceClosureSHA256'] == lock['sourceClosureSHA256']
assert not pure['nativeExecuted'] and not pure['guiExecuted']
result = read('result.json')
result.update(hostPureExecuted=True,generatedProgramsExecuted=True,
              scope='iOS product/harness compiled only; macOS production CoreGraphics helper executed without UIKit/app/window/simulator/GUI/capture',
              regressionDefinitions='8 pure arithmetic outcomes passed; 2 detached UIKit outcomes compiled but not executed',
              hostPureResult='host-pure-result.json')
write('result.json',result)
with tarfile.open(OUT/'source-inputs.tar.gz','w:gz') as package:
    for name in lock['sha256']: package.add(ROOT/name,arcname=name,recursive=False)
write('source-archive.json',dict(archive='source-inputs.tar.gz',sha256=sha(OUT/'source-inputs.tar.gz'),files=lock['sha256']))
write('integrity.json',dict(sourceCount=len(lock['sha256']),sourceClosureSHA256=lock['sourceClosureSHA256'],
      sourceLockSHA256=sha(OUT/'source-lock.json'),commandsSHA256=sha(OUT/'commands.json'),
      resultSHA256=sha(OUT/'result.json'),hostPureResultSHA256=sha(OUT/'host-pure-result.json'),
      liveSourceClosureMatched=True,artifactArchiveMatched=True,
      artifactArchiveSHA256=sha(archive),sourceArchiveSHA256=sha(OUT/'source-inputs.tar.gz'),
      sealCommand=[sys.executable,str(pathlib.Path(__file__).resolve())],
      toolingSHA256={name:sha(OUT/name) for name in ['compile.py','run-pure-host.py','seal.py']},
      scope='Source/binary integrity + retained eight pure macOS math results only; current native/UI/style qualification false'))
print(json.dumps(dict(sourceCount=len(lock['sha256']),sourceClosureSHA256=lock['sourceClosureSHA256'],
                      hostPurePassed=8,nativeExecuted=False)))

#!/usr/bin/env python3
"""Audit actual normal and duplicate-loading paths without native operations."""
import hashlib
import json
import pathlib
import sys
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[1]
source=set();reads=set();active=True

def audit(event,args):
    if event in ['subprocess.Popen','os.system']:raise RuntimeError('Process/native operation forbidden during import inventory')
    if not active:return
    if event=='exec':
        path=pathlib.Path(args[0].co_filename)
        if path.is_absolute() and path.is_relative_to(ROOT):source.add(path)
    if event=='open' and isinstance(args[0],str):
        path=pathlib.Path(args[0])
        mode=args[1]
        if path.is_absolute() and path.is_relative_to(ROOT) and isinstance(mode,str) and 'r' in mode:reads.add(path)
sys.addaudithook(audit)
import composition as c
for index in range(2):c.load('inventory_duplicate_'+str(index),c.KEYBOARD/'run.py')
c.compose()
active=False
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
result=dict(schema=1,sourceFiles={str(p.relative_to(ROOT)):sha(p) for p in sorted(source) if p.is_file()},
    dataFiles={str(p.relative_to(ROOT)):sha(p) for p in sorted(reads-source) if p.is_file() and p.suffix not in ['.py','.pyc']},
    allRuntimeImportsPacketLocal=all(p.is_relative_to(BASE) for p in source),
    normalAndDuplicateLoadingExercised=True,nativeInstancesQueried=False,nativeExecuted=False)
assert result['allRuntimeImportsPacketLocal']
assert len(result['dataFiles'])==4,result['dataFiles']
(BASE/'runtime-import-bindings.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(sourceFiles=len(result['sourceFiles']),dataFiles=len(result['dataFiles']),nativeExecuted=False)))

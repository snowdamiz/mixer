#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,tarfile,gzip,os,sys
STAGE=sys.argv[1]+"-" if len(sys.argv)>1 else ""
from run import run,SCRATCH,HERE,b
import inventory
if '--archive-only' not in sys.argv:
 for feature,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for release in [False,True]:
   p=run(STAGE+'check-'+feature+('-release' if release else '-debug'),['cargo','check','--lib','--locked','--offline',*flags,*(['--release'] if release else [])],SCRATCH/'candidate');assert p.returncode==0
 for name,args in [('rustc',['rustc','-vV']),('cargo',['cargo','-V']),('rustfmt',['rustfmt','--version']),('python',['python3','--version']),('host',['uname','-a']),('git',['git','rev-parse','HEAD'])]:
  p=run(STAGE+'tool-'+name,args);assert p.returncode==0
 # Validate recorded actual compiler inventories after the final accounting
 # declarations are present. The metadata-only copies are never used for MIR.
 p=subprocess.run(['python3','-B',str(HERE/'source_probe.py'),STAGE+'final-accounted'],cwd=HERE.parents[1]);assert p.returncode==0
 schema=json.loads((HERE/'inventory-schema.json').read_text());audit=[]
 for config in ['production','unit']:
  rows,defs,captures=inventory.canonical(HERE/(config+'.mir'),config)
  expected=[r for r in schema if r['config']==config]
  keys=['envelope','window','field','rustType','binding','sourceNames','position','config','kind','mirType']
  identity=lambda r:{k:r[k] for k in keys}
  assert list(map(identity,rows))==list(map(identity,expected)),(config,len(rows),len(expected))
  audit.append(dict(config=config,canonicalFunctions=len(defs),positiveCanonicalFields=len(rows),status='exact-final-accounted-source-roles',sourceClosure=b.digest(b.manifest(SCRATCH/'candidate')),mirSHA256=b.sha(HERE/(config+'.mir')),definitions=defs))
 (HERE/'canonical-audit.json').write_bytes(b.enc(audit))
for label in ['baseline','candidate','metadata-baseline','metadata-candidate'+('-'+STAGE[:-1] if STAGE else '')]:
 vm=SCRATCH/label;m=b.manifest(vm);(HERE/(label+'-source-manifest.json')).write_bytes(b.enc(m))
 with tarfile.open(HERE/(label+'-source.tar.gz'),'w:gz') as t:
  for path in m:t.add(vm/path,arcname='vm/'+path,recursive=False)
# Bind actual metadata executables used by Cargo before owned scratch cleanup.
binaries=[]
for directory in sorted((HERE/'commands').glob('layout-*')):
 if STAGE and directory.name.startswith('layout-candidate-'):continue
 rec=json.loads((directory/'receipt.json').read_text());target=Path(rec['environment']['CARGO_TARGET_DIR']);profile='release' if 'release' in directory.name else 'debug'
 paths=list((target/profile/'deps').glob('mixer_vm-*')) if directory.name.endswith('-unit') else [target/profile/'memory_contract_layout']
 paths=[p for p in paths if p.is_file() and p.suffix=='' and os.access(p,os.X_OK)]
 assert len(paths)==1,(directory,paths)
 binaries.append(dict(command=directory.name,path=str(paths[0]),sha256=b.sha(paths[0]),bytes=paths[0].stat().st_size,sourceTreeSHA256=rec['sourceTreeSHA256'],scope='metadata-only program/test; no guest memory method invoked'))
assert len(binaries)==16,len(binaries)
(HERE/'executable-manifest.json').write_bytes(b.enc(binaries))
print('final checks/inventory/source/executable closure complete',flush=True)

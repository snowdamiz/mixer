import sys,subprocess,json
from run import run,SCRATCH,HERE,b
import inventory
vm=SCRATCH/'candidate/vm'
def step(script,*args):
 p=subprocess.run(['python3','-B',str(HERE/script),*args]);assert p.returncode==0,(script,p.returncode)
step('regressions.py','final2');step('source_probe.py','final2')
schema=json.loads((HERE/'inventory-schema.json').read_text());audit=[];keys=['envelope','window','field','rustType','binding','sourceNames','position','config','kind','mirType']
for config in ['production','unit']:
 rows,defs,captures=inventory.canonical(HERE/(config+'.mir'),config);expected=[r for r in schema if r['config']==config];assert [{k:r[k]for k in keys}for r in rows]==[{k:r[k]for k in keys}for r in expected]
 audit.append(dict(config=config,canonicalBodies=len(defs),positiveCanonicalFields=len(rows),definitions=defs,sourceClosure=b.digest(b.manifest(vm)),mirSHA256=b.sha(HERE/(config+'.mir'))))
(HERE/'canonical-audit.json').write_bytes(b.enc(audit))
step('metadata.py','final2');step('frozen_identity.py','final2');step('matrix.py','final2');step('frozen_runtime.py','final2')
for feature,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:
  p=run('final2-check-'+feature+('-release'if release else'-debug'),['cargo','check','--lib','--locked','--offline',*flags,*(['--release']if release else[])],vm);assert p.returncode==0
for name,args in [('rustc',['rustc','-vV']),('cargo',['cargo','-V']),('rustfmt',['rustfmt','--version']),('python',['python3','--version']),('host',['uname','-a']),('git',['git','rev-parse','HEAD'])]:
 p=run('final2-tool-'+name,args);assert p.returncode==0
print('final exact-source qualification complete',flush=True)

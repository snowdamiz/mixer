from pathlib import Path
import subprocess,sys,json,datetime,os
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];tasks=[]
for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:tasks.append((config+('-release' if release else '-debug')+'-control-frame-value-unit',['cargo','test','--lib','--locked','--offline',*flags,*(['--release'] if release else []),'experimental_swift_reactor::execution::','--','--nocapture','--test-threads=1']))
for config,flags in [('span',['--features','experimental-span-execution']),('all',['--all-features'])]:
 for release in [False,True]:tasks.append((config+('-release' if release else '-debug')+'-frozen-parity',['cargo','test','--test','span_control_extraction','--locked','--offline',*flags,*(['--release'] if release else []),'--','--nocapture','--test-threads=1']))
for config,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:tasks.append((config+('-release' if release else '-debug')+'-check',['cargo','check','--lib','--locked','--offline',*flags,*(['--release'] if release else [])]))
tasks.append(('format-check',['cargo','fmt','--all','--','--check']))
results=[]
for name,args in tasks:
 if (HERE/'matrix-stop').exists():break
 p=subprocess.run([sys.executable,'-B',str(HERE/'run.py'),name,*args],cwd=ROOT,capture_output=True)
 (HERE/(name+'.log')).write_bytes(p.stdout+p.stderr);results.append(dict(name=name,exitCode=p.returncode,log=name+'.log'));(HERE/'matrix-summary.json').write_text(json.dumps(results,sort_keys=True,indent=2)+'\n');print(name,p.returncode,flush=True)
 if p.returncode:print((p.stdout+p.stderr).decode()[-6000:],flush=True);sys.exit(p.returncode)

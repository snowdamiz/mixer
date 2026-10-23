from pathlib import Path
import hashlib,json,datetime,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'verification/ui-measured-appearance-v2-contract'
r=json.loads((source/'receipt.json').read_text());lock=json.loads((source/'input-lock.json').read_text())
if r['status']!='passed-design-only':raise RuntimeError('not qualified design')
bindings=dict(r['artifacts'])
for p,h in lock['inputs'].items():
 if sha(ROOT/p)!=h or sha(source/'inputs'/p)!=h:raise RuntimeError('input mismatch '+p)
 bindings[p]=h
for c in r['commands']:
 if c['exit']!=0 or sha(ROOT/c['log'])!=c['sha256']:raise RuntimeError('command/log mismatch')
for p,h in bindings.items():
 if sha(ROOT/p)!=h:raise RuntimeError('artifact mismatch '+p)
if hashlib.sha256(''.join(p+'\0'+h+'\n' for p,h in sorted(r['artifacts'].items())).encode()).hexdigest()!=r['artifactCollectionSHA256']:raise RuntimeError('collection mismatch')
commands=[]
for mode,args in [('normal',[]),('optimized',['-O'])]:
 argv=[sys.executable,*args,str(source/'scripts/check-contract.py')]
 p=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 out=HERE/(mode+'.log');out.write_bytes(p.stdout)
 if p.returncode:raise RuntimeError(p.stdout.decode())
 commands.append({'argv':argv,'exit':p.returncode,'log':str(out.relative_to(ROOT)),'sha256':sha(out)})
for p in [source/'receipt.json',HERE/'accept.py']:
 bindings[str(p.relative_to(ROOT))]=sha(p)
accept={'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'status':'accepted-implementation-contract-only','reviewer':'root','bindings':bindings,'commands':commands,'scope':'Closed measuredShared2 contract frozen for independently owned V2 geometry, codec, resolver and native integration slices. Root reviewed schema/type boundaries, configurable defaults versus invariants, inherited disabled states, font hierarchy, fixed switch paths, group radius clamp, full-group layout, RTL, preference conversion and ordinary/signed failure boundaries. Public data is not native support or release authority.','limitations':['Both current adapters still use platform defaults; no §8.3 parity pass.','Authored curves/states/compact navigation are explicit new shared design choices; native exactness is not claimed.','Physical iOS/Android parity and interactions remain pending while phones disconnected.','Native resource capture, operation support, renderer consumption and signed V2 identity/install boundaries remain implementation work.','All GA and published FieldLog gates remain open.']}
(HERE/'acceptance.json').write_text(json.dumps(accept,indent=2,sort_keys=True)+'\n')
print('ACCEPT',len(bindings),'bindings; 13 model methods per normal/optimized; implementation contract only')

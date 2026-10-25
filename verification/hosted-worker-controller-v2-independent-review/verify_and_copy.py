#!/usr/bin/env python3
"""Independent read-only binding verification, then explicit owned copying."""
import hashlib,json,os,platform,shutil,stat,tarfile,tempfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer');HERE=ROOT/'verification/hosted-worker-controller-v2-independent-review';P=ROOT/'verification/hosted-worker-controller-v2'
EXPECTED={'receipt':'143295674a760138c358ce5d9ab749724d00848e7fe6eaae312228f6782c8a39','source':'c5848761151f9accfd81eff8292e756cff427e90092d9b7b309b010eb5feb736','archive':'17a5b38cbc7460d935b0b173ddc45ee8b9c4ef0da25587aa4a2746b3108909c2','closure':'ca309000071a7ef5608fe1925664e145bd5f6f7a7bce3fdb06373925728e2d6c'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(records):return hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def verify(p,e):
 assert p.is_file() and p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],str(p)
 if 'mode'in e:assert oct(stat.S_IMODE(p.stat().st_mode))==e['mode'],str(p)
 if 'symlink_target'in e:assert p.is_symlink() and os.readlink(p)==e['symlink_target'],str(p)
def archive(p,m):
 expected={e['path']:e for e in m['files']}
 with tarfile.open(p) as t:
  members=t.getmembers();assert len(members)==len(expected) and set(x.name for x in members)==set(expected)
  for x in members:
   assert x.isfile() and not Path(x.name).is_absolute() and '..'not in Path(x.name).parts
   b=t.extractfile(x).read();e=expected[x.name];assert len(b)==e['bytes']and hashlib.sha256(b).hexdigest()==e['sha256'],x.name
assert sha(P/'receipt.json')==EXPECTED['receipt'];r=json.loads((P/'receipt.json').read_text())
assert len(r['artifacts'])==352
for e in r['artifacts']:verify(ROOT/e['path'],e)
for k in ['source_manifest','source_archive','input_closure_manifest','input_closure_archive','root_internal_decisions']:
 verify(ROOT/r[k]['path'],r[k])
s=json.loads((P/'source-manifest.json').read_text());i=json.loads((P/'input-closure-manifest.json').read_text())
assert len(s['files'])==60 and digest(s['files'])==s['tree_sha256']==r['source_tree_sha256']==EXPECTED['source']
assert len(i['files'])==172 and digest(i['files'])==i['tree_sha256']==r['input_closure_tree_sha256']==EXPECTED['closure']
assert sha(P/'source-snapshot.tar.gz')==EXPECTED['archive']
for e in s['files']:verify(P/'candidate'/e['path'],e)
for e in i['files']:verify(ROOT/e['path'],e)
archive(P/'source-snapshot.tar.gz',s);archive(P/'input-closure.tar.gz',i)
deps=json.loads((P/'inputs/verification/hosted-worker-controller-implementation/dependency-files.json').read_text())['files']
jason=json.loads((P/'inputs/verification/hosted-worker-controller-implementation/jason-beams.json').read_text())['files']
assert len(deps)==1180 and len(jason)==29 and len(r['runtime_inputs'])==4
for e in deps+jason+r['runtime_inputs']:verify(ROOT/e['path'],e)
actual={str(p.relative_to(ROOT))for p in (ROOT/'hosted-worker-controller/node_modules').rglob('*')if p.is_file()}
assert actual=={e['path']for e in deps},'installed closure has extra or missing files'
for command in r['commands']:
 for c in command['commands']:
  for k in ['stdout','stderr']:verify(ROOT/c[k]['path'],c[k])
# Nothing above executes producer or dependency code. Copy only after all checks.
frozen=HERE/'frozen';frozen.mkdir(exist_ok=False)
union={e['path']:e for e in r['artifacts']+i['files']}
for rel in ['receipt.json','source-manifest.json','input-closure-manifest.json']:
 p=P/rel;union[str(p.relative_to(ROOT))]={'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
for path,e in sorted(union.items()):
 dest=frozen/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/path,dest);verify(dest,e)
# Include explicit consulted current instructions and review documents separately.
consulted=[]
for rel in ['AGENTS.md','docs/hosted-worker-controller-contract.md','docs/hosted-worker-controller-implementation-independent-review.md','docs/hosted-worker-controller-v2.md']:
 p=ROOT/rel;dest=HERE/'consulted'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);consulted.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
owned=Path(tempfile.mkdtemp(prefix='mixer-controller-v2-independent-'));(owned/'deps').mkdir()
for e in deps:
 src=ROOT/e['path'];dest=owned/'deps'/e['path'];dest.parent.mkdir(parents=True,exist_ok=True)
 if src.is_symlink():dest.symlink_to(os.readlink(src))
 else:shutil.copy2(src,dest)
for e in deps:verify(owned/'deps'/e['path'],e)
# Retain immutable input bytes in an archive, then remove disposable expanded copies at completion.
records=[{'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(frozen.rglob('*'))if p.is_file()]
(HERE/'frozen-input-manifest.json').write_text(json.dumps({'tree_sha256':digest(records),'files':records},indent=2)+'\n')
with tarfile.open(HERE/'frozen-inputs.tar.gz','w:gz')as t:
 for e in records:t.add(HERE/e['path'],arcname=e['path'],recursive=False)
state={'scratch':str(owned),'frozen':str(frozen),'producer_receipt_sha256':EXPECTED['receipt'],'source_tree_sha256':EXPECTED['source'],'counts':{'artifacts':352,'source':60,'input_closure':172,'dependencies':1180,'jason':29,'runtime_inputs':4},'frozen_records':len(records),'frozen_tree_sha256':digest(records),'frozen_archive_sha256':sha(HERE/'frozen-inputs.tar.gz'),'consulted':consulted,'versions_bound':r['versions'],'runtime_inputs':r['runtime_inputs'],'platform':platform.platform(),'time':datetime.now(timezone.utc).isoformat(),'before_execution':True,'dependency_installs':0,'install_scripts_executed':0,'no_git_inspected':True}
(HERE/'bindings.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))

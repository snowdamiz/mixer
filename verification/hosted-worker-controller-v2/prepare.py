#!/usr/bin/env python3
"""Verify frozen roots before creating the isolated repair candidate."""
import hashlib,json,os,platform,shutil,tarfile
from pathlib import Path
ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer'); HERE=Path(__file__).resolve().parent
P=ROOT/'verification/hosted-worker-controller-implementation'; R=ROOT/'verification/hosted-worker-controller-implementation-independent-review'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def check(e):
 p=ROOT/e['path']; assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],str(p)
 return p
def verify_archive(path,files):
 expected={e['path']:e for e in files}
 with tarfile.open(path) as t:
  assert set(t.getnames())==set(expected)
  for m in t:
   assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
   assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==expected[m.name]['sha256']
for p,h in [(P/'receipt.json','fb71bcb1cc076b121a26e075c8e1bf8c2703bc5a659686e4a6ae861b855dc68a'),(R/'receipt.json','7e146e6f341afc93dca4f108bbee7ee50f7c4a406eb329bd5fa96405463f5b7e')]:assert sha(p)==h
pr=json.loads((P/'receipt.json').read_text());rr=json.loads((R/'receipt.json').read_text());source=json.loads((P/'source-manifest.json').read_text())
assert hashlib.sha256(json.dumps(source['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==source['tree_sha256']=='6f47612d9bf3118fb50be51f36dc05bbd724bd60416a5cdec0b1fa6299042e95'
verified=[]; counts={}
for n in ['source-manifest.json','dependency-files.json','jason-beams.json']:
 es=json.loads((P/n).read_text())['files'];counts[n]=len(es)
 for e in es:check(e);verified.append(e)
for name,es in [('producer_artifacts',pr['artifacts']),('runtime_inputs',pr['runtime_binary_inputs']),('review_artifacts',rr['artifacts'])]:
 counts[name]=len(es)
 for e in es:check(e);verified.append(e)
for c in pr['commands_and_outputs']:
 for k in ['stdout','stderr']:check(c[k])
counts['producer_command_outputs']=len(pr['commands_and_outputs'])
verify_archive(P/'source-snapshot.tar.gz',source['files'])
with tarfile.open(R/'review-fixtures.tar.gz') as t:
 expected={e['path']:e for e in rr['artifacts']};assert len(t.getnames())==12
 for m in t:
  assert m.isfile() and m.name in expected
  assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==expected[m.name]['sha256']
counts['review_archived_fixtures']=12
lock=json.loads((ROOT/'hosted-worker-controller/package-lock.json').read_text());inv=json.loads((ROOT/'hosted-worker-controller/THIRD_PARTY.yml').read_text());deps={x['lockPath']:x for x in inv['packages']}
assert len(deps)==len(lock['packages'])-1==58
for path,e in lock['packages'].items():
 if not path:continue
 for k in ['version','license','integrity','resolved']:assert deps[path][k]==e[k]
 assert deps[path]['purpose'] and deps[path]['scope']=='development-only' and not deps[path]['installScriptsExecuted']
assert not (HERE/'candidate').exists()
(HERE/'inputs').mkdir()
for e in verified:
 p=check(e)
 # Runtime/dependency bytes stay in place; their exact manifests are copied below.
 if '/node_modules/' in str(p) or e in pr['runtime_binary_inputs'] or e['path'].startswith('hosted/_build/'):continue
 dest=HERE/'inputs'/e['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
for p in [P/'receipt.json',P/'source-manifest.json',P/'source-snapshot.tar.gz',P/'dependency-files.json',P/'jason-beams.json',R/'receipt.json',R/'review-fixtures.tar.gz']:
 dest=HERE/'inputs'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
with tarfile.open(P/'source-snapshot.tar.gz') as t:t.extractall(HERE/'candidate',filter='data')
report={'status':'passed','verified_counts':counts,'producer_receipt_sha256':sha(P/'receipt.json'),'rejected_review_receipt_sha256':sha(R/'receipt.json'),'source_tree_sha256':source['tree_sha256'],'source_archive_sha256':sha(P/'source-snapshot.tar.gz'),'dependency_entries':58,'dependency_installs':0,'install_scripts_executed':0,'platform':platform.platform(),'no_git_inspected':True}
(HERE/'baseline-bindings.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

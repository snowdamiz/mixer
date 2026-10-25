#!/usr/bin/env python3
"""Read-only frozen packet verification, without executing candidate code."""
import hashlib,json,tarfile
from pathlib import Path
ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer');HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify_record(e):
 p=ROOT/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path']
def verify_archive(archive,manifest,prefix):
 records=manifest['files'];expected={prefix+e['path']:e for e in records}
 with tarfile.open(archive) as t:
  assert set(t.getnames())==set(expected)
  for m in t:
   assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
   assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==expected[m.name]['sha256'],m.name
r=json.loads((HERE/'receipt.json').read_text())
for e in r['artifacts']:verify_record(e)
s=json.loads((HERE/'source-manifest.json').read_text());assert hashlib.sha256(json.dumps(s['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==r['source_tree_sha256']==s['tree_sha256']
for e in s['files']:
 p=HERE/'candidate'/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path']
verify_archive(HERE/'source-snapshot.tar.gz',s,'')
i=json.loads((HERE/'input-closure-manifest.json').read_text());assert hashlib.sha256(json.dumps(i['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==r['input_closure_tree_sha256']
for e in i['files']:verify_record(e)
verify_archive(HERE/'input-closure.tar.gz',i,'')
assert r['status']=='frozen-v2-repair-awaiting-independent-review'
for command in r['commands']:
 for e in command['commands']:
  for k in ['stdout','stderr']:verify_record(e[k])
for run in r['commands']:
 c=run['cleanup'];assert c['scratch_removed'] and not Path(c['scratch']).exists() and not c['matching_owned_workerd']
 for action in c['actions']:
  if 'persist' in action:assert not Path(action['persist']).exists()
print(json.dumps({'status':'passed','receipt_sha256':sha(HERE/'receipt.json'),'source_tree_sha256':s['tree_sha256'],'input_closure_tree_sha256':r['input_closure_tree_sha256'],'artifact_records':len(r['artifacts']),'candidate_source_records':len(s['files']),'input_closure_records':len(i['files']),'acceptance':False}))

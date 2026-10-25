#!/usr/bin/env python3
import hashlib,json,pathlib,tarfile,datetime,shutil,sys
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent.parent
PROD=ROOT/'verification/hosted-worker-transport-v2'
sha=lambda b:hashlib.sha256(b).hexdigest()
EXPECTED='3a386653714f44bc156d9b5c3f01b5917d93428b1c9ee1dd291ecab789b8d5de'
b=(PROD/'receipt.json').read_bytes();assert sha(b)==EXPECTED
r=json.loads(b); m=json.loads((PROD/r['source_map']).read_bytes())
assert r['source_digest']==m['source_digest']=='a46f83d136c2761f0f28b0599d62a088392534dbf4b806009e8f01015c905ad0'
rows=m['inputs'];assert len(rows)==r['input_count']==107
assert sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode())==r['source_digest']
for row in rows:
 p=ROOT/row['path'];assert p.is_file() and not p.is_symlink();d=p.read_bytes();assert len(d)==row['size'] and sha(d)==row['sha256'],row['path']
assert r['input_archive_sha256']=='73fb5f300b21f2c537b1987191c3cbd37ac1535f0afb86650a50bbccc1f721df'
assert r['output_archive_sha256']=='2a9fe04ccff62abb42a70da1b63c2ea61cb20aa95edf79d8e750f6c131780b15'
archives={}
for key, expected in [('input_archive',rows),('output_archive',r['output_bindings'])]:
 path=PROD/r[key];assert sha(path.read_bytes())==r[key+'_sha256']
 with tarfile.open(path,'r:gz') as t:
  members=t.getmembers();assert all(x.isfile() and not pathlib.PurePosixPath(x.name).is_absolute() and '..' not in pathlib.PurePosixPath(x.name).parts for x in members)
  assert len(members)==len({x.name for x in members})==len(expected)
  contents={x.name:t.extractfile(x).read() for x in members}
  assert set(contents)=={x['path'] for x in expected}
  for row in expected:
   d=contents[row['path']];assert len(d)==row['size'] and sha(d)==row['sha256'],row['path']
   if key=='output_archive':assert (PROD/row['path']).read_bytes()==d,row['path']
  archives[key]=contents
cmds=json.loads(archives['output_archive'][r['commands']])['commands']
assert len(cmds)==25
for c in cmds:
 assert c['exit_code']==0
 for stream in ['stdout','stderr']:
  assert sha(archives['output_archive'][c[stream]])==c[stream+'_sha256']
assert sum(x['tests'] for x in r['test_groups'])==r['tests']==42
assert r['vectors']['vectors']==36
assert all(x['failures']==x['skipped']==x['excluded']==0 and x['frozen_modules_loaded']==[] for x in r['test_groups'])
safe=[x['path'] for x in rows if '/candidate/context/' in x['path'] or '/candidate/lib/' in x['path']]
assert len(safe)==10 and all('authority' not in x.lower() and 'catalog' not in x.lower() for x in safe)
proof={'schema':1,'status':'verified-before-extraction','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'receipt_sha256':EXPECTED,'source_digest':r['source_digest'],'inputs_current_and_archived':len(rows),'outputs_current_and_archived':len(r['output_bindings']),'commands_bound':len(cmds),'safe_compiler_input_paths':safe,'producer_tests':42,'vectors':36,'frozen_lane_read_loaded_executed':False,'verifier_sha256':sha(pathlib.Path(__file__).read_bytes())}
(HERE/'binding-proof.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
# All bindings passed above before copying any frozen content into owned scratch.
scratch=HERE/'scratch';assert not scratch.exists()
for name,data in archives['input_archive'].items():
 p=scratch/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
for name in ['receipt.json',r['source_map'],r['commands']]:shutil.copyfile(PROD/name,HERE/('frozen-'+name))
print(json.dumps(proof,sort_keys=True))

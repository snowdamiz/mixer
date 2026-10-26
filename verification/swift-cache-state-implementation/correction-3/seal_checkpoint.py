#!/usr/bin/env python3
"""Freeze exact c3 source/evidence; never mutate an existing candidate seal."""
import datetime,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[2]
seal=ROOT/'candidate-repo-seal.json';assert not seal.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
preserved=[]
for rel,expected in [
 ('verification/swift-cache-state-implementation/candidate-repo-seal.json','caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3'),
 ('verification/swift-cache-state-implementation/correction-1/candidate-repo-seal.json','b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6'),
 ('verification/swift-cache-state-implementation/correction-2/candidate-repo-seal.json','26e6ece9d86f054a57e335c6b170595aa1d21e3081b45db4eda167e59abe52fb'),
 ('verification/swift-cache-state-g3-proposal3/seal.json','8bacc0355f35b504889784313ce070365f347262908bd3d416f26b2b6e11aa0b'),
 ('verification/swift-cache-state-g3-proposal4/seal.json','70beb0e18af675ff2213eade75f98bfdaf15cc4337ff00dfcca9201414705caa'),
 ('verification/swift-cache-state-g6-independent-review/seal.json','21343e183de35954dc39f74c27dbca01afed0f91793fac9d3d68ae1682a199e9'),
 ('verification/swift-semantic-adapter-root-review/clear128-anonymous-proposal/seal.json','ed0fa3abe9394bf4f7edfca280d80de7f89011a5eb6abb0db5742a13cf8cabb2')]:
 p=REPO/rel;assert sha(p)==expected;j=json.loads(p.read_text())
 for m in j['members']:
  q=REPO/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256']
 preserved.append({'seal':rel,'sha256':expected,'members_verified':len(j['members']),'bytes_verified':sum(m['bytes']for m in j['members'])})
assert not list(ROOT.glob('.scratch-*'))and not list(ROOT.rglob('__pycache__'))
for c in json.loads((ROOT/'evidence/owned-product-cleanup.json').read_text()):assert not(ROOT/c['path']).exists()
before=json.loads((ROOT/'evidence/source-before.json').read_text())
assert before=={str(p.relative_to(ROOT)):sha(p)for p in (ROOT/'source').rglob('*')if p.is_file()}
for n in ['checkpoint-audit.stderr','compaction.stderr','host-coordinator.stderr','validation-coordinator.stderr','phase-inventory.stderr']:assert(ROOT/'evidence'/n).stat().st_size==0
source_rows=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted((ROOT/'source').rglob('*'))if p.is_file()]
source_digest=hashlib.sha256(json.dumps(source_rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
members=[]
for p in sorted(ROOT.rglob('*')):
 if p.is_file():
  assert not p.is_symlink()and p.suffix not in ['.rlib','.binary']
  members.append({'path':str(p.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p)})
j={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'builder_sha256':sha(pathlib.Path(__file__)),
 'status':'frozen correction3 selected16x128 clear; fresh host behavior/API/layout checkpoint, complete work/lifetime pending',
 'member_path_base':'repository-root','owned_scope':['verification/swift-cache-state-implementation/correction-3/**'],
 'excluded':['verification/swift-cache-state-implementation/correction-3/candidate-repo-seal.json'],
 'members':members,'member_count':len(members),'member_bytes':sum(m['bytes']for m in members),
 'source_tree_digest':source_digest,'source_tree_digest_method':'SHA256 of compact sorted-key JSON array of source-relative path/bytes/sha256 rows, rows path-sorted',
 'source_rows':source_rows,'library_sha256':{p.name:sha(p)for p in (ROOT/'source/library').glob('*.rs')},
 'preserved_packets':preserved,'selection_sha256':'1fc73e9daa6ba38009fa4f30a68285b0ee0977169198a8f3da0be1b94a606c4e',
 'source_budget_accepted':False,'G6_complete_640_proved':False,'G6_external_ledger_pending_at_freeze':True,
 'G3_G4_accepted':False,'lifetime_29344_union_proved':False,'lifetime_proof_accepted':False,
 'root_implementation_accepted':False,'independent_accepted':False,'native_runtime_or_capture_started':False,'GA_qualified':False}
seal.write_text(json.dumps(j,indent=2)+'\n')
print(json.dumps({'seal':str(seal.relative_to(REPO)),'sha256':sha(seal),'members':len(members),'bytes':j['member_bytes'],'source_tree_digest':source_digest},indent=2))

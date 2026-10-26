#!/usr/bin/env python3
"""Final repository-relative custody wrapper; all prior sealed bytes preserved."""
import datetime,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
final=ROOT/'candidate-repo-seal.json';assert not final.exists()
prior=[]
for name in ['seal.json','candidate-v2-seal.json']:
 p=ROOT/name;data=json.loads(p.read_text())
 for m in data['members']:
  q=ROOT/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256']
 prior.append({'path':str(p.relative_to(REPO)),'sha256':sha(p),'members':data['member_count'],'path_base':'producer-root; preserved intermediate seal only'})
handoff=json.loads((ROOT/'handoff-v2.json').read_text());handoff.update({'status':'final immutable producer candidate; repository-relative custody; root admission and independent acceptance pending','candidate_seal_path':str(final.relative_to(REPO)),'member_path_base':'repository-root','supersedes_intermediate_seals':prior,'artifact_case_disposition':'verification/swift-cache-state-implementation/evidence/final-case-classification.json','final_library_sha256':{str((ROOT/path).relative_to(REPO)):digest for path,digest in handoff['library_sha256'].items()}})
(ROOT/'handoff-final.json').write_text(json.dumps(handoff,indent=2)+'\n')
files=[p for p in ROOT.rglob('*')if p.is_file()]+[REPO/'docs/swift-cache-state-implementation.md']
members=[{'path':str(p.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(files)]
assert len({m['path']for m in members})==len(members)
base=json.loads((ROOT/'candidate-v2-seal.json').read_text());payload={k:v for k,v in base.items()if k not in ['schema','at','members','member_count','member_bytes','excluded','status','effective_case_evidence']};payload.update({'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'builder_sha256':sha(pathlib.Path(__file__)),'status':'final-frozen-producer-candidate-repository-relative-custody-awaiting-root-and-independent-admission','member_path_base':'repository-root','owned_scope':['verification/swift-cache-state-implementation/**','docs/swift-cache-state-implementation.md'],'excluded':[str(final.relative_to(REPO))],'preserved_intermediate_seals':prior,'effective_case_evidence':'verification/swift-cache-state-implementation/evidence/final-case-classification.json','members':members,'member_count':len(members),'member_bytes':sum(m['bytes']for m in members),'root_implementation_accepted':False,'independent_accepted':False,'native_runtime_or_capture_started':False,'GA_qualified':False})
final.write_text(json.dumps(payload,indent=2)+'\n')
for m in members:
 p=REPO/m['path'];assert p.stat().st_size==m['bytes']and sha(p)==m['sha256']
actual={str(p.relative_to(REPO))for p in ROOT.rglob('*')if p.is_file()}|{'docs/swift-cache-state-implementation.md'}
assert actual=={m['path']for m in members}|{str(final.relative_to(REPO))}
for p in prior:assert sha(REPO/p['path'])==p['sha256']
print(json.dumps({'seal':str(final.relative_to(REPO)),'seal_sha256':sha(final),'member_path_base':'repository-root','members':len(members),'bytes':payload['member_bytes'],'source_tree_digest':payload['source_tree_digest'],'library_sha256':handoff['final_library_sha256'],'all_prior_sealed_bytes_preserved':True},indent=2))

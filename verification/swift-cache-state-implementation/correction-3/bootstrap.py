#!/usr/bin/env python3
"""Create only correction3 from sealed inputs; preserve all old packets."""
import difflib,hashlib,json,pathlib,shutil,sys
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
selection=REPO/'verification/swift-semantic-adapter-root-review/clear128-correction3-selection.json'
assert sha(selection)=='1fc73e9daa6ba38009fa4f30a68285b0ee0977169198a8f3da0be1b94a606c4e'
j=json.loads(selection.read_text());baselines=[]
for rel,expected in [('verification/swift-cache-state-implementation/correction-2/candidate-repo-seal.json','26e6ece9d86f054a57e335c6b170595aa1d21e3081b45db4eda167e59abe52fb')]+[(p['seal'],p['sha256'])for p in j['packets']]:
 p=REPO/rel;assert sha(p)==expected;b=json.loads(p.read_text())
 for m in b['members']:
  q=REPO/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256']
 baselines.append({'path':rel,'sha256':expected,'members_verified':len(b['members']),'bytes_verified':sum(m['bytes']for m in b['members'])})
old=REPO/'verification/swift-cache-state-implementation/correction-2';copies=[]
for folder in ['source','api']:
 for p in sorted((old/folder).rglob('*')):
  if p.is_file():
   dest=ROOT/p.relative_to(old);dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.copy2(p,dest)
   copies.append({'source':str(p.relative_to(REPO)),'destination':str(dest.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p),'copied_identically':True})
for n in ['run_host.py','run_regressions.py','api_checks.py','run_old_api.py','validate_regressions.py']:
 p=old/n;dest=ROOT/n;shutil.copy2(p,dest);copies.append({'source':str(p.relative_to(REPO)),'destination':str(dest.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p),'copied_identically_before_runner_evidence_changes':True})
selected=REPO/j['selected_source']['path'];assert sha(selected)==j['selected_source']['sha256']
dest=ROOT/'source/library/cache_state.rs';before=dest.read_text();after=selected.read_text()
a=before.index('    let zero = [0u8; 8];',before.index('fn cleanup('));z=before.index('    c[888..896]',a)
aa=after.index('    c[0..128].copy_from_slice',after.index('fn cleanup('));zz=after.index('    c[888..896]',aa)
assert before[:a]==after[:aa]and before[z:]==after[zz:]
dest.write_bytes(selected.read_bytes());assert sha(dest)=='0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
(ROOT/'evidence').mkdir();(ROOT/'proofs').mkdir()
(ROOT/'proofs/selected-product.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='correction2/cache_state.rs',tofile='correction3/cache_state.rs')))
(ROOT/'proofs/custody.json').write_text(json.dumps({'schema':1,'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'selection':{'path':str(selection.relative_to(REPO)),'sha256':sha(selection)},'baselines_verified':baselines,'copies':copies,'selected_source':j['selected_source'],'actual_library_sha256':{p.name:sha(p)for p in (ROOT/'source/library').glob('*.rs')},'only_product_change':'old256x8 clear block ->selected16x128 anonymous direct borrowed stores; exact prefix/suffix unchanged','all_expected_test_inputs_unchanged':True,'source_accounting_accepted':False,'lifetime_proof_accepted':False},indent=2)+'\n')
print(json.dumps({'copied_inputs':len(copies),'actual_library_sha256':{p.name:sha(p)for p in (ROOT/'source/library').glob('*.rs')},'only_selected_clear_changed':True},indent=2))

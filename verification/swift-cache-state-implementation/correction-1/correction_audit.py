#!/usr/bin/env python3
"""Bind only the selected guard correction; verify original454 bytes immutable."""
import difflib,hashlib,json,pathlib,sys
from run_host import ROOT,REPO,sha
BASE=ROOT.parent
selection=REPO/'verification/swift-semantic-adapter-root-review/guard-correction-selection.json'
assert sha(selection)=='0f70d7f9ce793d710da4d1d3dc97debaf8474d8bfb9031f77fdd1af5ddbc22fe'
seal=BASE/'candidate-repo-seal.json';assert sha(seal)=='caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3'
original=json.loads(seal.read_text());assert len(original['members'])==454
for m in original['members']:
 p=REPO/m['path'];assert p.stat().st_size==m['bytes']and sha(p)==m['sha256'],m['path']
old=(BASE/'source/library/cache_state.rs').read_text();new=(ROOT/'source/library/cache_state.rs').read_text()
def isolate(text,name):
 start=text.index('fn '+name+'(');body=text.index('{',start);depth=0
 for i in range(body,len(text)):
  if text[i]=='{':depth+=1
  if text[i]=='}':
   depth-=1
   if depth==0:return text[:start],text[start:i+1],text[i+1:]
 raise ValueError(name)
a,b,c=isolate(old,'shape_q');x,y,z=isolate(new,'shape_q');assert a==x and c==z
for n in ['analyzer.rs','envelope.rs']:
 assert (BASE/'source/library'/n).read_bytes()==(ROOT/'source/library'/n).read_bytes()
old_tests=(BASE/'source/tests/cache_state_tests.rs').read_bytes();assert (ROOT/'source/tests/cache_state_tests.rs').read_bytes().startswith(old_tests)
(ROOT/'proofs/selected-product.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original-sealed/cache_state.rs',tofile='correction-1/cache_state.rs')))
receipt={'schema':1,'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'selection_sha256':sha(selection),'original_seal_sha256':sha(seal),'original454_members_verified_unchanged':True,'original_external_doc_unchanged':True,'only_changed_product_function':'shape_q','old_function_sha256':hashlib.sha256(b.encode()).hexdigest(),'new_function_sha256':hashlib.sha256(y.encode()).hexdigest(),'product_prefix_and_suffix_bytes_unchanged':True,'unchanged_other_product_files':['analyzer.rs','envelope.rs'],'old_producer_test_prefix_unchanged':True,'new_focused_tests':'source/tests/guard_correction_tests.rs','source_sha256':{str(p.relative_to(ROOT)):sha(p)for p in sorted((ROOT/'source').rglob('*'))if p.is_file()},'no_independent_fixtures_or_oracle_or_glue_read_or_imported':True,'work_status':'same caps and unchanged leaf/cleanup/return source; inherited coarse-work and caller proofs still require independent reconciliation','native_runtime_or_capture_started':False,'independent_accepted':False,'GA_qualified':False}
(ROOT/'proofs/correction-source-audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('CORRECTION_AUDIT original454 unchanged; only shape_q product body differs')

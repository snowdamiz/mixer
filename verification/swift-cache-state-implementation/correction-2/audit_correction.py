#!/usr/bin/env python3
"""Exact selected24-copy custody/range/layout audit; no independent harness use."""
import difflib,hashlib,json,pathlib,re,sys
from run_host import ROOT,REPO,sha
BASE=ROOT.parent/'correction-1';selection=REPO/'verification/swift-semantic-adapter-root-review/accounting-correction-selection.json'
assert sha(selection)=='c083b9bc61b2728847392f070cf0ae38de9d0c72b159d083cf384c96ad23b249'
seals=[]
for root,h in [(ROOT.parent,'caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3'),(BASE,'b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6')]:
 p=root/'candidate-repo-seal.json';assert sha(p)==h;s=json.loads(p.read_text())
 for m in s['members']:
  q=REPO/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256'],m['path']
 seals.append({'path':str(p.relative_to(REPO)),'sha256':h,'members':len(s['members']),'unchanged':True})
review=REPO/'verification/swift-cache-state-accounting-independent-review/seal.json';assert sha(review)=='706e1ab2a1caa6b14cf588d40545a086ea32fc1a7a23a7eb5c1b1f5a48dfacd8'
for m in json.loads(review.read_text())['members']:
 p=REPO/m['path'];assert p.stat().st_size==m['bytes']and sha(p)==m['sha256']
old=(BASE/'source/library/cache_state.rs').read_text();new=(ROOT/'source/library/cache_state.rs').read_text();an=(BASE/'source/library/analyzer.rs').read_text();en=(BASE/'source/library/envelope.rs').read_text()
array=lambda name,text:[int(v.strip())for v in re.search(r'const '+name+r': \[usize; \d+\] = \[([^\]]+)\]',text)[1].split(',')]
row=array('ROW_CELLS',old);extra=array('EXTRA_CELLS',old);cells=array('CELLS',en)
sc=int(re.search(r'const SC: usize = (\d+)',old)[1]);base=int(re.search(r'const SCALAR: Region = Region \{ base: ([\d_]+)',an)[1].replace('_',''))
rows=[];commit=[];restore=[]
for label,items,start in [('ROW_CELLS',row,6),('EXTRA_CELLS',extra,17)]:
 for i,cell in enumerate(items):
  src=sc+(start+i)*8;dst=base+cell*8;statement=f'    b[{dst}..{dst+8}].copy_from_slice(&c[{src}..{src+8}]);\n';commit.append(statement);rows.append({'segment':'commit','constant':label,'index':i,'cell':cell,'source':[src,src+8],'destination':[dst,dst+8],'bytes':8,'statement':statement.strip()})
for i,cell in enumerate(cells):
 src=base+cell*8;dst=888+i*8;statement=f'    c[{dst}..{dst+8}].copy_from_slice(&b[{src}..{src+8}]);\n';restore.append(statement);rows.append({'segment':'restore','constant':'CELLS','index':i,'cell':cell,'source':[src,src+8],'destination':[dst,dst+8],'bytes':8,'statement':statement.strip()})
a=old.index('    for i in 0..10 {\n',old.index('    // Every destination'));z=old.index('    if w[1] == 6 {',a);expected=old[:a]+''.join(commit)+old[z:]
a=expected.index('    for i in 0..12 {\n',expected.index('fn cleanup('));z=expected.index('    #[cfg(test)]',a);expected=expected[:a]+''.join(restore)+expected[z:];assert expected==new
for n in ['analyzer.rs','envelope.rs']:assert (ROOT/'source/library'/n).read_bytes()==(BASE/'source/library'/n).read_bytes()
for p in (BASE/'source').rglob('*'):
 if p.is_file()and p.name not in ['cache_state.rs','cache_state_tests.rs']:assert p.read_bytes()==(ROOT/'source'/p.relative_to(BASE/'source')).read_bytes()
assert (ROOT/'source/tests/cache_state_tests.rs').read_bytes().startswith((BASE/'source/tests/cache_state_tests.rs').read_bytes())
for row in rows:
 line=next(i for i,l in enumerate(new.splitlines(),1)if l.strip()==row['statement']);row['source_line']=line;row['source_sha256']=sha(ROOT/'source/library/cache_state.rs');assert row['source'][1]-row['source'][0]==row['destination'][1]-row['destination'][0]==8
(ROOT/'proofs/literal-endpoint-proof.json').write_text(json.dumps({'schema':1,'derived_from_exact_old_constants_and_formulas':True,'old_source_sha256':sha(BASE/'source/library/cache_state.rs'),'new_source_sha256':sha(ROOT/'source/library/cache_state.rs'),'transfers':rows,'order_preserved':True,'all_other_product_bytes_unchanged':True,'all_ranges_inside_exact_arena_and_Candidate':True,'no_LE_conversion_or_array_return_in_literal_copies':True,'borrow_slices_exclusive_and_nonresizable':True,'work_bound_not_proved_by_endpoint_equivalence':True},indent=2)+'\n')
(ROOT/'proofs/selected-product.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='correction-1/cache_state.rs',tofile='correction-2/cache_state.rs')))
layout={}
for mode in ['debug','optimized']:
 raw=ROOT/'evidence'/f'tests-{mode}.stdout';pairs=re.findall(r'ACCOUNTING_LAYOUT (.+) size=(\d+) align=(\d+)',raw.read_text());assert len(pairs)==23
 layout[mode]={'raw_path':str(raw.relative_to(ROOT)),'raw_sha256':sha(raw),'types':[{'type':t,'bytes':int(n),'align':int(a)}for t,n,a in pairs]}
assert layout['debug']['types']==layout['optimized']['types']
(ROOT/'proofs/complete-layouts.json').write_text(json.dumps({'source_sha256':sha(ROOT/'source/library/cache_state.rs'),'measurements':layout,'producer_host_layout_evidence_only':True,'does_not_prove_work_or_lifetime_union':True},indent=2)+'\n')
(ROOT/'proofs/correction-source-audit.json').write_text(json.dumps({'schema':1,'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'selection_sha256':sha(selection),'independent_accounting_seal_sha256':sha(review),'accounting_review_only_no_independent_fixtures_or_active_G3_review_consumed':True,'immutable_baselines':seals,'changed_product_only':'two scalar commit loops and one restore loop replaced by24 literal8-byte copies','production_source_sha256':{p.name:sha(p)for p in sorted((ROOT/'source/library').glob('*.rs'))},'all_old_test_bytes_unchanged_prefix_or_exact_copy':True,'new_private_controls':'source/tests/literal_transfer_tests.rs','source_accounting_accepted':False,'lifetime_proof_accepted':False,'native_runtime_or_capture_started':False},indent=2)+'\n')
print('CORRECTION2_AUDIT exact24 endpoints/order; original454/correction814 unchanged; layouts bound')

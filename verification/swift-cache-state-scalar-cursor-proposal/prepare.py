#!/usr/bin/env python3
"""Isolated source proposal: remove cursor aggregate field projections only."""
import difflib,hashlib,json,pathlib,re
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'verification/swift-cache-state-prefix-subtraction-proposal/source/cache_state.rs.txt'
SHA='6ae313ca80cc32e73a081c3925a6c99862c6628dd8e9f1042ecdeedd7d703708'
def digest(b):return hashlib.sha256(b).hexdigest()
def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
old=BASE.read_bytes()
if digest(old)!=SHA:raise ValueError('base digest')
s=old.decode();start=s.index('#[repr(C)]\nstruct FixedArrayMergeCursor');end=s.index('#[cfg(test)]\nstatic COMMIT_FAULT',start)
chunk=s[start:end]
struct=chunk[:chunk.index('fn merge(')]
chunk=chunk[len(struct):]
pat=r'''            let mut s = FixedArrayMergeCursor \{\n                indices: source, timestamps,\n                lp: 0, le: (\d+), rp: (\d+), re: (\d+),\n                li: 256, ri: 256, lt: 0, rt: 0,\n            \};'''
def locals_(m):
 return ('            let mut lp: usize = 0;\n'
         f'            let mut le: usize = {m[1]};\n'
         f'            let mut rp: usize = {m[2]};\n'
         f'            let mut re: usize = {m[3]};\n'
         '            let mut li: u16 = 256;\n'
         '            let mut ri: u16 = 256;\n'
         '            let mut lt: u64 = 0;\n'
         '            let mut rt: u64 = 0;')
chunk,n=re.subn(pat,locals_,chunk)
if n!=5:raise ValueError('five constructors')
fields={k:len(re.findall(r'\bs\.'+k+r'\b',chunk)) for k in ['indices','timestamps','lp','le','rp','re','li','ri','lt','rt']}
for k in fields:chunk=re.sub(r'\bs\.'+k+r'\b',{'indices':'source','timestamps':'timestamps'}.get(k,k),chunk)
if re.search(r'\bs\.',chunk) or 'FixedArrayMergeCursor' in chunk:raise ValueError('cursor residual')
new=s[:start]+chunk+s[end:]
(HERE/'source/cache_state.rs.txt').write_text(new)
(HERE/'proposed.diff').write_text(''.join(difflib.unified_diff(s.splitlines(True),new.splitlines(True),fromfile='FROZEN_PREFIX_SUBTRACTION/cache_state.rs',tofile='UNSELECTED_SCALAR_CURSOR/cache_state.rs')))
write('source-assembly.json',dict(schema=1,predecessor_path=str(BASE.relative_to(ROOT)),predecessor_sha256=SHA,proposed_sha256=digest(new.encode()),edit_start_byte=start,old_fragment_bytes=end-start,new_fragment_bytes=len(chunk.encode()),old_fragment_sha256=digest(s[start:end].encode()),new_fragment_sha256=digest(chunk.encode()),unchanged_prefix_sha256=digest(s[:start].encode()),unchanged_suffix_sha256=digest(s[end:].encode()),constructors_replaced=n,field_access_replacements=fields,all_other_bytes_identical=True,canonical_source_changed=False,implementation_selected=False))
paths=['AGENTS.md','PLAN.md','mixer-product-plan.md','verification/swift-semantic-adapter-root-review/prefix-subtraction-merge-decision.json','verification/swift-cache-state-prefix-subtraction-proposal/seal.json',str(BASE.relative_to(ROOT)),'verification/swift-cache-state-merge-control-independent/seal.json','verification/swift-semantic-adapter-root-review/row-probe-G2-selection.json','verification/swift-semantic-adapter-root-review/row-probe-G5-G6-ownership.json','verification/swift-semantic-adapter-root-review/C3-remaining-work-selection.json','verification/swift-semantic-adapter-root-review/C3-lifetime-selection.json','verification/swift-cache-state-c3-lifetime-accounting/seal.json','verification/swift-cache-state-c3-lifetime-independent/seal.json','verification/swift-cache-state-c3-lifetime-accounting/phases.json','verification/swift-cache-state-c3-lifetime-accounting/templates.json','verification/swift-cache-state-c3-lifetime-accounting/named-places.json','verification/swift-cache-state-c3-lifetime-independent/coverage-addendum.json','verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs','verification/swift-cache-state-row-probe-independent/G2-lifetimes.json']
files=[]
for n in paths:
 b=(ROOT/n).read_bytes();r=dict(path=n,sha256=digest(b),bytes=len(b))
 if n in ['AGENTS.md','PLAN.md','mixer-product-plan.md']:
  p=HERE/'inputs'/n;p.parent.mkdir(exist_ok=True);p.write_bytes(b);r['snapshot']=str(p.relative_to(HERE))
 files.append(r)
write('input-bindings.json',dict(schema=1,files=files,input_tree_digest=digest(json.dumps(files,sort_keys=True,separators=(',',':')).encode()),input_code_imported_or_executed=False))
print(json.dumps(dict(proposed_sha256=digest(new.encode()),constructors=5,replacement_fields=fields)))

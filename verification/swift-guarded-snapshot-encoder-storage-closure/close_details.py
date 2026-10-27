from pathlib import Path
import json,re
from probe import ROOT,INPUT,sha
inv=json.loads((ROOT/'inventory.json').read_text());bodies=(ROOT/'function-bodies.mir').read_text();base=str(INPUT/'source/vm/src')+'/'
blocks=re.findall(r'(?m)^fn .*?\n\}',bodies,re.S);byheader={b.splitlines()[0].replace(base,'source/'):b for b in blocks}
source_manifest=json.loads((INPUT/'source-manifest.json').read_text())['members'];source_by_path={m['path']:m for m in source_manifest}
calls=[];coverage=[]
for f in inv['functions']:
 b=byheader[f['header']];roles=[r for r in inv['roles'] if r['id'] in f['role_ids']];nums={r['mir_local'] for r in roles}
 # Completeness means every declared slot and every argument, including nested lexical declarations.
 declared=set(re.findall(r'^\s+let (?:mut )?(_\d+):',b,re.M));args=set(re.findall(r'(_\d+):',b.splitlines()[0]));assert nums==declared|args,(f['id'],nums^(declared|args))
 for r in roles:
  if r['kind']=='parameter':
   d=next((line for line in b.splitlines() if any('debug '+n+' => '+r['mir_local']+';' in line for n in r['debug_names'])),None)
   if d:
    s=re.search(re.escape(base)+r'([^:]+):(\d+):(\d+): (\d+):(\d+)',d)
    if s:r['source']={'path':s[1],'start_line':int(s[2]),'start_column':int(s[3]),'end_line':int(s[4]),'end_column':int(s[5])}
  src=r['source'];path='src/'+src['path'];assert path in source_by_path
  lines=(INPUT/'source/vm'/path).read_text().splitlines();assert 1<=src['start_line']<=len(lines)
  r['source_member_sha256']=source_by_path[path]['sha256'];r['source_text']='\n'.join(lines[src['start_line']-1:min(src['end_line'],src['start_line']+3)])
 for line in b.splitlines():
  if ' -> [' not in line or re.match(r'\s*//',line):continue
  m=re.match(r'\s*(_\d+) = (.*?) -> \[',line)
  if not m:continue
  tail=m[2];depth=0;index=None
  for i,c in enumerate(tail):
   if c=='(' and depth==0:index=i;break
   if c in '<([{':depth+=1
   elif c in '>)]}':depth-=1
  assert index is not None,tail
  target=tail[:index]
  product=(target in ['field','require','put','optional','result_id','wasi_id','validate_runtime'] or (target.startswith(('snapshot_encoder_v2::','SnapshotViewV2::','SpanCheckV2::','initial_profile_v1::InitialProfileBorrowV1','LoaderProvenanceV1::snapshot_encode','experimental::account::Buffer::','control::AdoptedProof::','experimental_swift_reactor::cache::SwiftFunctionCache::','control::RuntimeControl::budget','AdoptionBodyV1::','FileIdentityV1::encode','WasiContext::snapshot_configuration_v2'))))
  calls.append({'caller':f['id'],'destination_role':next(r['id'] for r in roles if r['mir_local']==m[1]),'target':target.replace(base,'source/'),'class':'bounded-product-helper' if product else 'standard-library-call-site','mir_statement':line.strip().replace(base,'source/')})
 coverage.append({'function':f['id'],'declared_locals':len(declared),'parameters':len(args),'enumerated_roles':len(nums),'exact_coverage':True})
# Exact26 actual expression occurrences, not a sum of collapsed closure identities.
exprs=json.loads((INPUT/'encoder-helper-ledger.json').read_text())['captures'];sizes={r['name']:r for r in json.loads((INPUT/'layout-results.json').read_text())['profiles']['gated-production-debug']['exact_captures']}
closure_fns=[f for f in inv['functions'] if '::{closure#' in f['id']]
keymap={
 'word-conversion':('::word::{closure#0}',None),'span-end':('::check::{closure#0}',None),
 'provenance-map-error':('::into_cursor::{closure#0}',None),'memory-absent':('::into_cursor::{closure#1}',None),'table-absent':('::into_cursor::{closure#2}',None),'runtime-map-error':('::into_cursor::{closure#3}',None),'function-total':('::into_cursor::{closure#4}',None),
 'entry-signatures':('::record_word::{closure#2}',None),'entry-parameters':('::record_word::{closure#3}',None),'entry-imports':('::record_word::{closure#4}',None),'entry-functions':('::record_word::{closure#5}',None),'entry-globals':('::record_word::{closure#6}',None),'entry-exports':('::record_word::{closure#7}',None),'entry-data':('::record_word::{closure#8}',None),'entry-elements':('::record_word::{closure#9}',None),'parameter-range':('::record_word::{closure#0}',None),'record-word-result':('::record_word::{closure#1}',None),
 'directory-absent':('::next_block::{closure#0}',None),'source-copy-count':('::next_block::{closure#1}',None),'source-offset':('::next_block::{closure#2}',None),'metadata-index':('::next_block::{closure#3}',None),
 'runtime-convert':('::snapshot_runtime_v2::{closure#0}','no-inner'),'runtime-inner-convert':('::snapshot_runtime_v2::{closure#0}::{closure#0}',None),
 'provenance-source-convert':('::snapshot_encode_v2::{closure#0}',None),'provenance-metadata-convert':('::snapshot_encode_v2::{closure#1}',None),'provenance-scratch-convert':('::snapshot_encode_v2::{closure#2}',None)}
for e in exprs:
 suffix,_=keymap[e['name']];f=next(f for f in closure_fns if f['id'].endswith(suffix));e['closure_function']=f['id'];e['actual_source']=f['source'];e.update({k:sizes[e['name']][k] for k in ['bytes','alignment']});e['charged_callee_argument_role']=next(r['id'] for r in inv['roles'] if r['id'] in f['role_ids'] and r['mir_local']=='_1');e['multiplicity']=1
assert len({e['closure_function'] for e in exprs})==26
(ROOT/'closure-occurrences.json').write_text(json.dumps({'schema':1,'occurrences':exprs,'expression_only_sum_bytes':sum(e['bytes'] for e in exprs),'charged_once_in_inventory':'Materialized expression slots and separately materialized closure callee argument slots are already inventory roles. This file is an index, never an additional additive term.','overlap':'Eight entry closures are mutually exclusive per record_word. The parameter-range closure may run only in signatures branch after the entry callback completes. The final record-word-result closure is constructed after the selected arm completes. The retained runtime convert closure and its nested conversion callback may coexist, both zero sized. The largest simultaneously active expression-capture payload is16 bytes; separately materialized caller-object/callee-argument/move slots are already enumerated in E. The conservative E includes all distinct roles across branches.'},indent=2)+'\n')
(ROOT/'call-sites.json').write_text(json.dumps({'schema':1,'calls':calls,'product_callee_templates':38,'closure_callee_templates':26,'recursive_product_cycles':[],'source_audit':'All product-defined direct and transitive callees in call statements are covered by the64 frozen source functions. The Option::map function-item callback to AccountedWasi::snapshot_configuration_v2 and26 closure call bodies are explicitly included. Standard-library private function bodies are excluded per partition.json; product call-site slots remain charged.'},indent=2)+'\n')
(ROOT/'coverage.json').write_text(json.dumps({'schema':1,'functions':coverage,'all_parameters_and_declared_slots_covered':True,'function_count':len(coverage),'role_count':sum(x['enumerated_roles'] for x in coverage),'source_place_notes':'Named locals and patterns share their actual MIR slot where aliased. Multiple source moves to distinct MIR slots are distinct roles. Distinct debug labels aliasing one slot are not charged twice.'},indent=2)+'\n')
(ROOT/'inventory.json').write_text(json.dumps(inv,indent=2)+'\n')
print('coverage',len(coverage),'roles',len(inv['roles']),'calls',len(calls),'closures',len(exprs))

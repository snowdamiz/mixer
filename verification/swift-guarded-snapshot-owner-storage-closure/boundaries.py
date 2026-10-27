"""Close product call boundaries against owned, accepted encoder, or exact legacy bodies."""
import json,re
from collections import defaultdict
from probe import ROOT,INPUT,ENC,save,sha
from layouts import normalize
from close_recipe import closure_key
raw=json.loads((ROOT/'raw-inventory.json').read_text())
def catalog(text,vm):
 out=[];base=str(vm/'src')+'/'
 for m in re.finditer(r'(?m)^fn .*?\n\}',text,re.S):
  body=m[0];ret=re.search(r'let (?:mut )?_0: .*?;\s*// return place in scope \d+ at '+re.escape(base)+r'([^:]+):(\d+):',body)
  if not ret:continue
  header=body.splitlines()[0];name=header[3:header.index('(')];leaf=name.split('::')[-1]
  # Exact compiler logical body after removing diagnostics-only source spans/comments.
  logical='\n'.join(line.split('//',1)[0].rstrip() for line in body.splitlines())
  logical=logical.replace(base,'source/')
  logical=re.sub(r'<impl at [^>]+>', '<same-source-impl>',logical)
  logical=closure_key(logical,vm)
  logical=re.sub(r'alloc[0-9]+', 'same-immutable-allocation-identity',logical)
  out.append({'name':name.replace(base,'source/'),'leaf':leaf,'path':ret[1],'return_line':int(ret[2]),'header':header.replace(base,'source/'),'logical_mir_sha256':sha(logical.encode()),'body':body})
 return out
current=catalog((ROOT/'owned-work/source-slots.mir').read_text(),INPUT/'source/vm')
old=catalog((ROOT/'owned-work/inherited-slots.mir').read_text(),ROOT.parent/'swift-guarded-snapshot-encoder-implementation/source/vm')
oldhash={f['logical_mir_sha256']:f for f in old}
owned={(f['source']['path'],f['source']['return_line']):f['id'] for f in raw['functions']}
encoder=json.loads((ENC/'inventory.json').read_text())['functions']
enc={(f['source']['path'],f['source']['return_line']):f['id'] for f in encoder}
by=defaultdict(list)
for f in current:by[f['leaf']].append(f)
def leaf(target):
 # Remove nested generic/trait type arguments without truncating function text.
 out='';depth=0
 for c in target:
  if c=='<':depth+=1
  elif c=='>':depth-=1
  elif depth==0:out+=c
 return out.rstrip(':').split('::')[-1]
def path_for(t):
 if any(s in t for s in ('control::','RuntimeControl::','ReservationTicket::','SwiftReservations::')):return 'experimental_swift_reactor/control.rs'
 if t.startswith(('swift::','experimental::swift::','SnapshotBlockV2','SnapshotCursorV2','SnapshotViewV2')) or t=='borrow_snapshot_v2':return 'experimental/swift.rs'
 if t.startswith('experimental::account::'):return 'experimental/account.rs'
 if t.startswith(('accounted::','WasiConstructionPhase::')) or t=='accounted_header_bytes':return 'experimental_wasi/accounted.rs'
 if t.startswith(('experimental_swift_reactor::cache::','construct_snapshot_in_scope_v1')):return 'experimental_swift_reactor/cache.rs'
 if t.startswith(('AdoptionBodyV1::','SelectedSnapshotBodyV1::','SelectedValidatedProfileV1::')):return 'experimental_swift_reactor/retained_profile_loader_v1.rs'
 if t.startswith(('SnapshotScope','SnapshotRun')):return 'experimental_swift_reactor/control.rs'
 if t=='foundation_construction_bytes' or t=='snapshot_scope_candidate_foundation_v1':return 'experimental_swift_reactor/control.rs'
 if t.startswith('header::'):return 'experimental_swift_reactor/cache/initial_profile_v1/header.rs'
 return None
def builtin(t):return t.startswith(('<','Option','Result','std::','core::','Vec::','Instant::','Duration::','Atomic::','Layout::','Arguments::','u64::','usize::','execute::Cancellation::'))
def is_product(t):
 return not builtin(t) and (path_for(t) is not None or t.startswith(('Snapshot','Selected','AdoptionBody')) or t in {'accounted_header_bytes','begin_snapshot_access_v1','checked_add_v1','checked_mul_v1','compare_budget_v1','compare_local_structure_v1','construct_snapshot_owned_v1','inspect_initial_v1','proposed_emission_work_v1','selected_initial_profile_v1','snapshot_shape_v1','write_initial_profile_rows_v1','write_snapshot_v1'}) or t.startswith('construct_profile_core_v1')
bodymap={('owner::'+f['name'],f['path'],f['return_line']):f['body'] for f in current}
callbacks={}
for f in raw['functions']:
 if '{closure#' in f['name']:
  m=re.search(r'\{closure@source/[^}]+\}',f['header'])
  assert m,f['name']
  callbacks[m[0]]=f['id']
calls=[];inherited={};edges=[];unresolved=[]
for f in raw['functions']:
 body=bodymap[(f['id'],f['source']['path'],f['source']['return_line'])]
 for line in body.splitlines():
  m=re.match(r'\s+(_\d+) = (.*?)\(.*\) -> \[return:',line)
  if not m:continue
  target=m[2].replace(str(INPUT/'source/vm/src')+'/','source/');entry={'caller':f['id'],'call_result_role':f['id']+'::'+m[1],'target':target,'source_statement':line.strip().replace(str(INPUT/'source/vm/src')+'/','source/')}
  if target.startswith(('<B as','<P as','<<B as')):
   method=target.split('>::')[-1];matches=[q for q in raw['functions'] if q['name'].endswith('::'+method)]
   entry.update(category='closed-owned-dispatch',callee_role_templates=[q['id'] for q in matches]);assert matches,target
  elif not is_product(target):entry['category']='external-stdlib-or-unchanged-Cancellation-ABI';entry['rule']='actual product call-site slots charged; private std/core bodies and unchanged cancellation helper remain external/inherited'
  else:
   l=leaf(target);matches=by[l];path=path_for(target)
   if path:matches=[q for q in matches if q['path']==path]
   # Distinguish methods with same source file by the concrete receiver in the compiler signature.
   receiver=re.search(r'([A-Z][A-Za-z0-9_]*)(?:::[^:]*)?::',target)
   if receiver and len(matches)>1:
    narrowed=[q for q in matches if receiver[1] in q['header']]
    if narrowed:matches=narrowed
   if len(matches)>1 and len({(q['name'],q['path'],q['return_line']) for q in matches})==1:
    # Const/runtime compiler renderings share the same actual source function.
    exact=[q for q in matches if q['logical_mir_sha256'] in oldhash];matches=(exact or matches)[:1]
   if len(matches)!=1:
    entry.update(category='unresolved',matches=[{k:q[k] for k in ('name','path','return_line')} for q in matches]);unresolved.append(entry)
   else:
    q=matches[0];k=q['path'],q['return_line'];entry['callee']={x:q[x] for x in ('name','path','return_line','logical_mir_sha256')}
    if k in owned:entry.update(category='owned',callee_role_templates=[owned[k]])
    elif k in enc:entry.update(category='accepted-encoder',callee_role_templates=[enc[k]])
    elif q['logical_mir_sha256'] in oldhash:
     o=oldhash[q['logical_mir_sha256']];entry['category']='unchanged-inherited-original-callee';inherited[q['name']]={'current':entry['callee'],'accepted_old':{x:o[x] for x in ('name','path','return_line','logical_mir_sha256')},'rule':'exact identical compiler logical body and concrete signature after diagnostic spans/comments, identical closure-expression source hashes and immutable allocation numbering normalized; original foundation/phase subsystem remains authoritative; no new second charge'}
    else:entry['category']='unresolved-changed-callee';unresolved.append(entry)
  entry['owned_callbacks']=[v for k,v in callbacks.items() if k in target]
  calls.append(entry)
  for callback in entry['owned_callbacks']:edges.append({'from':f['id'],'to':callback,'call_result':entry['call_result_role'],'via':'actual std/direct closure call type'})
  for callee in entry.get('callee_role_templates',[]):edges.append({'from':f['id'],'to':callee,'call_result':entry['call_result_role']})
save(ROOT/'call-boundaries.json',{'schema':1,'calls':calls,'inherited_callees':list(inherited.values()),'edges':edges,'unresolved':unresolved,'external_scope':'No whole-old-engine re-inventory, std/private-library/ABI/unwind/allocator/spill/static-pointee bound. Target Cancellation helper source is unchanged. Three newly owned T helper specializations are charged fully in S rather than assumed size invariant.'})
print('calls',len(calls),'inherited',len(inherited),'unresolved',len(unresolved))
for e in unresolved:print(e['target'],e.get('matches'),e['category'])

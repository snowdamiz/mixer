"""Checked arithmetic closure over enumerated source roles, without runtime execution."""
from pathlib import Path
import json,re,hashlib,sys,platform
from probe import ROOT,INPUT,verify,sha
from measure import normalize
MAX=(1<<64)-1
def checked_add(a,b):
 if not (0<=a<=MAX and 0<=b<=MAX and b<=MAX-a):raise OverflowError('checked u64 source sum')
 return a+b

def closure_layout(t):
 if t.startswith('&'):return (8,8,'sized closure reference; compiler-selected64-bit pointer slot')
 m=re.search(r'/src/([^:]+):(\d+):(\d+):',t);assert m,t
 path,line,col=m[1],int(m[2]),int(m[3])
 if path=='experimental/swift.rs':
  expected={792:(0,1),835:(8,8),936:(0,1),986:(0,1),987:(0,1),1015:(0,1),1035:(0,1),1169:(16,8),1178:(8,8),1257:(16,8),1341:(0,1),1347:(0,1),1349:(0,1),1357:(0,1)}
  assert line in expected,(path,line);size,align=expected[line]
 elif path=='experimental_swift_reactor/cache/initial_profile_v1.rs':assert line==268;size,align=0,1
 elif path=='experimental_swift_reactor/retained_profile_loader_v1.rs':assert line in (1403,1404);size,align=0,1
 else:raise AssertionError((path,line))
 return size,align,'frozen exact26 closure-expression measurements; composition layout-results gated-production-debug'

def close():
 custody=verify();data=json.loads((ROOT/'raw-source-occurrences.json').read_text());req=json.loads((ROOT/'layout-requests.json').read_text());layouts={r['key']:r for r in json.loads((ROOT/'actual-type-layouts.json').read_text())}
 bytype={}
 for r in req:bytype.setdefault(r['compiler_type'],[]).append(layouts[r['key']])
 type_table={};roles=[];functions=[];ids=set();total=0;alignment=1
 for f in data['functions']:
  subtotal=0;functionroles=[]
  for r in f['roles']:
   assert r['id'] not in ids;r['id']=r['id'].replace(str(INPUT/'source/vm/src')+'/', 'source/');ids.add(r['id'])
   t=r['compiler_type']
   if '{closure@' in t:
    size,align,evidence=closure_layout(t);alternatives=[]
   else:
    alternatives=bytype[t];shapes={(x['bytes'],x['alignment']) for x in alternatives};assert len(shapes)==1,(t,shapes);size,align=next(iter(shapes));evidence='actual-type-layouts.json'
   assert size>=0 and align in (1,2,4,8,16) and size%align==0,(t,size,align)
   assert not any(x in r['id'] for x in ['EncoderInitPlaces','EncoderBlockPlaces','EncoderCallerPlaces'])
   key='type-'+sha(t.encode())[:16];type_table.setdefault(key,{'compiler_identity':t.replace(str(INPUT/'source/vm/src')+'/','source/'),'bytes':size,'alignment':align,'layout_evidence':evidence,'actual_instantiations':alternatives})
   r['type_key']=key;r['bytes']=size;r['alignment']=align;r['compiler_type']=type_table[key]['compiler_identity']
   # A move/use is evidence for the existing role. It is never a second charge.
   r['source_uses']=[u.replace(str(INPUT/'source/vm/src')+'/','source/') for u in r['source_uses']]
   r['move_use_count']=sum(len(re.findall(r'\bmove '+re.escape(r['mir_local'])+r'(?!\d)',u)) for u in r['source_uses'])
   r['copy_use_count']=sum(len(re.findall(r'\bcopy '+re.escape(r['mir_local'])+r'(?!\d)',u)) for u in r['source_uses'])
   r['storage_live_count']=sum('StorageLive('+r['mir_local']+')' in u for u in r['source_uses'])
   r['storage_dead_count']=sum('StorageDead('+r['mir_local']+')' in u for u in r['source_uses'])
   if r['kind']=='parameter':
    debugline=next((u for u in f.get('mir','').splitlines() if any('debug '+n+' => '+r['mir_local']+';' in u for n in r['debug_names'])),None)
   subtotal=checked_add(subtotal,size);total=checked_add(total,size);alignment=max(alignment,align);roles.append(r);functionroles.append(r['id'])
  functions.append({'id':f['id'],'header':f['header'].replace(str(INPUT/'source/vm/src')+'/','source/'),'source':f['source'],'role_ids':functionroles,'role_count':len(functionroles),'enumerated_bytes':subtotal,'maximum_simultaneous_invocations':1})
 assert len(functions)==64 and len(roles)==2658
 capture_bodies=[f for f in functions if '::{closure#' in f['id']];assert len(capture_bodies)==26
 captures=json.loads((INPUT/'encoder-helper-ledger.json').read_text())['captures'];assert len(captures)==26
 inherited=json.loads((INPUT/'layout-results.json').read_text())['profiles']['gated-production-debug']['exact_captures'];assert len(inherited)==26
 capturebytes=sum(r['bytes'] for r in inherited);assert capturebytes==160
 # A checked sum of the enumerated role sizes, not identity sizes and not an operational grant.
 result={'schema':1,'source_binding':custody,'scope':'complete bounded product-source callee inventory for the frozen pure encoder and encoding bridges/getters/helpers; source-storage accounting only','formula':'E = checked_u64_fold(0, roles, |sum, role| sum.checked_add(size_of(actual_type(role))))','enumerated_bytes':total,'maximum_alignment':alignment,'role_count':len(roles),'function_count':len(functions),'type_identity_count':len(type_table),'actual_nameable_type_instantiation_measurements':len(layouts),'closures':{'actual_expression_occurrences':26,'macro_entry_occurrences':8,'frozen_expression_only_bytes':160,'not_an_extra_sum_term':'all materialized expression/argument/local roles are already charged in roles; zero-sized expression occurrences remain in closure-occurrences.json'},'multiplicity':'Every unique (function source identity, MIR local) occurs once; loops and repeated calls reuse source templates; disjoint branches and all distinct local/return/move intermediates are conservatively summed. A move operation is linked to its original slot and destination; it is not charged again as an invented copy.','ownership':'Only encoder/bridge/getter/helper callee parameter, return-expression, named-local/pattern and compiler-projected source temporary slots. External owner/payload/caller slots excluded by partition.json.','functions':functions,'types':type_table,'roles':roles,'operational_floor_selected':False,'runtime_executions':0,'physical_stack_or_RSS_bound':False,'product_source_role_omissions':[],'external_dependency_limit':'Standard-library private bodies, allocator/unwind/ABI stacks and backend spills are outside this product-source model. Their product call-site arguments/results/reborrows are represented. No physical-stack or whole-process-storage claim follows.'}
 (ROOT/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
 formula={k:result[k] for k in ['schema','source_binding','formula','enumerated_bytes','maximum_alignment','role_count','function_count','type_identity_count','actual_nameable_type_instantiation_measurements','closures','operational_floor_selected','runtime_executions','physical_stack_or_RSS_bound','product_source_role_omissions','external_dependency_limit']}
 formula['by_function']=[{'id':f['id'],'role_count':f['role_count'],'bytes':f['enumerated_bytes']} for f in functions]
 (ROOT/'formula.json').write_text(json.dumps(formula,indent=2)+'\n')
 print(json.dumps({k:formula[k] for k in ['enumerated_bytes','role_count','function_count','type_identity_count','actual_nameable_type_instantiation_measurements']}))
 return result
if __name__=='__main__':close()

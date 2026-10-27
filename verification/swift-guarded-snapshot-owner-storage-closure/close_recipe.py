"""Checked finite owner/common/selected/phase/host role formulas and inheritance."""
from collections import defaultdict,deque
import copy,json,re
from probe import ROOT,INPUT,ENC,sha,save,verify
from layouts import normalize,instantiate,variants,table,resolve
MAX=(1<<64)-1
def add(a,b):
 assert 0<=a<=MAX and 0<=b<=MAX and b<=MAX-a,'u64 overflow'
 return a+b
def inherited_family(f):
 name=f['name'];p=f['source']['path'];line=f['source']['return_line']
 if p.endswith('control.rs') and ('::adopt_body_core_v1' in name or '::adopt_body' in name or 1837==line):return 'adoption'
 if p.endswith('initial_profile_v1.rs') and name.startswith(('construct_profile_core_v1','construct_with_initial_profile_v1')):return 'constructor'
 if p.endswith('retained_profile_loader_v1.rs') and (name.endswith('::adopt') or line==169):return 'selected-carrier-original-adopt'
 return None
def closure_key(t,vm):
 def replace(m):
  path,line,col,end,endcol=m[1],int(m[2]),int(m[3]),int(m[4]),int(m[5]);ls=(vm/'src'/path).read_text().splitlines()[line-1:end]
  if len(ls)==1:text=ls[0][col-1:endcol-1]
  else:ls[0]=ls[0][col-1:];ls[-1]=ls[-1][:endcol-1];text='\n'.join(ls)
  return '{closure-source:'+sha(re.sub(r'\s+','',text).encode())+'}'
 return re.sub(r'\{closure@source/([^:]+):(\d+):(\d+): (\d+):(\d+)\}',replace,t)
def key(f,r,vm):
 family=inherited_family(f)
 if not family:return None
 t=closure_key(instantiate(r['compiler_type'],'original'),vm)
 kind=r['kind'];names=','.join(r['debug_names'])
 if kind=='return-expression':extra='return'
 elif kind=='parameter':extra='parameter:'+names
 elif names:extra='named:'+names
 else:extra='expression:'+re.sub(r'\s+','',r['source_text'])
 return family,kind,t,extra
def measured_type(t,prod,unit):
 base=resolve(t,prod);key=normalize(t);other=unit.get(key)
 if other:
  size=max(base['bytes'],other['bytes']);align=max(base['alignment'],other['alignment'])
  return {'bytes':size,'alignment':align,'production':base,'unit':other,'rule':'maximum actual layout over production and unit source contexts'}
 return {**base,'production':base,'unit':None,'rule':'target-invariant base/reference/function-item/array or exact anonymous capture; no cfg-dependent owned capture'}
def close():
 custody=verify();raw=json.loads((ROOT/'raw-inventory.json').read_text());prod=table();unit={normalize(r['compiler_type']):r for r in json.loads((ROOT/'unit-type-layouts.json').read_text())}
 oldvm=ROOT.parent/'swift-guarded-snapshot-encoder-implementation/source/vm';pools=defaultdict(deque)
 for f in raw['baseline_functions']:
  for r in f['roles']:pools[key(f,r,oldvm)].append(r)
 pools.pop(None,None)
 roles=[];inheritance=[];types={};functions=[]
 # Relocated original core consumes inherited slots before newly introduced adapters.
 fs=sorted(raw['functions'],key=lambda f:(0 if f['funding_class'].startswith('shared-') else 1))
 for f in fs:
  ids=[];subtotal=0
  for original in f['roles']:
   r=copy.deepcopy(original);layouts=[]
   for profile,T,t in variants(f,r):
    lay=measured_type(t,prod,unit);layouts.append({'profile':profile,'T':T,'actual_type':t,**lay});types.setdefault(t,lay)
   original_shapes=[x for x in layouts if x['profile']=='original'];selected_shapes=[x for x in layouts if x['profile']=='selected']
   shape=max(layouts,key=lambda x:x['bytes']);r.update({'bytes':shape['bytes'],'alignment':max(x['alignment'] for x in layouts),'actual_variants':layouts})
   cls=f['funding_class'];inherited=None
   # The ordinary ABI adapter is new; only the relocated core and the moved refund/body logic may reuse old slots.
   eligible=cls.startswith('shared-') or (f['source']['path'].endswith('control.rs') and f['source']['return_line']==1837) or (f['source']['path'].endswith('retained_profile_loader_v1.rs') and f['source']['return_line'] in (165,169))
   k=key(f,r,INPUT/'source/vm') if eligible else None
   if k is not None and pools[k]:
    old=pools[k].popleft();inherited={'old_id':old['id'],'old_source':old['source'],'old_source_member_sha256':old['source_member_sha256'],'alias_rule':'same bounded logical source core, exact concrete type and return/parameter/debug binding or normalized expression identity'}
   charges={'common-extra':0,'selected-unconditional':0,'admitted-only':0}
   if cls in ['shared-adoption','shared-constructor']:
    ob=max(x['bytes'] for x in original_shapes);sb=max(x['bytes'] for x in selected_shapes)
    if not inherited:charges['common-extra']=ob
    charges['selected-unconditional']=max(0,sb-ob)
   elif cls=='common':
    if not inherited:charges['common-extra']=r['bytes']
   else:charges[cls]=r['bytes']
   r['funding']=charges;r['inherited_alias']=inherited;r['template']=f['id']
   r['lifetime_assignment']='initial common foundation' if cls=='common' or cls.startswith('shared-') else 'admitted phase until writer/helper calls end, then actual typed phase completion' if cls=='admitted-only' else 'selected pre-Construction foundation through actual returned diagnostic destruction; no healthy narrowing'
   if inherited:inheritance.append({'new_id':r['id'],**inherited})
   roles.append(r);ids.append(r['id']);subtotal=add(subtotal,sum(charges.values()))
  functions.append({'id':f['id'],'source':f['source'],'funding_class':f['funding_class'],'role_ids':ids,'role_count':len(ids),'additional_bytes':subtotal,'generic_rule':'one source template; closed profiles or actual normalizer type alternatives measured; maximum per source role; no recursive helper invocation'})
 # Exact host caller: all source slots classified, harness machinery remains explicit.
 host=copy.deepcopy(raw['host_caller']);htotal=0
 for r in host['roles']:
  if r['funding_class']=='host-caller':
   t=instantiate(r['compiler_type'],'selected');lay=measured_type(t,prod,unit);r.update({'bytes':lay['bytes'],'alignment':lay['alignment'],'layout':lay,'actual_type':t});htotal=add(htotal,r['bytes']);types.setdefault(t,lay)
 # Encoder functions reused by pregrant owner pairing are moved to unconditional funding, not added twice.
 enc=json.loads((ENC/'inventory.json').read_text());es=0;ea=0;ejoins=[]
 for f in enc['functions']:
  before=(f['id'].endswith('::proof') or f['id'].endswith('::budget') or (f['source']['path']=='experimental/account.rs' and f['id'].endswith('::len')))
  category='selected-unconditional' if before else 'admitted-only'
  if before:es=add(es,f['enumerated_bytes'])
  else:ea=add(ea,f['enumerated_bytes'])
  ejoins.append({'encoder_function_id':f['id'],'role_ids':f['role_ids'],'bytes':f['enumerated_bytes'],'funding_class':category,'reason':'reachable before grant through cache/adopted/body proof pairing or original budget read' if before else 'encoder/encoding-bridge/opaque block getter only after actual writer admission'})
 assert es+ea==40531
 totals={c:0 for c in ['common-extra','selected-unconditional','admitted-only']}
 for r in roles:
  for c,n in r['funding'].items():totals[c]=add(totals[c],n)
 owner_totals=dict(totals);totals['selected-unconditional']=add(totals['selected-unconditional'],es);totals['admitted-only']=add(totals['admitted-only'],ea)
 result={'schema':1,'source_binding':custody,'functions':functions,'roles':roles,'types':types,'role_count':len(roles),'function_count':len(functions),'owner_only_formulas':owner_totals,'encoder_join':{'unconditional_bytes':es,'admitted_only_bytes':ea,'total':40531,'functions':ejoins,'rule':'exact partition replacement, no EncoderInit/Block/Caller or identity-size aggregate added'},'formulas':totals,'host_caller_bytes':htotal,'all_loop_multiplicities':1,'physical_stack_or_RSS_claim':False,'operational_floor_selected':False,'runtime_executions':0}
 save(ROOT/'inventory.json',result);save(ROOT/'inherited-aliases.json',{'schema':1,'aliases':inheritance,'retained_unused_legacy_slots':[r for q in pools.values() for r in q],'rule':'one-to-one matching of existing bounded original source roles; unmatched old roles remain covered conservatively by unchanged legacy floor and are never subtracted'})
 save(ROOT/'host-caller.json',{'schema':1,'function':host,'enumerated_product_bytes':htotal,'all_roles_classified':True,'outer_getter_calls':1,'optional_wasi_paths':['None','Some(actual budget/grants and retained attachment result)'],'runtime_dispatched':False,'production_caller_integrated':False})
 save(ROOT/'formula.json',{'schema':1,'role_count':len(roles),'function_count':len(functions),'common_extra':totals['common-extra'],'selected_unconditional_extra':totals['selected-unconditional'],'admitted_only_extra':totals['admitted-only'],'host_caller_extra':htotal,'owner_only':owner_totals,'encoder_unconditional':es,'encoder_admitted_only':ea,'definition':'Each term is a checked u64 fold of unique concrete source roles; shared Original/Selected representation growth and one-to-one inherited original aliases are explicit. Actual normalizer generic alternatives use maximum per role. Loops reuse each role.','initial_common_recipe':'F_common = checked_add(existing sole Original foundation, C)','selected_initial_recipe':'F_selected = checked_add(F_common, S); concrete next host additionally prefunds H','admitted_recipe':'F_phase = checked_add(F_selected [+H for concrete host], A)','retirement_rule':'Keep selected charge and actual diagnostics through final return/caller destruction; no narrowing or healthy finish is selected','complete_for_frozen_owner_scope':True,'production_caller_integration_pending':True,'operational_selection':False})
 print(json.dumps({'roles':len(roles),'functions':len(functions),'inherited_aliases':len(inheritance),'formulas':totals,'host':htotal,'encoder_S':es,'encoder_A':ea}))
 return result
if __name__=='__main__':close()

"""Host-only custody, omission, multiplicity, partition and arithmetic controls."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import json,re,sys,platform,hashlib,copy
from probe import ROOT,INPUT,ENC,verify,sha
from close_inventory import checked_add,closure_layout

def need(ok,label):
 if not ok:raise AssertionError(label)
def rejected(fn):
 try:fn()
 except (AssertionError,KeyError,OverflowError):return True
 return False

def validate(j):
 roles=j['roles'];need(len(roles)==2658,'exact role cardinality');need(len({r['id'] for r in roles})==len(roles),'duplicate role ID')
 types=j['types'];total=0
 for r in roles:
  t=types[r['type_key']];need((r['bytes'],r['alignment'])==(t['bytes'],t['alignment']),'layout mismatch')
  need(r['multiplicity']==1,'loop multiplied source slot');total=checked_add(total,r['bytes'])
 need(total==j['enumerated_bytes']==40531,'checked sum');need(j['operational_floor_selected'] is False,'no operational selection')
 need(not any(r['compiler_type']=='[u8; 4096]' for r in roles),'external transfer owner copied')
 need(not any('EncoderInitPlaces' in r['compiler_type'] or 'EncoderBlockPlaces' in r['compiler_type'] or 'EncoderCallerPlaces' in r['compiler_type'] for r in roles),'aggregate/role double counting')
 return total

def callgraph(j):
 fns=j['functions'];graph={f['id']:set() for f in fns};calls=json.loads((ROOT/'call-sites.json').read_text())['calls']
 def match(ends,path=None,impl=None):
  fs=[f for f in fns if f['id'].endswith('::'+ends) and (path is None or f['source']['path']==path) and (impl is None or impl in f['id'])]
  need(len(fs)==1,('callee resolution',ends,path,impl,len(fs)));return fs[0]['id']
 for c in calls:
  if c['class']!='bounded-product-helper':continue
  t=c['target'];method=t.split('::')[-1];path=None;impl=None
  if t.startswith('experimental::account::Buffer::'):path='experimental/account.rs'
  elif t.startswith(('snapshot_encoder_v2::','SnapshotViewV2::','SpanCheckV2::')) or t in ['field','require','put','optional','result_id','wasi_id','validate_runtime']:path='experimental/swift.rs'
  elif t.startswith('initial_profile_v1::'):path='experimental_swift_reactor/cache/initial_profile_v1.rs'
  elif t.startswith('LoaderProvenanceV1::') or t.startswith(('AdoptionBodyV1::','FileIdentityV1::')):
   path='experimental_swift_reactor/retained_profile_loader_v1.rs';impl=':146:' if t.startswith('AdoptionBodyV1::') else None
  elif t.startswith('control::AdoptedProof::'):path='experimental_swift_reactor/control.rs';impl=':350:'
  elif t.startswith('control::RuntimeControl::'):path='experimental_swift_reactor/control.rs';impl=':590:'
  elif t.startswith('experimental_swift_reactor::cache::'):path='experimental_swift_reactor/cache.rs'
  elif t.startswith('WasiContext::'):path='experimental_wasi/mod.rs'
  else:raise AssertionError(('unresolved product target',t))
  graph[c['caller']].add(match(method,path,impl))
 for f in fns:
  if '::{closure#' in f['id']:
   parent=f['id'].rsplit('::{closure#',1)[0];need(parent in graph,'closure parent');graph[parent].add(f['id'])
  if f['id'].endswith('::snapshot_runtime_v2'):
   graph[f['id']].add(match('snapshot_configuration_v2','experimental_wasi/accounted.rs'))
 active=set();done=set()
 def visit(n):
  need(n not in active,'recursive product source dependency')
  if n in done:return
  active.add(n)
  for child in graph[n]:visit(child)
  active.remove(n);done.add(n)
 for n in graph:visit(n)
 return {k:sorted(v) for k,v in graph.items()}

if __name__=='__main__':
 custody=verify();j=json.loads((ROOT/'inventory.json').read_text());total=validate(j);graph=callgraph(j)
 source_a=(ENC/'host/encoder.rs').read_text().splitlines(keepends=True)[:643];source_b=(INPUT/'source/vm/src/experimental/swift.rs').read_text().splitlines(keepends=True)[731:1374];need(source_a==source_b,'frozen643 encoder behavior lines')
 coverage=json.loads((ROOT/'coverage.json').read_text());need(all(x['exact_coverage'] for x in coverage['functions']) and coverage['role_count']==2658,'all declared/parameter slots')
 cl=json.loads((ROOT/'closure-occurrences.json').read_text());need(len(cl['occurrences'])==26 and len([e for e in cl['occurrences'] if e['name'].startswith('entry-')])==8,'exact macro expression multiplicity');need(cl['expression_only_sum_bytes']==160,'capture expression evidence')
 controls={}
 bad=copy.deepcopy(j);bad['roles'][1]['id']=bad['roles'][0]['id'];controls['duplicate_source_role_rejected']=rejected(lambda:validate(bad))
 bad=copy.deepcopy(j);del bad['types'][bad['roles'][0]['type_key']];controls['missing_actual_type_rejected']=rejected(lambda:validate(bad))
 bad=copy.deepcopy(j);bad['roles'][0]['multiplicity']=9;controls['record_or_loop_multiplication_rejected']=rejected(lambda:validate(bad))
 bad=copy.deepcopy(j);bad['roles'].pop();controls['omitted_role_rejected']=rejected(lambda:validate(bad))
 bad=copy.deepcopy(j);bad['enumerated_bytes']+=1;controls['changed_formula_rejected']=rejected(lambda:validate(bad))
 controls['checked_u64_overflow_rejected']=rejected(lambda:checked_add((1<<64)-1,1))
 controls['unknown_closure_dependency_rejected']=rejected(lambda:closure_layout('{closure@/src/unknown.rs:999:1: 999:2}'))
 need(all(controls.values()),'negative controls')
 graph_result={'schema':1,'nodes':graph,'acyclic':True,'function_count':len(graph),'source_template_maximum_simultaneous_invocations':1,'standard_library_private_frames_included':False}
 need(json.loads((ROOT/'product-callgraph.json').read_text())==graph_result,'frozen callgraph reproducibility')
 result={'schema':1,'command':[sys.executable,str(Path(__file__).resolve())],'python_version':platform.python_version(),'source_binding':custody,'checked_enumerated_bytes':total,'exact_source_role_coverage':True,'encoder_behavior643_lines_byte_identical':True,'encoder_behavior_sha256':sha(''.join(source_a).encode()),'complete_product_source_callgraph':True,'product_source_function_count':64,'roles':2658,'negative_controls':controls,'passed':True,'runtime_executions':0,'scope':'host Python custody/source projection/arithmetic validation only; no encoder/VM/writer/native/device/simulator/emulator/UI/capture/process inventory'}
 need(json.loads((ROOT/'checks.json').read_text())==result,'frozen check result reproducibility');print(json.dumps(result))

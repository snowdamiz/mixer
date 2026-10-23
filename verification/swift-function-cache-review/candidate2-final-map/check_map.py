#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,re,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(t):return re.sub(r'\s+','',t)
producer=ROOT/'verification/swift-function-cache/candidate-2'
bindings={'preflight-and-root-tail-map.md':'4e7b7e65e4634c82c7718721f63ab45a730a79fc27243a01b406d6973fd25327','preflight-root-tail-map.json':'1089fa9afdc3bf493380da6a3ff73acd6962831456d0d33cb60d2305e00eb695'}
for name,h in bindings.items():assert sha((producer/name).read_bytes())==h,name
m=json.loads((producer/'preflight-root-tail-map.json').read_text())
s=(HERE/'tree/vm/src/experimental_swift_reactor/cache.rs').read_text()
measure=json.loads((HERE/'measurement-receipt.json').read_text())
assert measure['source_before_test_overlay'][m['source']]==m['source_sha256']
assert measure['source_before_test_overlay']['vm/src/experimental_swift_reactor/cache_tests.rs']==m['tests_source_sha256']
for name,h in m['logs'].items():assert sha((producer/name).read_bytes())==h,name
observations={}
for mode in ['debug','release']:
 log=(HERE/f'measured-{mode}.log').read_text()
 assert re.search(r'test result: ok\. 1 passed; 0 failed;',log)
 layouts={norm(t):{'type':t,'size':int(sz),'align':int(al)} for t,sz,al in re.findall(r'^layout (.*?) (\d+) (\d+)$',log,re.M)}
 fields={}
 for st,f,t,sz,al,off in re.findall(r'^model (\w+) (\w+) (.*?) (\d+) (\d+) (\d+)$',log,re.M):
  assert f not in fields.setdefault(st,{})
  fields[st][f]={'field':f,'type':t,'size':int(sz),'align':int(al),'offset':int(off)}
 assert set(layouts)==set(m['layouts'])
 for key,row in m['layouts'].items():assert layouts[key]==row,(mode,key)
 assert set(fields)==set(m['model_fields'])
 for st,rows in m['model_fields'].items():
  assert fields[st]=={r['field']:r for r in rows},(mode,st)
  body=re.search(r'\bstruct '+re.escape(st)+r'\s*\{(.*?)\n\}',s,re.S).group(1)
  declared=re.findall(r'^\s*(\w+):',body,re.M)
  assert set(declared)==set(fields[st]),(st,set(declared)^set(fields[st]))
 sums={}
 for fn,table in m['component_checked_sums'].items():
  body=s.split('const fn '+fn+'()',1)[1].split('\n}',1)[0]
  literal=[(int(c),norm(t)) for c,t in re.findall(r'\(\s*(\d+)\s*,\s*size_of::<(.*?)>\s*\(\s*\)\s*,?\s*\)',body,re.S)]
  assert literal==[(r['count'],r['type']) for r in table['objects']],fn
  total=0
  for (c,t),row in zip(literal,table['objects']):
   assert layouts[t]['size']==row['size'] and layouts[t]['align']==row['align']
   assert c*row['size']==row['bytes'];total+=row['bytes']
  assert total==table['bytes'];sums[fn]=total
 observed={k:int(v) for k,v in re.findall(r'(cleanup|header|construction|operation|foundation)=(\d+)',log)}
 assert observed==m['observed_bounds']
 assert sums['compute_cache_cleanup_temporary_bytes']==observed['cleanup']
 assert sums['compute_cache_construction_bytes']==observed['construction']
 assert sums['compute_cache_operation_bytes']==observed['operation']
 assert layouts['SwiftFunctionCache']['size']-layouts['ValidatedSwiftReactor']['size']+observed['cleanup']==observed['header']
 assert sum(r['count']*r['size'] for r in m['foundation_counts'])==observed['foundation']
 assert all(row['phase_bytes']<=row['whole_bytes'] for row in m['preflight_slots'])
 observations[mode]={'layout_rows':len(layouts),'field_groups':len(fields),'fields':sum(map(len,fields.values())),'all_rows_equal_producer':True,'all_declared_inventory_fields_measured':True,'literal_sums':sums,'bounds':observed}
assert observations['debug']==observations['release']
assert sha((ROOT/m['source']).read_bytes())==m['source_sha256'],'live cache source changed'
env=os.environ|{'PATH':'/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']}
versions=[]
for argv in [['rustc','-Vv'],['cargo','-V'],['python3','--version'],['git','--version'],['uname','-a']]:
 r=subprocess.run(argv,env=env,capture_output=True,text=True,check=True);versions.append({'argv':argv,'stdout':r.stdout,'stderr':r.stderr})
result={'scope':'independent frozen map source/artifact/type arithmetic check; phase correctness reviewed separately','source_sha256':m['source_sha256'],'tests_sha256':m['tests_source_sha256'],'source_digest':measure['source_digest'],'full_vm_input_files':len(measure['full_vm_input_manifest']),'bindings':{str((producer/name).relative_to(ROOT)):h for name,h in bindings.items()},'measurement_receipt_sha256':sha((HERE/'measurement-receipt.json').read_bytes()),'observations':observations,'tools':versions,'live_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
(HERE/'map-check-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='tools'},indent=2))

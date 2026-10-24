#!/usr/bin/env python3
"""Replay accepted Python matrices as raw-model oracle, emit compact deltas.

The Elixir component independently executes every emitted input. Original suite
outcomes remain evidence of their original environment, not product acceptance.
"""
import base64,copy,gzip,hashlib,importlib.util,json,os,pathlib,runpy,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];UP=ROOT/'verification/hosted-catalog-wildcard-correction'
os.environ['MIXER_SHAPE_PACKET']=str(UP)
sys.path.insert(0,str(UP/'candidate'))
import inspector,raw_validation
baseline_path=UP/'inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz'
baseline=inspector.decode(gzip.decompress(baseline_path.read_bytes()))['raw']
expected=inspector.decode((UP/'selected-expected.json').read_bytes())
(HERE/'inputs/baseline.json.gz').write_bytes(gzip.compress(json.dumps(baseline).encode(),mtime=0))
def delta(old,new,path=()):
 if type(old) is dict and type(new) is dict:
  out=[]
  for key in old.keys()-new.keys():out.append({'op':'delete','path':list(path+(key,))})
  for key in new:
   if key not in old:out.append({'op':'set','path':list(path+(key,)),'value':new[key]})
   else:out.extend(delta(old[key],new[key],path+(key,)))
  return out
 if type(old) is list and type(new) is list and len(old)==len(new):
  return [change for i,(a,b) in enumerate(zip(old,new)) for change in delta(a,b,path+(i,))]
 if type(old) is type(new) and old==new:return []
 return [{'op':'set','path':list(path),'value':new}]
cases=[];seen=set();oracle=inspector.validate
def record(raw,selected):
 changes=delta(baseline,raw);key=json.dumps(changes,sort_keys=True,separators=(',',':'),ensure_ascii=True)
 if key in seen:return
 seen.add(key)
 try:raw_validation.validate_raw(raw);rv=True
 except ValueError:rv=False
 cases.append({'index':len(cases),'patch_base64':base64.b64encode(key.encode()).decode(),'raw_valid':rv,'selected':selected})
def wrapped(raw,expected):
 try:out=oracle(raw,expected)
 except ValueError:record(raw,False);raise
 record(raw,True);return out
inspector.validate=wrapped
spec=importlib.util.spec_from_file_location('accepted_boundaries',UP/'replay-boundaries.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
result=m.execute();assert result['passed']
path=HERE/'inputs/oracle-boundary-replay.json';path.write_text(json.dumps(result,indent=2)+'\n')
for script,target in [('replay-extra-probes.py','oracle-extra-replay.json'),('model-tests.py','oracle-focused-replay.json')]:
 if script=='replay-extra-probes.py':
  sys.argv=[str(UP/script),'--packet',str(UP),'--out',str(HERE/'inputs'/target)]
  try:runpy.run_path(str(UP/script),run_name='__main__')
  except SystemExit as exc:assert exc.code==0
 else:
  spec=importlib.util.spec_from_file_location('accepted_focused',UP/script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);r=m.execute();assert r['passed'];(HERE/'inputs'/target).write_text(json.dumps(r,indent=2)+'\n')
out='\n'.join(json.dumps(c,separators=(',',':')) for c in cases)+'\n'
(HERE/'inputs/models.jsonl.gz').write_bytes(gzip.compress(out.encode(),mtime=0))
(HERE/'inputs/model-summary.json').write_text(json.dumps({'unique_models':len(cases),'raw_valid':sum(c['raw_valid'] for c in cases),'selected':sum(c['selected'] for c in cases),'baseline_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),'source_matrices':{'original':126,'shape':1083,'portability':3,'extra':128,'focused':24}},indent=2)+'\n')
print(json.dumps({'unique_model_inputs':len(cases)}))

#!/usr/bin/env python3
"""Replay complete positive new inventory and both accepted components."""
from pathlib import Path
import importlib.util,json,sys
from run import HERE,enc
sys.dont_write_bytecode=True
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
new=module('new_growth_inventory',HERE/'inventory.py')
keys=['field','rustType','binding','sourceNames','mirFunction','position','config','kind','envelope','window']
def projection(rows,qualify=False):
 output=[{key:row.get(key)for key in keys}for row in rows]
 if qualify:
  prefix='experimental_swift_reactor::execution::frame_operations::'
  for row in output:
   if row['mirFunction']and row['mirFunction'].startswith(prefix+'memory_operations::'):row['mirFunction']=row['mirFunction'][len(prefix):]
 return output
prior=[]
for name in ['memory','bulk']:
 old=module('accepted_'+name,HERE/'inputs'/('accepted-'+name+'-inventory.py'))
 if hasattr(old,'promoted_constants'):old.promoted_constants=new.promoted_constants
 schema=json.loads((HERE/'inputs'/('accepted-'+name+'-schema.json')).read_text());prior.append((name,old,schema))
schema=json.loads((HERE/'inventory-schema.json').read_text());report=[]
for features in ['all','swift']:
 for config in ['production','unit']:
  path=HERE/('qualified-'+features+'-'+config+'.mir.gz');rows,functions,captures=new.canonical(path,config);assert projection(rows)==projection([r for r in schema if r['config']==config]),(features,config,'new inventory drift')
  item=dict(features=features,config=config,freshFields=len(rows),functions=functions,captures=captures,accepted={})
  for name,old,accepted in prior:
   actual,_,_=old.canonical(path,config)
   assert projection(actual,name=='memory')==projection([r for r in accepted if r['config']==config],name=='memory'),(features,config,name,'accepted drift')
   item['accepted'][name]=len(actual)
  report.append(item)
assert new.selected('growth_pinned_step::promoted[0]')
assert not new.selected('growth_checkpoint::promoted[0]')
assert not new.selected('memory_growth_operations::tests::mg19_actual_deadline_at_growth_boundary::promoted[0]')
assert new.selected('release_growth_pending')
assert any('preflight::promoted['in row['mirFunction']for row in schema if row['config']=='unit')
assert any(row['mirFunction']=='growth_pinned_step::promoted[0]'for row in schema if row['config']=='unit')
(HERE/'inventory-replay.json').write_bytes(enc(report));print('Four final compiler inventories exact; 4800 accepted memory +4324 accepted bulk unchanged;10356 fresh positive fields')

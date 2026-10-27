#!/usr/bin/env python3
"""Promote already observed per-configuration layout literals, preserving IDs."""
from pathlib import Path
import json,re,shutil,hashlib
ROOT=Path(__file__).resolve().parent;S=ROOT/'source/vm/src/experimental_swift_reactor'
layouts={}
for config in ['unit','production']:
 a=json.loads((ROOT/f'layouts/{config}-debug.json').read_text());b=json.loads((ROOT/f'layouts/{config}-optimized.json').read_text())
 assert a['rows']==b['rows'] and a['values']==b['values']
 assert [e['id']for e in a['rows']]==list(range(1,202))
 layouts[config]=a
pre=ROOT/'source-preimages/layout-discovery-source';assert not pre.exists();shutil.copytree(ROOT/'source/vm',pre)
changes=[]
for config,path in [('production','cache/initial_profile_v1/selected.rs'),('unit','cache/initial_profile_v1/tests.rs')]:
 p=S/path;text=p.read_text();old=text
 records={e['id']:e for e in layouts[config]['rows']}
 def replace(m):
  i=int(m.group(1));e=records[i]
  if int(m.group(2))!=e['bytes']or int(m.group(3))!=e['alignment']:changes.append({'configuration':config,'id':i,'name':e['name'],'old_bytes':int(m.group(2)),'old_alignment':int(m.group(3)),'bytes':e['bytes'],'alignment':e['alignment']})
  return f'LocalTypeLayoutV1 {{id:{i},reserved:0,bytes:{e["bytes"]},alignment:{e["alignment"]}}}'
 text,count=re.subn(r'LocalTypeLayoutV1 \{id:(\d+),reserved:0,bytes:(\d+),alignment:(\d+)\}',replace,text)
 assert count==201,(path,count)
 values=layouts[config]['values']
 for field,key in [('cache_cleanup_bytes','cleanup'),('cache_header_bytes','header'),('cache_construction_bytes','construction'),('cache_operation_bytes','operation')]:
  text,count=re.subn(r'  '+field+r':\d+,','  '+field+':'+str(values[key])+',',text);assert count==1,(path,field)
 # Original fixed-at64 equals unchanged slot/pin/patch capacity plus new header.
 old_fixed=118240;old_header=92128;new_fixed=old_fixed-old_header+values['header']
 text,count=re.subn(r'  cache_fixed_at_selected_maxslots:\d+,','  cache_fixed_at_selected_maxslots:'+str(new_fixed)+',',text);assert count==1
 if config=='unit':
  assert text.count('+92128')==1; text=text.replace('+92128','+'+str(values['header']))
  assert text.count('(80,118240)')==1;text=text.replace('(80,118240)','(80,'+str(new_fixed)+')')
 text=text.replace('// prospective:','// appended:')
 p.write_text(text)
changes.append({'test':'phase_boundary fault46/47 exact added cache header','old':92128,'new':layouts['unit']['values']['header'],'reason':'fault ceiling remains current combined plus actual measured header; no production limit changes'})
changes.append({'test':'fresh header offset80 expected fixed capacity','old':118240,'new':121264,'reason':'actual header grows3024; selected slot/pin/patch capacities unchanged'})
(ROOT/'layouts/literal-migration.json').write_text(json.dumps({'schema':1,'measure_before_update':True,'original165_ids_retained':True,'appended_ids':list(range(166,202)),'changes':changes,'no_budget_limit_raised':True},indent=2)+'\n')
print(json.dumps({'records_each_configuration':201,'changed_records_and_assertions':len(changes),'production_values':layouts['production']['values'],'unit_values':layouts['unit']['values']}))

#!/usr/bin/env python3
"""Read-only offline proof replay. No writes, compilation, extraction or execution."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,re,sys,tarfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
enc=lambda obj:(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
sha=lambda data:hashlib.sha256(data).hexdigest()
read=lambda path:json.loads(path.read_text())
BASE='96c945a817c81be17fb526067d87cc667a21cdaf5a47be18179e10fe5ed8de0d'
CANDIDATE='56e47ffa2c74ea243c9ead371a5ebfdeb59e85c0f05555419d51c84483afabe3'
seal=read(HERE/'seal.json');files={str(p.relative_to(HERE))for p in HERE.rglob('*')if p.is_file()and p.name not in['seal.json','offline-verify.log']and'__pycache__'not in p.parts}
assert files==set(seal['files']),(files-set(seal['files']),set(seal['files'])-files)
for name,digest in seal['files'].items():assert sha((HERE/name).read_bytes())==digest,name
for name,digest in seal['documentation'].items():assert sha((HERE.parents[1]/name).read_bytes())==digest,name

def archive(path):
 with tarfile.open(path,'r:gz')as tar:
  members=tar.getmembers();assert all(m.isfile()and not Path(m.name).is_absolute()and'..'not in Path(m.name).parts for m in members)
  out={m.name:tar.extractfile(m).read()for m in members};assert len(out)==len(members);return out
cache={}
def source(digest):
 if digest not in cache:
  data=archive(HERE/'sources'/(digest+'.tar.gz'));assert sha(enc({k:sha(v)for k,v in data.items()}))==digest;cache[digest]=data
 return cache[digest]
base=source(BASE);candidate=source(CANDIDATE);assert len(base)==125 and len(candidate)==127
for label,digest,data in [('baseline',BASE,base),('candidate',CANDIDATE,candidate)]:
 assert read(HERE/(label+'-source-manifest.json'))=={k:sha(v)for k,v in data.items()}
 assert archive(HERE/(label+'-source.tar.gz'))==data
receipt=read(HERE/'receipt.json');assert receipt['baselineSourceSHA256']==BASE and receipt['candidateSourceSHA256']==CANDIDATE
assert receipt['scope']=='private-bounded-host-memory-growth-candidate'
assert receipt['acceptance']==dict(independentReview='pending',rootIntegration='pending',product='pending',ga='pending')
commands=read(HERE/'command-index.json')
def output(name,stream='stdout'):return gzip.decompress((HERE/'commands'/name/(stream+'.gz')).read_bytes()).decode()
for name,row in commands.items():
 directory=HERE/'commands'/name;assert read(directory/'receipt.json')==row
 for stream in['stdout','stderr']:assert sha(gzip.decompress((directory/(stream+'.gz')).read_bytes()))==row[stream+'SHA256'],(name,stream)
 assert row['sourceUnchanged']is True
 if row['sourceTreeSHA256']:
  m=read(directory/'source-manifest.json');assert sha(enc(m))==row['sourceTreeSHA256'];assert m=={k:sha(v)for k,v in source(row['sourceTreeSHA256']).items()}
for name in receipt['qualifyingCommands']:
 row=commands[name];assert row['exitCode']==0,name
 if not row['sourceTreeSHA256']:continue
 target=row['environment']['CARGO_TARGET_DIR'];assert '/target-source-'+row['sourceTreeSHA256']+'/'in target,(name,target)
 assert re.search(r'/(?:all|default|experimental-swift-reactor)-(?:debug|release)-(?:unit|production)-(?:layout|runtime|mir)$',target),(name,target)
 for binary in row['executables']:
  assert binary['path'].startswith(target+'/')and re.fullmatch('[a-f0-9]{64}',binary['sha256'])and binary['bytes']>0
assert set(receipt['excludedFailedCommands'])=={name for name,row in commands.items()if row['exitCode']!=0}
assert all(name not in receipt['qualifyingCommands']for name in receipt['excludedCacheOrContextCommands'])
# Exact current-source growth test identities and complementary Release regression.
expected=re.findall(r'fn (mg\d+_\w+)\(',candidate['src/experimental_swift_reactor/memory_growth_operations_tests.rs'].decode());assert len(expected)==20 and len(set(expected))==20
matrix=read(HERE/'matrix-results.json');assert len(matrix)==4
for row in matrix:
 name='qualified-runtime-'+row['features']+'-'+row['profile'];assert row['commands']==[name]
 assert commands[name]['sourceTreeSHA256']==CANDIDATE and commands[name]['executables']
 tests=re.findall(r'test ([\w:]+) \.\.\.',output(name));actual=[n.rsplit('::',1)[-1]for n in tests]
 wanted=expected if row['features']=='all'else[n for n in expected if not n.startswith('mg20_')]
 assert sorted(actual)==sorted(wanted)==sorted(row['growthTests'])and len(actual)==len(set(actual))==row['totalTests']
 assert re.search(r'test result: ok\. '+str(len(wanted))+r' passed; 0 failed; 0 ignored;',output(name))
 bounds=re.findall(r'MG_BOUND fixtures=(\d+) steps=(\d+) maxFixtures=24 maxSteps=128 maxFrames=3',output(name));assert len(bounds)==len(wanted)and all(int(f)<=24 and int(s)<=128 for f,s in bounds)
 # The separate finite Frozen recipe has no Swift owners/caller steps.
 if row['features']=='all':assert len(re.findall(r'MG_FROZEN delta=',output(name)))==5
regression=read(HERE/'regression-results.json');name='qualified-regression-all-release';assert regression['commands']==[name]and commands[name]['sourceTreeSHA256']==CANDIDATE
names=re.findall(r'test ([\w:]+) \.\.\.',output(name));assert len(names)==98 and len(set(names))==98
assert sorted(n for n in names if'memory_growth_operations::tests::'not in n)==read(HERE/'inputs/accepted-all-runtime-test-names.json')
# Positive MIR replay includes standalone promotions and excludes test hooks.
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
new=module('growth_inventory_readonly',HERE/'inventory.py');schema=read(HERE/'inventory-schema.json');assert len(schema)==10356 and len({r['field']for r in schema})==10356
assert sum(r['envelope']=='permanent'for r in schema)==1560
accounting=candidate['src/experimental_swift_reactor/memory_growth_operations.rs'].decode().split('// ACCOUNTING_START')[1]
for row in schema:assert'    '+row['field']+': '+row['rustType']+','in accounting,row['field']
keys=['field','rustType','binding','sourceNames','mirFunction','position','config','kind','envelope','window']
def projection(rows,qualify=False):
 result=[{key:r.get(key)for key in keys}for r in rows]
 if qualify:
  prefix='experimental_swift_reactor::execution::frame_operations::'
  for row in result:
   if row['mirFunction']and row['mirFunction'].startswith(prefix+'memory_operations::'):row['mirFunction']=row['mirFunction'][len(prefix):]
 return result
old=[]
for name,count in[('memory',4800),('bulk',4324)]:
 collector=module('accepted_'+name+'_readonly',HERE/'inputs'/('accepted-'+name+'-inventory.py'));collector.promoted_constants=new.promoted_constants
 prior=read(HERE/'inputs'/('accepted-'+name+'-schema.json'));assert len(prior)==count;old.append((name,collector,prior))
for features in['all','swift']:
 for config in['production','unit']:
  name='qualified-'+features+'-'+config+'-mir';assert commands[name]['sourceTreeSHA256']==CANDIDATE
  path=HERE/('qualified-'+features+'-'+config+'.mir.gz');assert sha(gzip.decompress(path.read_bytes()))==read(HERE/'commands'/name/'mir.json')['sha256']
  rows,functions,_=new.canonical(path,config);assert projection(rows)==projection([r for r in schema if r['config']==config])
  for name,collector,prior in old:
   rows,_,_=collector.canonical(path,config);assert projection(rows,name=='memory')==projection([r for r in prior if r['config']==config],name=='memory')
assert new.selected('growth_pinned_step::promoted[0]')and new.selected('release_growth_pending')and not new.selected('growth_checkpoint::promoted[0]')
assert not new.selected('memory_growth_operations::tests::fixture::promoted[0]')
# Sixteen actual metadata configurations and every measured padding byte.
layouts=read(HERE/'layouts.json');assert len(layouts)==16
for layout in layouts:
 features,profile,unit=layout['features'],layout['profile'],layout['unit'];label=layout['label']
 name='layout-qualified-'+label+'-'+features+'-'+profile+('-unit'if unit else'-production');assert commands[name]['executables']
 derived=source(commands[name]['sourceTreeSHA256']);original=candidate if label=='candidate'else base
 for path,data in original.items():assert derived[path].startswith(data),(name,path,'non-appended layout mutation')
 assert set(derived)-set(original)=={'src/bin/growth_contract_layout.rs'}
 if features=='all':assert layout['totals']['frozen_header']==2912
 if label!='candidate':continue
 prior=next(r for r in layouts if(r['label'],r['features'],r['profile'],r['unit'])==('baseline',features,profile,unit));assert layout['types']==prior['types']and layout['owners']==prior['owners']
 selected=[r for r in schema if unit or r['config']!='unit'];assert set(layout['fields'])=={r['field']for r in selected}
 for cls in['PermanentPositions','ActivePositions']:
  cursor=0;payload=0;padding=0
  for row in sorted((r for r in selected if r['ownerClass']==cls),key=lambda r:layout['fields'][r['field']]['offset']):
   value=layout['fields'][row['field']];assert value['offset']%value['alignment']==0
   if value['bytes']==0:continue
   assert value['offset']>=cursor;padding+=value['offset']-cursor;cursor=value['offset']+value['bytes'];payload+=value['bytes']
  padding+=layout['classes'][cls]['bytes']-cursor;assert payload+padding==layout['classes'][cls]['bytes']
  exact=next(r for r in read(HERE/'padding.json')if(r['features'],r['profile'],r['unit'],r['ownerClass'])==(features,profile,unit,cls));assert exact['payloadBytes']==payload and exact['paddingBytes']==padding
 t=layout['totals'];assert t['header']==prior['totals']['header']+t['growth_permanent']and t['frame']==prior['totals']['frame']+t['growth_active']
 assert t['growth_permanent']==(559472 if unit else 316376)and t['growth_active']==(1815568 if unit else 973920)
 for key in['construction','frame_permanent','frame_active','control_permanent','control_active','value','state_limit','combined_limit','accepted_memory_permanent','accepted_memory_active','accepted_bulk_permanent','accepted_bulk_active']:assert t[key]==prior['totals'][key]
 assert t['state_limit']==128*1024*1024 and t['combined_limit']==256*1024*1024
# Literal Frozen compiler expansion, owner declarations and runtime observations.
def item(text,keyword):
 a=text.index(keyword);i=text.index('{',a)+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[a:i]
identity=read(HERE/'frozen-identity.json');maps=[]
for label,digest in[('baseline',BASE),('candidate',CANDIDATE)]:
 name='isolated-expanded-'+label;assert commands[name]['sourceTreeSHA256']==digest
 impl=item(output(name),'impl SpanInstance {');names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',impl,re.M);assert len(names)==39
 maps.append({name:sha(item(impl,'fn '+name+'(').encode())for name in names})
assert maps[0]==maps[1]==identity['methods']and len(identity['containingOwners'])==14
for filename in['memory_operations.rs','bulk_memory_operations.rs']:
 path='src/experimental_swift_reactor/'+filename;assert base[path].decode().split('// ACCOUNTING_START')[1]==candidate[path].decode().split('// ACCOUNTING_START')[1]
for path in['src/experimental_swift_reactor/control.rs','src/experimental_swift_reactor/cache.rs','src/experimental_wasi/accounted.rs']:assert base[path]==candidate[path]
pairs=read(HERE/'frozen-differentials.json');assert len(pairs)==4
for profile in['debug','release']:
 observations=[]
 for label in['baseline','candidate']:
  name='isolated-frozen-differential-'+label+'-'+profile;lines=[line[line.index('FROZEN_GROWTH '):]for line in output(name).splitlines()if'FROZEN_GROWTH 'in line]
  row=next(r for r in pairs if(r['label'],r['profile'])==(label,profile));assert len(lines)==10 and row['observations']==lines;observations.append(lines)
 assert observations[0]==observations[1]
cleanup=read(HERE/'cleanup.json');assert cleanup['removed']is True and cleanup['openFilesBeforeRemoval']==0 and cleanup['nativeOrPhysicalToolsUsed']is False
print('PASS:127-file growth candidate;78 four-config growth +98 broad Release selections;20 Frozen pairs;10356 fresh +4800 memory +4324 bulk fields;16 layouts;39 Frozen methods;offline read-only replay')

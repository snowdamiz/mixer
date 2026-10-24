#!/usr/bin/env python3
"""Read-only offline replay. No compilation, extraction, writes, or VM execution."""
from pathlib import Path
import argparse,collections,gzip,hashlib,importlib.util,json,re,sys,tarfile
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda data:hashlib.sha256(data).hexdigest()
read=lambda path:json.loads(path.read_text())
BASE='17f9ea5b93fbc0b5bd51df8484e30e0cbe420eac646730da7d330c4b4ecde9ff'
CANDIDATE='e5050427a9653019e429bd6cb050133e89617d9a40c9896e0d684f12aa7c8626'
parser=argparse.ArgumentParser();parser.add_argument('--live-baseline',action='store_true');args=parser.parse_args()
seal=read(HERE/'seal.json')
actual_files={str(p.relative_to(HERE))for p in HERE.rglob('*')if p.is_file()and p.name not in['seal.json','offline-verify.log']and'__pycache__'not in p.parts}
assert actual_files==set(seal['files']),(actual_files-set(seal['files']),set(seal['files'])-actual_files)
for name,digest in seal['files'].items():assert sha((HERE/name).read_bytes())==digest,name
for name,digest in seal['documentation'].items():assert sha((HERE.parents[1]/name).read_bytes())==digest,name

def archive(path):
 with tarfile.open(path,'r:gz')as tar:
  members=tar.getmembers();assert all(m.isfile()and not Path(m.name).is_absolute()and'..'not in Path(m.name).parts for m in members)
  data={m.name:tar.extractfile(m).read()for m in members};assert len(data)==len(members)
 return data
cache={}
def source(digest):
 if digest not in cache:
  data=archive(HERE/'sources'/(digest+'.tar.gz'));m={name:sha(value)for name,value in data.items()};assert sha(enc(m))==digest;cache[digest]=data
 return cache[digest]
base=source(BASE);candidate=source(CANDIDATE)
assert len(base)==123 and len(candidate)==125
for label,digest,content in [('baseline',BASE,base),('candidate',CANDIDATE,candidate)]:
 assert read(HERE/(label+'-source-manifest.json'))=={name:sha(value)for name,value in content.items()}
 assert archive(HERE/(label+'-source.tar.gz'))==content
receipt=read(HERE/'receipt.json');assert receipt['candidateSourceSHA256']==CANDIDATE and receipt['baselineSourceSHA256']==BASE
assert receipt['scope']=='private-bounded-host-bulk-memory-candidate'
assert receipt['acceptance']['independentReview']=='pending'and receipt['acceptance']['rootIntegration']=='pending'and receipt['acceptance']['ga']=='pending'
commands=read(HERE/'command-index.json')
for name,r in commands.items():
 d=HERE/'commands'/name;assert read(d/'receipt.json')==r
 for stream in ['stdout','stderr']:
  path=d/stream;data=path.read_bytes()if path.exists()else gzip.decompress((d/(stream+'.gz')).read_bytes())
  assert sha(data)==r[stream+'SHA256'],(name,stream)
 assert r['sourceUnchanged']is True
 if r['sourceTreeSHA256']:
  m=read(d/'source-manifest.json');assert sha(enc(m))==r['sourceTreeSHA256'];assert {k:sha(v)for k,v in source(r['sourceTreeSHA256']).items()}==m

def output(name,stream='stdout'):
 p=HERE/'commands'/name/stream
 return(p.read_bytes()if p.exists()else gzip.decompress(p.with_name(stream+'.gz').read_bytes())).decode()
for name in receipt['qualifyingCommands']:assert commands[name]['exitCode']==0,name
expected=re.findall(r'#\[test\] fn (bm\d+_\w+)',(HERE/'tests.rs').read_text());assert len(expected)==16 and len(set(expected))==16
matrix=read(HERE/'matrix-results.json');assert len(matrix)==4
for r in matrix:
 name='sealed-runtime-'+r['features']+'-'+r['profile'];text=output(name)
 assert commands[name]['sourceTreeSHA256']==CANDIDATE
 assert re.search(r'test result: ok\. 78 passed; 0 failed; 0 ignored;',text)
 tests=re.findall(r'test ([\w:]+) \.\.\.',text);actual=[n.rsplit('::',1)[-1]for n in tests if'bulk_memory_operations::tests::'in n]
 assert sorted(actual)==sorted(expected)==sorted(r['bulkTests'])
 assert len(tests)==78 and all(actual.count(n)==1 for n in expected)
 bounds=re.findall(r'BM_BOUND fixtures=(\d+) totalSteps=(\d+) maxStepsPerFixture=64 maxFrames=3 realPages=584',text)
 assert len(bounds)==16 and all(int(n)<=64 and int(steps)<=4096 for n,steps in bounds)
 assert r['sourceTreeSHA256']==CANDIDATE

schema=read(HERE/'inventory-schema.json');assert len(schema)==4324 and len({r['field']for r in schema})==4324
assert len([r for r in schema if r['envelope']=='permanent'])==52
accounting=candidate['src/experimental_swift_reactor/bulk_memory_operations.rs'].decode().split('// ACCOUNTING_START')[1]
for r in schema:assert'    '+r['field']+': '+r['rustType']+','in accounting
old_schema=read(HERE/'inputs/accepted-memory-schema.json');assert len(old_schema)==4800
for p in ['src/experimental_swift_reactor/memory_operations.rs']:
 assert base[p].decode().split('// ACCOUNTING_START')[1]==candidate[p].decode().split('// ACCOUNTING_START')[1]
layouts=read(HERE/'layouts.json');assert len(layouts)==16
for r in layouts:
 if r['label']!='candidate':continue
 prior=next(p for p in layouts if(p['label'],p['features'],p['profile'],p['unit'])==('baseline',r['features'],r['profile'],r['unit']))
 assert r['types']==prior['types']and r['owners']==prior['owners']
 selected=[s for s in schema if r['unit']or s['config']!='unit'];assert set(r['fields'])=={s['field']for s in selected}
 seen={}
 for row in sorted(selected,key=lambda s:(s['ownerClass'],r['fields'][s['field']]['offset'])):
  v=r['fields'][row['field']];cls=row['ownerClass'];assert v['offset']>=seen.get(cls,0)and v['offset']%v['alignment']==0;seen[cls]=v['offset']+v['bytes'];assert seen[cls]<=r['classes'][cls]['bytes']
 for key in ['construction','frame_permanent','frame_active','control_permanent','control_active','value','state_limit','combined_limit','accepted_memory_permanent','accepted_memory_active']:assert r['totals'][key]==prior['totals'][key]
 t=r['totals'];assert t['bulk_permanent']==121856 and t['bulk_active']==(1206544 if r['unit']else642456)
 assert t['header']==prior['totals']['header']+t['bulk_permanent']and t['frame']==prior['totals']['frame']+t['bulk_active']
 assert t['frame']==t['frame_active']+t['value']+t['control_active']+t['accepted_memory_active']+t['bulk_active']
 if r['features']=='all':assert t['frozen_header']==2912
# Replay actual canonical compiler positions; no audit script with writes is imported.
def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
bulk=load_module('bulk_inventory_read_only',HERE/'inventory.py');old=load_module('accepted_inventory_read_only',HERE/'inputs/accepted-memory-inventory.py')
keys=['field','rustType','binding','sourceNames','mirFunction','position','config','kind','envelope','window']
def projection(rows,qualify=False):
 result=[{key:r.get(key)for key in keys}for r in rows]
 if qualify:
  prefix='experimental_swift_reactor::execution::frame_operations::'
  for r in result:
   if r['mirFunction']and r['mirFunction'].startswith(prefix+'memory_operations::'):r['mirFunction']=r['mirFunction'][len(prefix):]
 return result
for stage in ['sealed','sealed-swift']:
 for config in['production','unit']:
  path=HERE/(stage+'-'+config+'.mir.gz');rows,functions,_=bulk.canonical(path,config);assert projection(rows)==projection([r for r in schema if r['config']==config])
  rows,_,_=old.canonical(path,config);assert projection(rows,True)==projection([r for r in old_schema if r['config']==config],True)
  if config=='unit':assert any(f['function']=='bulk_memory_pinned_step::promoted[0]'for f in functions)
assert bulk.selected('bulk_memory_pinned_step::promoted[0]')and not bulk.selected('bulk_memory_operations::tests::fixture::promoted[0]')and not bulk.selected('memory_pinned_step::promoted[0]')
# Reproduce identity from actual compiler-expanded output, then compare recorded hashes.
def method(text,name):
 a=text.index('fn '+name+'(');i=text.index('{',a)+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[a:i]
maps=[]
for label in ['baseline','candidate']:
 text=output('sealed-expanded-'+label);text=text[text.index('impl SpanInstance {'):];i=text.index('{')+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 text=text[:i];names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',text,re.M);assert len(names)==39 and len(set(names))==39
 maps.append({name:sha(method(text,name).encode())for name in names})
identity=read(HERE/'frozen-identity.json');assert maps[0]==maps[1]==identity['methods']and len(identity['containingOwners'])==14
for profile in['debug','release']:
 a=[line[line.index('FROZEN_SNAPSHOT '):]for line in output('sealed-frozen-snapshot-baseline-'+profile).splitlines()if'FROZEN_SNAPSHOT 'in line]
 b=[line[line.index('FROZEN_SNAPSHOT '):]for line in output('sealed-frozen-snapshot-candidate-'+profile).splitlines()if'FROZEN_SNAPSHOT 'in line]
 assert len(a)==32 and a==b
 for label in['baseline','candidate']:assert re.search(r'test result: ok\. 16 passed; 0 failed; 0 ignored;',output('sealed-frozen-integration-'+label+'-'+profile))
cleanup=read(HERE/'cleanup.json');assert cleanup['removed']is True and cleanup['openFilesBeforeRemoval']==0 and cleanup['nativeOrPhysicalToolsUsed']is False
if args.live_baseline:
 vm=HERE.parents[1]/'vm';paths=[vm/'Cargo.toml',vm/'Cargo.lock']
 for directory in['src','tests','include']:paths+=sorted(p for p in(vm/directory).rglob('*')if p.is_file())
 actual={str(p.relative_to(vm)):sha(p.read_bytes())for p in paths};assert sha(enc(actual))==BASE
print('PASS: sealed125-file candidate;312 execution tests;64 Frozen pairs;4800 retained +4324 fresh fields;16 layouts;39 Frozen methods;read-only replay')

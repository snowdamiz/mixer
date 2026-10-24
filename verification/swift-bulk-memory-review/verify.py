#!/usr/bin/env python3
"""Read-only sealed independent review replay; no compilation or extraction."""
from pathlib import Path
import collections,gzip,hashlib,importlib.util,json,re,sys,tarfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PACKET=HERE.parent/'swift-bulk-memory'
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda d:hashlib.sha256(d).hexdigest()
read=lambda p:json.loads(p.read_text())
BASE='17f9ea5b93fbc0b5bd51df8484e30e0cbe420eac646730da7d330c4b4ecde9ff';CAND='e5050427a9653019e429bd6cb050133e89617d9a40c9896e0d684f12aa7c8626'
seal=read(HERE/'seal.json')
actual={str(p.relative_to(HERE))for p in HERE.rglob('*')if p.is_file()and p.name not in['seal.json','offline-verify.log']and'__pycache__'not in p.parts}
assert actual==set(seal['files'])
for name,digest in seal['files'].items():assert sha((HERE/name).read_bytes())==digest,name
for name,digest in seal['documentation'].items():assert sha((ROOT/name).read_bytes())==digest,name
assert sha((PACKET/'seal.json').read_bytes())==seal['producerSealSHA256']
# Recheck producer bytes referenced by the review, without trusting a summary.
producer=read(PACKET/'seal.json')
for name,digest in producer['files'].items():assert sha((PACKET/name).read_bytes())==digest,name
for name,digest in producer['documentation'].items():assert sha((ROOT/name).read_bytes())==digest,name

def output(folder,stream='stdout'):
 p=folder/stream;return p.read_bytes()if p.exists()else gzip.decompress((folder/(stream+'.gz')).read_bytes())
commands=read(HERE/'command-index.json')
for name,r in commands.items():
 folder=HERE/'commands'/name;assert read(folder/'receipt.json')==r
 for stream in['stdout','stderr']:assert sha(output(folder,stream))==r[stream+'SHA256']
 assert r['sourceUnchanged']is True and r['sourceRevision']=='615a05dc14655dace87c2ff561a610bef4526621'
 if r['sourceTreeSHA256']:assert sha(enc(read(folder/'source-manifest.json')))==r['sourceTreeSHA256']
receipt=read(HERE/'receipt.json');assert receipt['candidateSourceSHA256']==CAND and receipt['baselineSourceSHA256']==BASE
assert receipt['decision']=='suitable-for-root-integration-private-bounded-host-slice'and receipt['rootIntegration']=='pending'and receipt['GA']=='pending'
for name in receipt['qualifyingCommands']:assert commands[name]['exitCode']==0
assert {n for n,r in commands.items()if r['exitCode']!=0}==set(receipt['excludedNonzeroCommands'])
assert len(read(HERE/'historical-failures.json'))==7
for prefix,path,expected_count,source in[('fresh-bulk-',HERE/'matrix-results.json',16,CAND),('fresh-adversarial-',HERE/'adversarial-results.json',3,receipt['adversarialSourceSHA256'])]:
 rows=read(path);assert len(rows)==4
 for row in rows:
  name=prefix+row['features']+'-'+row['profile']+('-retry'if prefix=='fresh-adversarial-'and row['features']=='swift'and row['profile']=='debug'else'')
  r=commands[name];text=output(HERE/'commands'/name).decode();assert r['sourceTreeSHA256']==source and r['executables']
  tests=re.findall(r'test ([\w:]+) \.\.\.',text);assert len(tests)==expected_count and len(set(tests))==expected_count
  expected=row['selected']if prefix=='fresh-bulk-'else row['tests'];actual=[n.rsplit('::',1)[-1]for n in tests]if prefix=='fresh-bulk-'else tests;assert actual==expected
  assert f'test result: ok. {expected_count} passed; 0 failed; 0 ignored;'in text
  bounds=re.findall(r'BM_BOUND fixtures=(\d+) totalSteps=(\d+) maxStepsPerFixture=64 maxFrames=3 realPages=584',text);assert len(bounds)==expected_count and all(int(n)<=64 and int(s)<=int(n)*64 for n,s in bounds)
  assert bounds==[tuple(x)for x in row['bounds']]
# Actual archives for review instrumentation and failed compiler attempt.
for label in['adversarial','failed-adversarial','layout-baseline','layout-candidate']:
 with tarfile.open(HERE/(label+'-source.tar.gz'),'r:gz')as t:
  members=t.getmembers();assert all(m.isfile()and not Path(m.name).is_absolute()and'..'not in Path(m.name).parts for m in members)
  data={m.name:sha(t.extractfile(m).read())for m in members};assert len(data)==len(members)
 assert data==read(HERE/(label+'-source-manifest.json'))

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
bulk=load('review_bulk_read_only',PACKET/'inventory.py');old=load('review_old_read_only',PACKET/'inputs/accepted-memory-inventory.py')
schema=read(PACKET/'inventory-schema.json');old_schema=read(PACKET/'inputs/accepted-memory-schema.json')
keys=['field','rustType','binding','sourceNames','mirFunction','position','config','kind','envelope','window'];project=lambda rows:[{k:r.get(k)for k in keys}for r in rows]
canonical=read(HERE/'canonical-results.json');assert len(canonical)==4
for row in canonical:
 name='fresh-mir-'+row['features']+'-'+row['config'];path=HERE/(name+'.mir.gz');content=gzip.decompress(path.read_bytes());assert sha(content)==row['mirSHA256']and commands[name]['sourceTreeSHA256']==CAND
 fields,functions,captures=bulk.canonical(path,row['config']);assert project(fields)==project([r for r in schema if r['config']==row['config']]);assert functions==row['functions']and captures==row['captures']
 prior,_,_=old.canonical(path,row['config']);actual=project(prior);expected=project([r for r in old_schema if r['config']==row['config']]);delta=[];prefix='experimental_swift_reactor::execution::frame_operations::';assert len(actual)==len(expected)
 for a,b in zip(actual,expected):
  changes={k:[a[k],b[k]]for k in keys if a[k]!=b[k]}
  if changes:
   assert set(changes)=={'mirFunction'}and a['mirFunction']==prefix+b['mirFunction']and b['mirFunction'].startswith('memory_operations::')
   delta.append(dict(field=a['field'],**changes))
 assert delta==row['qualificationOnlyDelta']and len(delta)==(1672 if row['config']=='unit'else 0)
 raw=[]
 for line in content.decode().splitlines():
  if not(line.startswith('fn ')or(line.startswith('const ')and'::promoted['in line)):continue
  if'bulk_memory_'in line and'::tests::'not in line and'::tests}'not in line and'bulk_memory_operations_tests.rs'not in line:raw.append(line)
 assert raw==row['rawHeaders']
 assert set(h.split('(',1)[0][3:]if h.startswith('fn ')else h[6:].split(': &',1)[0]for h in raw)=={f['function']for f in functions}
 assert row['preflightPromotions']and(bool(row['standalonePromotions'])==(row['config']=='unit'))
# Fresh Frozen expansion hashes are reconstructed directly from compiler output.
def item(text,needle):
 at=text.index(needle);i=text.index('{',at)+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[at:i]
identity=read(HERE/'identity-results.json');assert identity['methodsCount']==39 and identity['ownerCount']==14
for label in['baseline','candidate']:
 text=output(HERE/'commands'/('fresh-expanded-'+label)).decode();span=item(text,'impl SpanInstance {');names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',span,re.M);assert len(names)==39
 assert {n:sha(item(span,'fn '+n+'(').encode())for n in names}==identity['methods']==read(PACKET/'frozen-identity.json')['methods']
# Reconstruct every fresh layout output before testing its actual intervals.
fresh=read(HERE/'layout-results.json');assert len(fresh)==4
for row in fresh:
 name='fresh-layout-'+row['label']+('-unit'if row['unit']else'-production');text=output(HERE/'commands'/name).decode();data={k:{}for k in['types','owners','classes','fields','totals']}
 for line in text.splitlines():
  at=line.find('RV_')
  if at<0:continue
  tag,key,*values=line[at:].split();v=list(map(int,values));target={'RV_TYPE':'types','RV_OWNER':'owners','RV_CLASS':'classes','RV_FIELD':'fields','RV_TOTAL':'totals'}[tag];assert key not in data[target]
  data[target][key]=dict(bytes=v[0],alignment=v[1])if target in['types','classes']else dict(offset=v[0],bytes=v[1],alignment=v[2])if target=='fields'else v[0]
 assert all(data[k]==row[k]for k in data)
 if row['label']=='candidate':
  selected=[r for r in schema if row['unit']or r['config']!='unit'];ends={}
  for r in sorted(selected,key=lambda r:(r['ownerClass'],data['fields'][r['field']]['offset'])):
   f=data['fields'][r['field']];cls=r['ownerClass'];assert f['offset']>=ends.get(cls,0)and f['offset']%f['alignment']==0;ends[cls]=f['offset']+f['bytes'];assert ends[cls]<=data['classes'][cls]['bytes']
  baseline=next(r for r in fresh if r['label']=='baseline'and r['unit']==row['unit']);assert data['owners']==baseline['owners']and data['types']==baseline['types'];assert data['totals']['header']==baseline['totals']['header']+121856;assert data['totals']['frame']==baseline['totals']['frame']+data['totals']['bulk_active']
accounting=read(HERE/'accounting-results.json');assert accounting['freshFields']==4324 and accounting['retainedFields']==4800 and accounting['roleGroups']==1081
assert len(accounting['layouts'])==8
for row in accounting['layouts']:
 t=row['totals'];assert t['frame']==sum(t[k]for k in['frame_active','control_active','value','accepted_memory_active','bulk_active']);assert t['bulk_active']==(1206544 if row['unit']else 642456)and t['bulk_permanent']==121856
cleanup=read(HERE/'cleanup.json');assert cleanup['removed']is True and cleanup['openFilesBeforeRemoval']==0 and cleanup['nativeOrPhysicalToolsUsed']is False
print('PASS independent sealed private bulk review:64 fresh candidate selections +12 independent selections;4 fresh MIR;39 Frozen methods;14 owners;4 fresh typed layouts;all retained/new positions;cleanup')

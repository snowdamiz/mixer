#!/usr/bin/env python3
from review import *
import collections,re

def run():
 seal=json.loads((PACKET/'seal.json').read_text());bound={str(p.relative_to(PACKET)):sha(p.read_bytes())for p in PACKET.rglob('*')if p.is_file()and p!=PACKET/'seal.json'};assert bound==seal['files']and len(bound)==1671
 assert sha((ROOT/seal['documentation']).read_bytes())==seal['documentationSHA256']
 archives={};source_by_digest={}
 for f in sorted(PACKET.glob('*-source-manifest.json')):
  m=json.loads(f.read_text());label=f.name.removesuffix('-source-manifest.json');seen={}
  with tarfile.open(PACKET/(label+'-source.tar.gz'))as t:
   for a in t:
    assert a.isfile()and not Path(a.name).is_absolute()and '..'not in Path(a.name).parts and a.name not in seen
    seen[a.name]=sha(t.extractfile(a).read())
  assert seen==m
  digest=sha(enc(m));archives[label]=dict(files=len(m),closure=digest,archiveSHA256=sha((PACKET/(label+'-source.tar.gz')).read_bytes()));source_by_digest[digest]=m
 commands={};unexpected=[]
 for f in sorted((PACKET/'commands').glob('*/receipt.json')):
  r=json.loads(f.read_text());name=f.parent.name
  for n in ['stdout','stderr']:assert sha(gzip.decompress((f.parent/(n+'.gz')).read_bytes()))==r[n+'SHA256']
  before=r['sourceTreeBeforeSHA256']
  if before:
   m=json.loads((f.parent/'source-manifest.json').read_text());assert sha(enc(m))==before==r['sourceTreeAfterSHA256']and r['sourceUnchanged']and m==source_by_digest[before]
  if 'groupCleanup'in r:assert r['groupCleanup']['after']==[] and not r['timedOut']and r['groupCleanup']['group']==r['ownedProcessGroup']
  if r['exitCode']!=r['expectedExitCode']:unexpected.append(name)
  commands[name]=r
 receipt=json.loads((PACKET/'receipt.json').read_text());assert sorted(unexpected)==sorted(receipt['excludedFailedCommands'])and len(unexpected)==9
 # Bind every retained binary to a real fresh Cargo JSON record from a matching source build.
 artifacts={}
 for d in sorted((PACKET/'artifacts').iterdir()):
  if not d.is_dir():continue
  identity=json.loads((d/'identity.json').read_text());cargo=json.loads((d/'cargo-artifact.json').read_text());exe=gzip.decompress((d/'executable.gz').read_bytes());h=sha(exe)
  assert h==identity['executableSHA256']and len(exe)==identity['executableBytes']and cargo['fresh']is False and identity['cargoArtifactFresh']is False and identity['targetCreatedEmpty']
  assert cargo['executable']==identity['exactExecutablePath']and identity['sourceTreeSHA256']in source_by_digest
  builds=[]
  for name,r in commands.items():
   if r['sourceTreeBeforeSHA256']!=identity['sourceTreeSHA256']or not r['argv']or r['argv'][0]!='cargo':continue
   if r['environment'].get('CARGO_TARGET_DIR')!=identity.get('cargoTarget',str(Path(identity['exactExecutablePath']).parents[2])):continue
   output=gzip.decompress((PACKET/'commands'/name/'stdout.gz').read_bytes()).decode()
   for line in output.splitlines():
    if line.startswith('{'):
     obj=json.loads(line)
     if obj==cargo:builds.append(name)
  assert builds,(d.name,'no exact Cargo record')
  for k in ['executableBeforeRunSHA256','executableAfterRunSHA256','executableBeforeListSHA256','executableAfterListSHA256','probeExecutableSHA256']:
   if identity.get(k)is not None:assert identity[k]==h
  if (d/'test-list.json').exists():
   tests=json.loads((d/'test-list.json').read_text());assert len(tests)==len(set(tests))==identity['fullUnitTestCount']
   listing=[n for n,r in commands.items()if r['argv']==[cargo['executable'],'--list']];assert len(listing)==1
   output=gzip.decompress((PACKET/'commands'/listing[0]/'stdout.gz').read_bytes()).decode();assert [l[:-6]for l in output.splitlines()if l.endswith(': test')]==tests
  artifacts[d.name]=dict(executableSHA256=h,bytes=len(exe),buildCommands=builds,sourceClosure=identity['sourceTreeSHA256'])
 # Reconstruct precise diff independently, including every test-only append.
 import difflib
 baseline=scratch()/'baseline';candidate=scratch()/'candidate';bm=manifest(baseline);cm=manifest(candidate);diff='';changes={}
 for n in sorted(set(bm)|set(cm)):
  if bm.get(n)==cm.get(n):continue
  changes[n]=dict(before=bm.get(n),after=cm.get(n));a=(baseline/n).read_text().splitlines(True)if n in bm else[];b=(candidate/n).read_text().splitlines(True)
  diff+=''.join(difflib.unified_diff(a,b,fromfile='a/vm/'+n,tofile='b/vm/'+n))
 assert diff==(PACKET/'candidate.patch').read_text()and changes==json.loads((PACKET/'changed-files.json').read_text())
 # Actual original declarations and source are unchanged; engine declaration count is cross-checked by compiler expansion separately.
 def declaration(s,needle):
  start=s.index(needle);at=s.index('{',start);depth=1;end=at+1
  while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
  return s[start:end]
 fi=json.loads((PACKET/'frozen-identity.json').read_text());owners=fi['unchangedOwners']
 found={}
 for n in bm:
  if not n.endswith('.rs'):continue
  a=(baseline/n).read_text();b=(candidate/n).read_text()
  for needle,h in owners.items():
   if needle in a:
    x=declaration(a,needle)
    if sha(x.encode())!=h:continue
    assert needle not in found,(needle,n);assert x==declaration(b,needle);found[needle]=n
 assert set(found)==set(owners)and len(found)==16
 for n in ['src/experimental/execution/mod.rs','src/experimental_wasi/mod.rs','src/experimental_swift_reactor/memory_operations.rs','src/experimental_swift_reactor/bulk_memory_operations.rs','src/experimental_swift_reactor/memory_growth_operations.rs']:
  assert bm[n]==cm[n]
 for n in ['src/experimental_swift_reactor/control.rs','src/experimental_wasi/accounted.rs']:assert (candidate/n).read_text().startswith((baseline/n).read_text())
 # Check all sixteen observations against their exact executable command output, additive original bounds and intervals.
 schema=json.loads((PACKET/'inventory-schema.json').read_text());layouts=json.loads((PACKET/'qualified-accounted-layouts.json').read_text());assert len(layouts)==16 and len({x['cargoTarget']for x in layouts})==16
 zeros={};layout_receipts=[]
 for x in layouts:
  name='qualified-accounted-'+x['label']+'-'+x['features']+'-'+x['profile']+'-'+('unit'if x['unit']else'production');cmd=commands['execute-'+name];a=artifacts[name]
  assert cmd['argv'][0]==json.loads((PACKET/'artifacts'/name/'cargo-artifact.json').read_text())['executable']and cmd['sourceTreeBeforeSHA256']==x['sourceTreeSHA256']==a['sourceClosure']and cmd['exitCode']==0
  output=gzip.decompress((PACKET/'commands'/('execute-'+name)/'stdout.gz').read_bytes()).decode();observed=parse_layout(output);assert observed==x['layout']
  if x['label']=='candidate':
   b=next(v for v in layouts if(v['label'],v['features'],v['profile'],v['unit'])==('baseline',x['features'],x['profile'],x['unit']))['layout'];z=x['layout'];assert z['types']==b['types']and z['owners']==b['owners'];expected={r['field']for r in schema if x['unit']or r['config']!='unit'};assert set(z['fields'])==expected
   positive={};zero=[]
   for r in schema:
    if r['field']not in expected:continue
    f=z['fields'][r['field']];cls=z['classes'][r['ownerClass']];start=f['offset'];end=start+f['bytes'];assert start%f['alignment']==0 and 0<=start<=end<=cls['bytes']
    if f['bytes']==0:zero.append(r['field']);continue
    positive.setdefault(r['ownerClass'],[]).append((start,end,r['field']))
   for intervals in positive.values():
    intervals.sort();assert all(a[1]<=b[0]for a,b in zip(intervals,intervals[1:]))
   zeros[name]=zero
   for k,v in b['totals'].items():assert z['totals'][k]==v+(z['classes']['HostPermanentPositions']['bytes']if k=='header'else z['classes']['HostActivePositions']['bytes']if k=='frame'else 0)
   assert z['totals']['ticket_max']==86 and z['totals']['state_limit']==134217728 and z['totals']['combined_limit']==268435456
  layout_receipts.append(dict(name=name,sourceClosure=x['sourceTreeSHA256'],executableSHA256=a['executableSHA256']))
 # Final qualifying MIR and measured layouts finish before every qualifying library run.
 final=receipt['candidateSourceClosure'];mir_end=max(commands['qualified-source-mir-'+c]['completedUTC']for c in ['production','unit']);layout_end=max(commands['execute-'+r['name']]['completedUTC']for r in layout_receipts)
 for name in ['execute-qualified-runtime-'+f+'-'+p for f in ['default','swift','all']for p in ['debug','release']]:
  r=commands[name];assert r['sourceTreeBeforeSHA256']==final and r['exitCode']==0 and r['startedUTC']>mir_end and r['startedUTC']>layout_end
 # Cleanup record is a historical fact cross-linked to its exact targeted holder command and absent source tree.
 cleanup=json.loads((PACKET/'cleanup.json').read_text());cr=commands['qualified-cleanup-holders'];assert cr['argv']==cleanup['lsofArgv']and cr['exitCode']==cleanup['lsofExitCode']==1 and cleanup['scratchRemoved']and not Path(cleanup['scratch']).exists()
 for stream in ['stdout','stderr']:assert gzip.decompress((PACKET/'commands/qualified-cleanup-holders'/(stream+'.gz')).read_bytes())==b''
 save('packet-audit.json',dict(sealSHA256=sha((PACKET/'seal.json').read_bytes()),boundFiles=len(bound),archives=archives,nestedCommands=len(commands),artifacts=artifacts,changedFiles=changes,unchangedOwners=found,layoutExecutables=layout_receipts,zeroSizedIntervals=zeros,accountingPositions=len(schema),schemaCounts=dict(collections.Counter(r['config']for r in schema)),excludedFailedCommands=unexpected,finalMIRCompletedUTC=mir_end,finalLayoutsCompletedUTC=layout_end,qualifyingRuntimeAfterMIRAndLayouts=True,historicalCleanupConsistent=True,historicalCleanupNotRerun=True))
 print('Independent packet audit passed',len(bound),len(commands),len(artifacts),flush=True)

def parse_layout(output):
 result={k:{}for k in ['types','classes','fields','totals','owners']}
 for line in output.splitlines():
  at=line.find('HC_')
  if at<0:continue
  tag,name,*values=line[at:].split();values=list(map(int,values));key={'HC_TYPE':'types','HC_CLASS':'classes','HC_FIELD':'fields','HC_TOTAL':'totals','HC_OWNER':'owners'}[tag];assert name not in result[key]
  result[key][name]=dict(bytes=values[0],alignment=values[1])if key in ['types','classes']else dict(offset=values[0],bytes=values[1],alignment=values[2])if key=='fields'else values[0]
 return result
if __name__=='__main__':run()

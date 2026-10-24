#!/usr/bin/env python3
"""Offline verify exact sealed evidence. No runtime/native tool is started."""
from pathlib import Path
import argparse,gzip,hashlib,json,re,tarfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda x:hashlib.sha256(x).hexdigest()
def read(n):return json.loads((HERE/n).read_text())
def digest(x):return sha(enc(x))
def check(preseal=False,live=False):
 archives={}
 for p in sorted(HERE.glob('*-source-manifest.json')):
  label=p.name.removesuffix('-source-manifest.json');m=json.loads(p.read_text());archive=HERE/(label+'-source.tar.gz');assert archive.exists(),label
  with tarfile.open(archive)as t:
   members=t.getmembers();assert len(members)==len(m)and all(x.isfile()and not Path(x.name).is_absolute()and'..'not in Path(x.name).parts for x in members)
   actual={x.name:sha(t.extractfile(x).read())for x in members}
  assert actual==m,label
  archives[label]=dict(files=len(m),sourceTreeSHA256=digest(m),archiveSHA256=sha(archive.read_bytes()))
 known={x['sourceTreeSHA256']for x in archives.values()};commands={};failed=[]
 for p in sorted((HERE/'commands').glob('*/receipt.json')):
  r=json.loads(p.read_text());name=p.parent.name
  for stream in['stdout','stderr']:assert sha(gzip.decompress((p.parent/(stream+'.gz')).read_bytes()))==r[stream+'SHA256'],(name,stream)
  if r['sourceTreeBeforeSHA256']is not None:
   m=json.loads((p.parent/'source-manifest.json').read_text());assert digest(m)==r['sourceTreeBeforeSHA256']==r['sourceTreeAfterSHA256'];assert r['sourceUnchanged']and digest(m)in known,(name,'unarchived source')
  if'groupCleanup'in r:assert not r['groupCleanup']['after']and not r['timedOut'],name
  if r['exitCode']!=r['expectedExitCode']:failed.append(name)
  commands[name]=r
 final_tree=archives['candidate']['sourceTreeSHA256'];assert archives['candidate']['files']==128;assert archives['baseline']['sourceTreeSHA256']=='a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b'
 artifacts={}
 for d in sorted((HERE/'artifacts').iterdir()):
  if not d.is_dir():continue
  a=json.loads((d/'cargo-artifact.json').read_text());identity=json.loads((d/'identity.json').read_text());data=gzip.decompress((d/'executable.gz').read_bytes());h=sha(data)
  assert a['fresh']is False and identity['cargoArtifactFresh']is False and identity['targetCreatedEmpty']
  assert h==identity['executableSHA256']and len(data)==identity['executableBytes']
  assert a['executable']==identity['exactExecutablePath']
  for k in['executableBeforeRunSHA256','executableAfterRunSHA256','executableBeforeListSHA256','executableAfterListSHA256','probeExecutableSHA256']:
   if identity.get(k)is not None:assert identity[k]==h,(d.name,k)
  listed=d/'test-list.json'
  if listed.exists():
   tests=json.loads(listed.read_text());assert len(tests)==len(set(tests))==identity['fullUnitTestCount']
   matches=[n for n,r in commands.items()if r['argv']==[a['executable'],'--list']];assert len(matches)==1,(d.name,matches)
   output=gzip.decompress((HERE/'commands'/matches[0]/'stdout.gz').read_bytes()).decode();actual=[l[:-6]for l in output.splitlines()if l.endswith(': test')];assert actual==tests
  artifacts[d.name]=identity
 schema=read('inventory-schema.json');assert len(schema)==4876
 for config in['production','unit']:
  r=commands['qualified-source-mir-'+config];assert r['sourceTreeBeforeSHA256']==final_tree and r['exitCode']==0
  a=read('qualified-source-mir-'+config+'-artifact.json');assert a['fresh']is False
 layouts=read('qualified-accounted-layouts.json');assert len(layouts)==16;assert len({x['cargoTarget']for x in layouts})==16
 for x in layouts:
  name='qualified-accounted-'+x['label']+'-'+x['features']+'-'+x['profile']+'-'+('unit'if x['unit']else'production');a=artifacts[name];assert a['sourceTreeSHA256']==x['sourceTreeSHA256'];layout=x['layout'];assert layout['totals']['state_limit']==134217728 and layout['totals']['combined_limit']==268435456 and layout['totals']['ticket_max']==86
  if x['label']!='candidate':continue
  b=next(y for y in layouts if(y['label'],y['features'],y['profile'],y['unit'])==('baseline',x['features'],x['profile'],x['unit']))['layout'];assert layout['types']==b['types']and layout['owners']==b['owners']
  for k,v in b['totals'].items():assert layout['totals'][k]==v+(layout['classes']['HostPermanentPositions']['bytes']if k=='header'else layout['classes']['HostActivePositions']['bytes']if k=='frame'else 0),(name,k)
  expected={r['field']for r in schema if x['unit']or r['config']!='unit'};assert set(layout['fields'])==expected;end={}
  for r in sorted((r for r in schema if r['field']in expected),key=lambda r:(r['ownerClass'],layout['fields'][r['field']]['offset'])):
   f=layout['fields'][r['field']];owner=r['ownerClass'];assert f['offset']>=end.get(owner,0)and f['offset']%f['alignment']==0;end[owner]=f['offset']+f['bytes'];assert end[owner]<=layout['classes'][owner]['bytes']
  if x['unit']:
   base_name=name.replace('candidate','baseline');bt=set(json.loads((HERE/'artifacts'/base_name/'test-list.json').read_text()));ct=set(json.loads((HERE/'artifacts'/name/'test-list.json').read_text()));assert bt<=ct;assert len(ct-bt)==16 and all('::host_tests::h'in n for n in ct-bt)
 runtimes=[]
 for f in['swift','all','default']:
  for p in['debug','release']:
   r=read('runtime-'+f+'-'+p+'.json');assert r['sourceTreeSHA256']==final_tree and r['hostTests']==(0 if f=='default'else 16);name='qualified-runtime-'+f+'-'+p;cmd=commands['execute-'+name];assert cmd['exitCode']==0 and cmd['sourceTreeBeforeSHA256']==final_tree;output=gzip.decompress((HERE/'commands'/('execute-'+name)/'stdout.gz').read_bytes()).decode();assert re.search(r'test result: ok\. '+str(r['passed'])+r' passed; 0 failed;',output);assert r['passed']==artifacts[name]['fullUnitTestCount'];runtimes.append(r)
 frozen=read('frozen-runtime-results.json');assert len(frozen)==4 and all(x['passed']==16 for x in frozen)
 for x in frozen:assert x['sourceTreeSHA256']==archives[x['label']]['sourceTreeSHA256']
 identity=read('frozen-identity.json');assert identity['methodCount']==39 and identity['originalContainingOwnerCount']==14 and identity['checkedOwnerCount']==16
 negative=read('negative-borrows.json');assert set(negative)=={'arguments','cache-view','cache-phase'}and all(set(x['errorCodes'])<={'E0499','E0502'}and x['errorCodes']for x in negative.values())
 if not preseal:
  receipt=read('receipt.json');assert set(failed)==set(receipt['excludedFailedCommands'])
  seal=read('seal.json');actual={str(p.relative_to(HERE)):sha(p.read_bytes())for p in sorted(HERE.rglob('*'))if p.is_file()and p!=HERE/'seal.json'};assert actual==seal['files'];assert sha((ROOT/'docs/swift-host-operation-implementation.md').read_bytes())==seal['documentationSHA256']
  cleanup=read('cleanup.json');assert cleanup['scratchRemoved']and cleanup['lsofObservedNoOpenHolders']and not Path(cleanup['scratch']).exists()
 if live:
  vm=ROOT/'vm';paths=[vm/'Cargo.toml',vm/'Cargo.lock']
  for name in['src','tests','include']:paths+=sorted(p for p in(vm/name).rglob('*')if p.is_file())
  m={str(p.relative_to(vm)):sha(p.read_bytes())for p in paths}
  assert m==read('baseline-source-manifest.json'),'live source has advanced from candidate baseline'
 return dict(sourceArchives=len(archives),commands=len(commands),artifacts=len(artifacts),finalCandidate=final_tree,finalPositivePositions=len(schema),finalLayoutContexts=16,libraryTests=sum(x['passed']for x in runtimes),frozenTests=64,excludedFailedCommands=failed,nestedCommandReceiptsVerified=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--preseal',action='store_true');a.add_argument('--live-baseline',action='store_true');args=a.parse_args();print(json.dumps(check(args.preseal,args.live_baseline),sort_keys=True))

#!/usr/bin/env python3
"""Read-only sealed review verifier; starts no compiler, runtime, device or native tool."""
from pathlib import Path
import argparse,gzip,hashlib,json,re,tarfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
enc=lambda v:(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def read(n):return json.loads((HERE/n).read_text())
def check(preseal=False):
 archives={};known=set()
 for p in HERE.glob('*-source-manifest.json'):
  label=p.name.removesuffix('-source-manifest.json');m=json.loads(p.read_text());archive=HERE/(label+'-source.tar.gz');assert archive.exists();seen={}
  with tarfile.open(archive)as t:
   for a in t:
    assert a.isfile()and a.name not in seen and not Path(a.name).is_absolute()and'..'not in Path(a.name).parts;seen[a.name]=sha(t.extractfile(a).read())
  assert seen==m;digest=sha(enc(m));known.add(digest);archives[label]=digest
 identity=read('input-identity.json');assert archives['candidate']==identity['candidateClosure']=='7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329';assert archives['baseline']==identity['baselineClosure']=='a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b';assert sha((HERE/'candidate-source.tar.gz').read_bytes())==identity['candidateArchiveSHA256']=='e9d134c69cb2a4566f32973a1f728104e263d85f5c8ea7257b775d4072d34645'
 producer=ROOT/'verification/swift-host-operation';assert sha((producer/'seal.json').read_bytes())==identity['producerSealSHA256']=='3ea5e287af6cf1b82ae16b5db09cb3de70053f4e44fa26d86b140fbc8e7ded09'
 commands={};failed=[]
 for p in (HERE/'commands').glob('*/receipt.json'):
  r=json.loads(p.read_text());name=p.parent.name
  for stream in ['stdout','stderr']:assert sha(gzip.decompress((p.parent/(stream+'.gz')).read_bytes()))==r[stream+'SHA256']
  if r['sourceBefore']is not None:assert r['sourceBefore']==r['sourceAfter']and r['sourceBefore']in known
  assert not r['timedOut']
  if r['exitCode']!=r['expectedExitCode']:failed.append(name)
  commands[name]=r
 receipt=read('receipt.json');assert sorted(failed)==sorted(receipt['excludedReviewCommands'])==sorted(read('historical-attempts.json')['excludedCommandReceipts'])
 for name,count,filtered in [('exact-all-debug-full',265,0),('exact-all-debug-host',16,249),('adversarial-v2-all-release-reviewer',5,265),('adversarial-v2-all-release-host',16,254)]:
  r=commands[name];assert r['exitCode']==0;out=gzip.decompress((HERE/'commands'/name/'stdout.gz').read_bytes()).decode();assert re.search(r'test result: ok\. '+str(count)+r' passed; 0 failed; 0 ignored; 0 measured; '+str(filtered)+r' filtered out;',out)
 artifacts=0
 for d in (HERE/'artifacts').iterdir():
  if not d.is_dir():continue
  i=json.loads((d/'identity.json').read_text());h=sha(gzip.decompress((d/'executable.gz').read_bytes()));assert i['sourceClosure']in known
  if 'executableSHA256'in i:
   assert h==i['executableSHA256'];after=json.loads((d/'after.json').read_text());assert h==after['executableSHA256'];a=json.loads((d/'cargo-artifact.json').read_text());assert a['fresh']is False and i['targetInitiallyEmpty']and a['executable']==i['exactExecutablePath'];assert len(json.loads((d/'test-list.json').read_text()))==i['listedTests'];runs=[r for r in commands.values()if r['argv']and r['argv'][0]==a['executable']];assert len(runs)>=3 and all(r['exitCode']==0 and r['sourceBefore']==i['sourceClosure']for r in runs)
  else:
   assert h==i['executableBeforeSHA256']==i['executableAfterSHA256'];a=json.loads((d/'producer-cargo-artifact.json').read_text());assert a['executable']==i['producerExactExecutablePath']and a['fresh']is False;r=commands[d.name];assert r['argv'][0]==i['reviewExactExecutablePath']and r['sourceBefore']==i['sourceClosure']and r['exitCode']==0
  artifacts+=1
 assert artifacts==18 and read('replayed-layouts.json')['contexts']==16
 mir=read('mir-audit.json');assert(mir['production']['positions'],mir['unit']['positions'],mir['fixedPositions'],mir['totalPositions'])==(2344,2488,44,4876);assert(mir['production']['selectedBodies'],mir['unit']['selectedBodies'])==(30,32);assert len(mir['unitReturnEmptyIntervals'])==4
 from audit_mir import sections,chosen
 for config in ['production','unit']:
  original=gzip.decompress((producer/('qualified-source-mir-'+config+'.mir.gz')).read_bytes());fresh=gzip.decompress((HERE/('independent-'+config+'.mir.gz')).read_bytes());assert [v for v in sections(original)if chosen(v[0])]==[v for v in sections(fresh)if chosen(v[0])]
 assert read('independent-frozen-expansion.json')['methodCount']==39 and read('independent-frozen-expansion.json')['baselineEqualsCandidate']
 claims=read('claim-audit.json');assert(claims['libraryExecutions'],claims['hostPreprobeExecutions'],claims['frozenExecutions'])==(1014,64,64)
 packet=read('packet-audit.json');assert(packet['boundFiles'],packet['nestedCommands'],len(packet['artifacts']),len(packet['archives']))==(1671,285,91,36)
 cleanup=read('cleanup.json');assert cleanup['scratchRemoved']and cleanup['lsofObservedNoOpenHolders']and not Path(cleanup['scratch']).exists();r=commands['cleanup-holders'];assert r['exitCode']==1 and r['argv']==cleanup['lsofArgv']
 for stream in ['stdout','stderr']:assert gzip.decompress((HERE/'commands/cleanup-holders'/(stream+'.gz')).read_bytes())==b''
 if not preseal:
  seal=read('seal.json');actual={str(p.relative_to(HERE)):sha(p.read_bytes())for p in sorted(HERE.rglob('*'))if p.is_file()and p!=HERE/'seal.json'};assert actual==seal['files']and len(actual)==seal['boundFiles'];assert sha((ROOT/seal['documentation']).read_bytes())==seal['documentationSHA256']
 return dict(status='passed',sourceArchives=len(archives),commands=len(commands),artifacts=artifacts,independentTestExecutions=302,layoutReplays=16,positions=4876,excludedReviewCommands=sorted(failed),scratchRemoved=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--preseal',action='store_true');a=p.parse_args();print(json.dumps(check(a.preseal),sort_keys=True))

#!/usr/bin/env python3
"""Offline recheck of independently retained source/compiler/accounting evidence."""
import gzip,json,pathlib,tarfile
from collect import HERE,ROOT,UP,encode,sha
import audit

def verify():
 r=json.loads((HERE/'receipt.json').read_text());seal=json.loads((HERE/'seal.json').read_text());assert sha((HERE/'receipt.json').read_bytes())==seal['receiptSHA256']
 expected={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p.name not in ['receipt.json','seal.json','offline-verify.log'] and '__pycache__' not in p.parts}|{'docs/swift-memory-helper-contract-review.md'}
 assert set(r['bindings'])==expected
 for path,digest in r['bindings'].items():assert sha((ROOT/path).read_bytes())==digest,path
 assert sha((UP/'receipt.json').read_bytes())==r['producerReceiptSHA256']=='57685ea8486d7387ef708d00427bb21e0fdb61c4f97559b31ec6f03b038b20fa'
 producer=json.loads((UP/'receipt.json').read_text());assert len(producer['bindings'])==319
 for path,digest in producer['bindings'].items():assert sha((ROOT/path).read_bytes())==digest,path
 for label,expected in r['sourceClosures'].items():
  m=json.loads((HERE/(label+'-source-manifest.json')).read_text());assert sha(encode(m))==expected
  with tarfile.open(HERE/(label+'-source.tar.gz'),'r:gz') as t:
   data={}
   for x in t.getmembers():
    assert x.isfile() and x.name.startswith('vm/') and '..' not in pathlib.Path(x.name).parts and x.name[3:] not in data
    data[x.name[3:]]=sha(t.extractfile(x).read())
   assert data==m
 commands=sorted(p for p in (HERE/'commands').iterdir() if p.is_dir());assert len(commands)==r['qualifyingCommandCount']==33
 for d in commands:
  c=json.loads((d/'receipt.json').read_text());assert c['exitCode']==0 and c['sourceUnchanged'],d.name
  for k in ['stdout','stderr']:assert sha(gzip.decompress((d/(k+'.gz')).read_bytes()))==c[k+'SHA256']
  if c['sourceTreeSHA256']:
   m=json.loads((d/'source-manifest.json').read_text());assert sha(encode(m))==c['sourceTreeSHA256'] and c['sourceTreeSHA256'] in r['sourceClosures'].values()
 assert all(not r[k] for k in ['behaviorAccepted','nativeRuntime','physicalRuntime','fullTargetExecuted','liveIntegrated','liveVMEdited','Ready','publicInvocation','gaAcceptance','committed','pushed'])
 assert r['unresolvedContractBlockers']==[] and r['recommendation']=='accept-contract-type-accounting-prerequisite-only-subject-to-root'
 c=json.loads((HERE/'cleanup.json').read_text());assert c['ownedScratchRemoved'] and not pathlib.Path(c['scratch']).exists() and c['lsofExitCode']==1 and c['lsofObservedNoOpenFiles'] and c['deviceInstancesCreated']==0
 before={p:sha((ROOT/p).read_bytes()) for p in r['bindings']};audit.main();assert all(sha((ROOT/p).read_bytes())==digest for p,digest in before.items())
 print('PASS: sealed independent Load/Store contract prerequisite; no behavior/native/full-target/Ready/public/release acceptance; root decision pending.')
if __name__=='__main__':verify()

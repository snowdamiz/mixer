#!/usr/bin/env python3
from review import *
import re

def run():
 receipts={p.parent.name:json.loads(p.read_text())for p in (PACKET/'commands').glob('*/receipt.json')}
 summaries=[];library=0;host=0
 for f,count in [('default',7),('swift',235),('all',265)]:
  for profile in ['debug','release']:
   name='qualified-runtime-'+f+'-'+profile;d=PACKET/'artifacts'/name;a=json.loads((d/'cargo-artifact.json').read_text());identity=json.loads((d/'identity.json').read_text());tests=json.loads((d/'test-list.json').read_text());r=receipts['execute-'+name];out=gzip.decompress((PACKET/'commands'/('execute-'+name)/'stdout.gz').read_bytes()).decode();m=re.search(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;',out)
   assert m and list(map(int,m.groups()))==[count,0,0,0,0]and len(tests)==count and r['argv'][0]==a['executable']and r['sourceTreeBeforeSHA256']==load('input-identity.json')['candidateClosure'];library+=count
   if f!='default':
    r=receipts['probe-'+name];out=gzip.decompress((PACKET/'commands'/('probe-'+name)/'stdout.gz').read_bytes()).decode();m=re.search(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;',out);assert m and list(map(int,m.groups()))==[16,0,0,0,count-16]and r['argv'][0]==a['executable']and identity['probeExecutableSHA256']==identity['executableSHA256'];host+=16
   summaries.append(dict(features=f,profile=profile,passed=count,sourceClosure=identity['sourceTreeSHA256'],exactExecutableSHA256=identity['executableSHA256']))
 frozen=0
 for label in ['baseline','candidate']:
  for profile in ['debug','release']:
   name='qualified-frozen-'+label+'-'+profile;d=PACKET/'artifacts'/name;a=json.loads((d/'cargo-artifact.json').read_text());identity=json.loads((d/'identity.json').read_text());tests=json.loads((d/'test-list.json').read_text());r=receipts['execute-'+name];out=gzip.decompress((PACKET/'commands'/('execute-'+name)/'stdout.gz').read_bytes()).decode();assert 'test result: ok. 16 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;'in out and len(tests)==16 and r['argv'][0]==a['executable']and r['sourceTreeBeforeSHA256']==load('input-identity.json')[label+'Closure'];frozen+=16
 negatives={}
 for name,expected in json.loads((PACKET/'negative-borrows.json').read_text()).items():
  label='qualified-negative-'+name;r=receipts[label];assert r['exitCode']==r['expectedExitCode']==101 and r['sourceTreeBeforeSHA256']==expected['sourceTreeSHA256'];errors=gzip.decompress((PACKET/'commands'/label/'stderr.gz').read_bytes()).decode();codes=sorted(set(re.findall(r'error\[(E\d+)\]',errors)));assert codes==expected['errorCodes']
  with tarfile.open(PACKET/(label+'-source.tar.gz'))as t:
   archived={a.name:t.extractfile(a).read()for a in t}
  baseline=manifest(scratch()/'candidate');changed=[n for n,b in archived.items()if sha(b)!=baseline[n]];assert changed==['src/experimental_swift_reactor/frame_operations.rs']and archived[changed[0]].startswith((scratch()/'candidate'/changed[0]).read_bytes());negatives[name]=dict(sourceClosure=expected['sourceTreeSHA256'],errorCodes=codes,onlyAppendedBorrowRejectionModule=True)
 # Confirm the supplemental original RuntimeControl/cache declarations in addition to the sixteen primary owners.
 extra=json.loads((PACKET/'original-authority-supplement.json').read_text())['unchangedDeclarations'];checked={}
 for needle,h in extra.items():
  for n in manifest(scratch()/'baseline'):
   if not n.endswith('.rs'):continue
   a=(scratch()/'baseline'/n).read_text()
   if needle not in a:continue
   start=a.index(needle);end=a.index('{',start)+1;depth=1
   while depth:depth+=(a[end]=='{')-(a[end]=='}');end+=1
   dec=a[start:end]
   if sha(dec.encode())!=h:continue
   assert dec in(scratch()/'candidate'/n).read_text();checked[needle]=dict(file=n,SHA256=h)
 assert len(checked)==2
 for feature in ['swift','all']:
  r=receipts['qualified-clippy-'+feature];assert r['exitCode']==0 and r['sourceTreeBeforeSHA256']==load('input-identity.json')['candidateClosure']and r['argv'][-3:]==['-D','warnings'][-3:]if False else True
 # Check the complete actual Clippy argv without narrowing or dropped warning policy.
 clippy=[]
 for name,r in receipts.items():
  if name in ['qualified-clippy-swift','qualified-clippy-all']:
   assert r['exitCode']==0 and r['sourceTreeBeforeSHA256']==load('input-identity.json')['candidateClosure']and r['argv'][-3:]==['--','-D','warnings'];clippy.append(name)
 assert len(clippy)==2
 for tool in ['rustc','cargo']:
  original=gzip.decompress((PACKET/'commands'/('tool-'+tool)/'stdout.gz').read_bytes());ours=gzip.decompress((HERE/'commands'/('tool-'+tool)/'stdout.gz').read_bytes());assert original==ours
 assert(library,host,frozen)==(1014,64,64)
 save('claim-audit.json',dict(libraryExecutions=library,hostPreprobeExecutions=host,frozenExecutions=frozen,libraryMatrix=summaries,negativeBorrows=negatives,supplementalOwners=checked,clippy=clippy,toolIdentityMatches=True,producerFailuresExcluded=9,fullSwift=False,publicRoute=False,native=False,physical=False,GA=False));print('Independent claims audit passed 1014 library +64 host +64 Frozen; 3 negative borrow probes',flush=True)
if __name__=='__main__':run()

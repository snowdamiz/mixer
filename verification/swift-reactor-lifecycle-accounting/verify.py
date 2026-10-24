#!/usr/bin/env python3
"""Read-only archive/live verification; no compiler, test body or VM executes."""
import argparse,gzip,hashlib,json,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3'
FINAL='0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f'
def sha(data):return hashlib.sha256(data).hexdigest()
def enc(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def read(path):return json.loads(path.read_bytes())
def manifest(tree):return {str(p.relative_to(tree)):sha(p.read_bytes())for p in sorted(tree.rglob('*'))if p.is_file()}
def verify_archive(folder):
 expected=read(folder/'source-manifest.json')
 with tarfile.open(folder/'source.tar.gz','r:gz')as packed:
  members=packed.getmembers();assert len(members)==len(expected)and len({m.name for m in members})==len(members)
  for member in members:
   assert member.isfile()and member.name in expected
   assert sha(packed.extractfile(member).read())==expected[member.name],member.name
 return expected

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
 baseline=read(HERE/'baseline-manifest.json');candidate=read(HERE/'candidate-final-manifest.json')
 assert len(baseline)==130 and len(candidate)==132 and sha(enc(baseline))==BASE and sha(enc(candidate))==FINAL
 assert manifest(HERE/'baseline')==baseline and manifest(HERE/'candidate')==candidate
 changed={name for name,pin in candidate.items()if baseline.get(name)!=pin}
 assert changed=={'src/experimental_swift_reactor/lifecycle.rs','src/experimental_swift_reactor/lifecycle_tests.rs','src/experimental_swift_reactor/memory_growth_operations.rs'}
 if args.live:
  for name,pin in baseline.items():assert sha((ROOT/'vm'/name).read_bytes())==pin,name
 for name,pin in read(HERE/'input-bindings.json').items():
  assert sha((HERE/'inputs'/name).read_bytes())==pin,name
  if args.live:assert sha((ROOT/name).read_bytes())==pin,name
 receipt=read(HERE/'receipt.json');assert receipt['candidateClosure']==FINAL
 assert not receipt['accountingAccepted']and not receipt['runtimeSelected']and not receipt['gaAccepted']
 assert receipt['vmExecutions']==0 and receipt['testBodiesExecuted']==0 and not receipt['fullTargetReadHashedOrRun']and not receipt['liveVMModified']
 assert receipt['coverageLedger']==read(HERE/'authored-coverage.json')and receipt['coverageLedgerSHA256']==sha((HERE/'authored-coverage.json').read_bytes())
 assert receipt['completeOriginalPlannedMatrixSHA256']==sha((HERE/'planned-matrix-unchanged.json').read_bytes())
 assert sha((ROOT/'docs/swift-reactor-lifecycle-accounting.md').read_bytes())==receipt['documentSHA256']
 commands=read(HERE/'command-index.json');assert len(commands)==57
 failures=[]
 for indexed in commands:
  folder=HERE/indexed['attempt'];row=read(folder/'command.json');assert {k:v for k,v in indexed.items()if k!='attempt'}==row
  source=verify_archive(folder);assert sha(enc(source))==row['sourceClosure']and row['sourceUnchanged']
  assert not row['remainingGroup']
  for stream in ['stdout','stderr']:
   raw=gzip.decompress((folder/(stream+'.log.gz')).read_bytes());assert sha(raw)==row[stream+'SHA256']
  cleanup=read(folder/'cleanup.json');assert cleanup['removed']and cleanup['holderCheckEmpty']and not cleanup['remainingGroup']
  for artifact in read(folder/'artifacts.json'):
   raw=gzip.decompress((folder/artifact['path']).read_bytes());assert len(raw)==artifact['bytes']and sha(raw)==artifact['sha256']
  if row['exitCode']!=0:failures.append(indexed['attempt'])
  argv=row['argv'];assert 'run'not in argv
  if 'test'in argv:assert '--no-run'in argv
  if (folder/'list-identity.json').exists():
   listed=read(folder/'list-identity.json');assert listed['argv'][1:]==['--list']and listed['testBodiesExecuted']==0 and listed['vmExecutions']==0
   assert listed['exitCode']==0 and not listed['remainingGroup']and len(listed['lifecycleTests'])==23
   for stream in ['stdout','stderr']:assert sha(gzip.decompress((folder/('list-'+stream+'.gz')).read_bytes()))==listed[stream+'SHA256']
   clean=read(folder/'list-cleanup.json');assert clean['removed']and clean['holderCheckEmpty']and not clean['remainingGroup']
  if (folder/'overlay-cleanup.json').exists():
   clean=read(folder/'overlay-cleanup.json');assert clean['removed']and clean['holderCheckEmpty']
   projection=read(folder/'source-projection.json');assert projection['probeManifest']==source
   assert projection['originalClosure']==sha(enc(projection['originalManifest']))
   assert projection['originalClosure']in [BASE,FINAL]
 assert len(failures)==4 and {x['attempt']for x in read(HERE/'failed-compiler-attempts.json')}==set(failures)
 for cfg in [features+'-'+profile+'-'+mode for features in ['swift','all']for profile in ['debug','release']for mode in ['production','unit']]:
  final=read(HERE/f'exact-query-{cfg}.json');assert final['exitCode']==0 and final['sourceClosure']==FINAL
  old=read(HERE/'discovery-final-preinstall'/f'exact-query-{cfg}.json');assert old['exitCode']==0 and old['sourceClosure']=='779f94a6599e43a12674a7d3b20743e5df1bb23249130ed5af8453b1dd868832'
  for query in [final,old]:assert sha(gzip.decompress((HERE/query['attempt']/'exact-layouts.jsonl.gz').read_bytes()))==query['sha256']
 reconciliation=read(HERE/'reconciliation-summary.json');assert reconciliation['originalPositions']==reconciliation['finalPositions']==21364
 assert reconciliation['runtimeBodies']==268 and reconciliation['actualTypeIdentityOrLayoutChanges']==0 and reconciliation['newOrRemovedRuntimePositions']==0
 assert reconciliation['bodySHA256Changed']==96 and reconciliation['sourceInfoPositionsChanged']==7216 and reconciliation['finitePositions']==256
 annotations=json.loads(gzip.decompress((HERE/'annotation-const-proofs.json.gz').read_bytes()));assert len(annotations)==384
 assert all(r['actualLength']==6 and r['runtimeByteCredit']==0 and r['noFunctionItemOrCall']for r in annotations)
 layouts=read(HERE/'paired-layouts.json');assert len(layouts)==8
 for pair in layouts:
  assert pair['baseline']['sourceClosure']==BASE and pair['candidate']['sourceClosure']==FINAL
  assert all(r['actualUnchangedLayout']for r in pair['comparisons'].values())
  a=pair['baseline']['totals'];b=pair['candidate']['totals'];assert a['ticket_max']==b['ticket_max']==86
  assert b['header']==a['header']+b['lifecycle_permanent']and b['frame']==a['frame']+b['lifecycle_active']
  for key in ['original_growth_permanent','original_growth_active','frame_frozen_permanent','frame_frozen_active']:assert a[key]==b[key]
 inventories=read(HERE/'test-inventories.json');assert len(inventories)==4
 for inventory in inventories:
  assert inventory['sourceClosure']==FINAL and inventory['listOnly']and inventory['testBodiesExecuted']==0
  assert len(inventory['lifecycleTests'])==23 and inventory['allTestCount']==(335 if inventory['context'].startswith('swift')else 365)
 frozen=read(HERE/'frozen-identity.json');assert frozen['baseline']['methods']==frozen['candidate']['methods']and len(frozen['candidate']['methods'])==39
 session=read(HERE/'layout-tool-session.json');clean=read(HERE/session['preparation']/'final-cleanup.json');assert clean['removed']and clean['holderCheckEmpty']and not clean['sharedToolchainInstalledOrConfigured']
 cleanup=read(HERE/'cleanup-summary.json');assert cleanup['allOwnedScratchRemoved']and cleanup['immediateCommandGroupsAllEmpty']
 assert receipt['originalByteCeilings']['State']==134217728 and receipt['originalByteCeilings']['Combined']==268435456 and receipt['originalByteCeilings']['ticketMaximum']==86
 seal=HERE/'seal.json'
 if seal.exists():
  value=read(seal);files={name:pin for name,pin in manifest(HERE).items()if name!='seal.json'};assert value['files']==files and value['closureSHA256']==sha(enc(files))
 print(json.dumps({'schema':'mixer.swift-lifecycle.accounting-replay.1','verified':True,'liveRechecked':args.live,'candidateClosure':FINAL,'freshCompilerContexts':8,'pairedCompilerLayouts':16,'runtimeBodies':268,'exactPositionRoles':21364,'preservedBodySHAChanges':96,'preservedSourceInfoChanges':7216,'exactFinitePositions':256,'fullyBoundCTFEAnnotations':384,'listedLifecycleTestsPerBinary':23,'listOnlyBinaries':4,'testBodiesExecuted':0,'vmExecutions':0,'accountingAccepted':False,'runtimeSelected':False,'allOwnedScratchRemoved':True},sort_keys=True,indent=2))
if __name__=='__main__':main()

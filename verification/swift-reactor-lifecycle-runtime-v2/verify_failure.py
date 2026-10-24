#!/usr/bin/env python3
"""Read-only final V2 failure replay, including both immutable proof freezes."""
from pathlib import Path
import gzip,hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def enc(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def read(path):return json.loads(path.read_bytes())
subprocess.run([sys.executable,'-B',str(HERE/'verify_occurrences.py')],check=True,stdout=subprocess.DEVNULL)
receipt=read(HERE/'receipt.json');assert not receipt['runtimeAccepted']and not receipt['nextRepairSelectedOrImplemented']and not receipt['sourceChangedAfterProofOrRuntime']
assert not receipt['broaderRegressionsRun']and not receipt['otherFocusedContextsRun']and receipt['unchangedFailedTestReruns']==0
assert sha((HERE/'finite-representation-selection.json').read_bytes())=='807910d1c680f9e66a07738713e442e3a79d8d219ebaa7f3d91c95978121041b'
assert read(HERE/'finite-representation-selection.json')['finiteRepresentationAccepted']
assert receipt['documentSHA256']==sha((ROOT/'docs/swift-reactor-lifecycle-runtime-v2.md').read_bytes())
assert receipt['originalCoverageLedger']==read(HERE/'authored-coverage.json')
assert receipt['originalCoverageLedgerSHA256']==sha((HERE/'authored-coverage.json').read_bytes())
assert receipt['originalMatrixSHA256']==sha((HERE/'planned-matrix-unchanged.json').read_bytes())
assert receipt['nextRepairProposalSHA256']==sha((HERE/'ticket-repair-proposal.md').read_bytes())
assert receipt['independentTicketTraceSHA256']==sha((HERE/'independent-ticket-trace.json').read_bytes())
for name,pin in read(HERE/'runtime-driver-bindings.json').items():assert sha((HERE/'runtime-executed-scripts'/name).read_bytes())==pin
attempts=list((HERE/'runtime-attempts').iterdir());assert len(attempts)==1 and attempts[0].name=='focused-swift-debug'
folder=attempts[0]
for name,code in [('build',0),('list',0),('execute',101)]:
    row=read(folder/(name+'.json'));assert row['exitCode']==code and row['sourceUnchanged']and not row['remainingGroup']
    assert row['sourceClosure']==receipt['candidateClosure']
    for stream in ['stdout','stderr']:assert sha(gzip.decompress((folder/(name+'-'+stream+'.gz')).read_bytes()))==row[stream+'SHA256']
assert read(folder/'execute.json')['argv'][1:]==['swift_lifecycle_','--nocapture','--test-threads=1']
names=read(folder/'exact-tests.json');actual=read(folder/'observed-identities.json')
assert len(names)==23 and names==[r['test']for r in actual]
assert sum(r['status']=='passed'for r in actual)==22 and sum(r['status']=='failed'for r in actual)==1
raw=gzip.decompress((folder/'execute-stderr.gz').read_bytes()).decode();assert 'left: 24\n right: 22'in raw
assert 'lifecycle_tests.rs:996:5'in raw
for artifact in read(folder/'artifacts.json'):
    raw=gzip.decompress((folder/artifact['path']).read_bytes());assert sha(raw)==artifact['sha256']==read(folder/'execute.json')['executableSHA256']
clean=read(folder/'cleanup.json');assert clean['removed']and clean['holderCheckEmpty']and clean['lsofExitCode']==1
assert not (HERE/'runtime-complete.json').exists()
trace=read(HERE/'independent-ticket-trace.json');assert trace['expectedTicketDeltas']==[1,2,0]and trace['expectedLiveCacheEntries']==[0,1,3,3]
for bound in trace['sourceBindings']:
    p=HERE/'candidate'/bound['path'];assert sha(p.read_bytes())==bound['fileSHA256']
    assert ''.join(p.read_text().splitlines(keepends=True)[bound['firstLine']-1:bound['lastLine']])==bound['text']
if (HERE/'seal.json').exists():
    seal=read(HERE/'seal.json');files={str(p.relative_to(HERE)):sha(p.read_bytes())for p in sorted(HERE.rglob('*'))if p.is_file()and p.name!='seal.json'}
    assert seal['files']==files and seal['closureSHA256']==sha(enc(files))
print(json.dumps({'verified':True,'sourceClosure':receipt['candidateClosure'],'preservedProofFreezes':2,'rawPositionOccurrences':2744,'runtimeContexts':1,'testBodiesExecuted':23,'passed':22,'failed':1,'unchangedReruns':0,'broaderRegressionsRun':False,'ownedScratchRemoved':True,'nextRepairImplemented':False,'runtimeAccepted':False},sort_keys=True,indent=2))

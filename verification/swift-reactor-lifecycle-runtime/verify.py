#!/usr/bin/env python3
"""Pure read-only failed-run/source/seal replay; never reruns runtime."""
from pathlib import Path
import argparse, gzip, hashlib, json, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def sha(raw): return hashlib.sha256(raw).hexdigest()
def enc(value): return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def read(path): return json.loads(path.read_bytes())
def manifest(tree): return {str(p.relative_to(tree)):sha(p.read_bytes())for p in sorted(tree.rglob('*'))if p.is_file()}

ap=argparse.ArgumentParser();ap.add_argument('--live',action='store_true');args=ap.parse_args()
expected=read(HERE/'candidate-manifest.json')
assert len(expected)==132 and sha(enc(expected))=='0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f'
assert manifest(HERE/'candidate')==expected
with tarfile.open(HERE/'source.tar.gz','r:gz')as archive:
    members=archive.getmembers();assert len(members)==len(expected)
    assert all(m.isfile()and sha(archive.extractfile(m).read())==expected[m.name]for m in members)
assert sha((HERE/'runtime-selection.json').read_bytes())=='e6ad507b8484d1f34cef67113022927c5d55a459dd9d9caa9a224088ad7e3287'
assert sha((HERE/'accounting-seal.json').read_bytes())=='02b53f531a4cb4852cc7e99104d13bb09e969f9d6b018c4d5d8fd6cd0d3dbbdd'
if args.live:
    accounting=ROOT/'verification/swift-reactor-lifecycle-accounting'
    assert manifest(accounting/'candidate')==expected
    for name,pin in read(accounting/'baseline-manifest.json').items():assert sha((ROOT/'vm'/name).read_bytes())==pin
    assert (HERE/'runtime-selection.json').read_bytes()==(ROOT/'verification/swift-reactor-lifecycle-accounting-root-review/runtime-selection.json').read_bytes()
    for name in ['authored-coverage.json','planned-matrix-unchanged.json']:
        assert (HERE/name).read_bytes()==(accounting/name).read_bytes()
receipt=read(HERE/'receipt.json')
assert receipt['runtimeSelected']and not receipt['runtimeAccepted']and not receipt['repairSelectedOrImplemented']and not receipt['fullPlannedSLRowsComplete']
assert not receipt['full53MBTargetReadHashedOrRun']and not receipt['liveVMModified']and not receipt['nativeInstancesCreated']
assert receipt['remainingCoverageLedger']==read(HERE/'authored-coverage.json')
assert receipt['remainingCoverageLedgerSHA256']==sha((HERE/'authored-coverage.json').read_bytes())
assert receipt['originalMatrixSHA256']==sha((HERE/'planned-matrix-unchanged.json').read_bytes())
assert receipt['repairProposalSHA256']==sha((HERE/'repair-proposal.md').read_bytes())
assert receipt['sourceTraceSHA256']==sha((HERE/'independent-source-traces.json').read_bytes())
assert receipt['documentSHA256']==sha((ROOT/'docs/swift-reactor-lifecycle-runtime.md').read_bytes())
folder=HERE/'attempts/swift-debug'
for name,code in [('build',0),('list',0),('execute',101)]:
    row=read(folder/(name+'.json'));assert row['launched']and row['exitCode']==code and row['sourceUnchanged']and not row['remainingGroup']
    assert row['sourceClosure']==receipt['candidateClosure']
    for stream in ['stdout','stderr']:assert sha(gzip.decompress((folder/(name+'-'+stream+'.gz')).read_bytes()))==row[stream+'SHA256']
assert read(folder/'execute.json')['argv'][1:]==['swift_lifecycle_','--nocapture','--test-threads=1']
assert read(folder/'list.json')['argv'][1:]==['swift_lifecycle_','--list']
names=read(folder/'exact-tests.json');assert len(names)==23 and len(set(names))==23
identities=read(HERE/'observed-identities.json')
assert [r['test']for r in identities]==names and sum(r['status']=='passed'for r in identities)==21 and sum(r['status']=='failed'for r in identities)==2
raw=gzip.decompress((folder/'execute-stdout.gz').read_bytes()).decode()
assert '21 passed; 2 failed; 0 ignored; 0 measured; 312 filtered out;'in raw
for row in identities:
    assert 'test '+row['test']+' ... '+('ok'if row['status']=='passed'else'FAILED')in raw
    assert not row['fullPlannedSLRowComplete']
artifacts=read(folder/'artifacts.json');assert len(artifacts)==1
for item in artifacts:
    raw=gzip.decompress((folder/item['path']).read_bytes());assert sha(raw)==item['sha256']and len(raw)==item['bytes']
    assert sha(raw)==read(folder/'execute.json')['executableSHA256']==read(folder/'list.json')['executableSHA256']
clean=read(folder/'cleanup.json');assert clean['removed']and clean['holderCheckEmpty']and clean['lsofExitCode']==1
assert not list((HERE/'attempts').glob('swift-release'))and not list((HERE/'attempts').glob('all-*'))
assert not (HERE/'focused-complete.json').exists()
trace=read(HERE/'independent-source-traces.json')
for binding in trace['sourceBindings']:
    p=HERE/'candidate'/binding['path'];assert sha(p.read_bytes())==binding['fullSourceSHA256']
    assert ''.join(p.read_text().splitlines(keepends=True)[binding['firstLine']-1:binding['lastLine']])==binding['text']
assert sum(row['credits']for row in trace['SL09']['constructorExecutionWorkOperations'])==38319823
assert [r['total']for r in trace['SL13']['warmOperations']]==[4,6]
if (HERE/'seal.json').exists():
    seal=read(HERE/'seal.json');files={k:v for k,v in manifest(HERE).items()if k!='seal.json'}
    assert seal['files']==files and seal['closureSHA256']==sha(enc(files))
print(json.dumps({'schema':'mixer.swift-lifecycle.runtime-failure-replay.1','verified':True,'liveRechecked':args.live,'sourceClosure':receipt['candidateClosure'],'testBodiesExecuted':23,'passed':21,'failed':2,'matrixStopped':True,'unchangedReruns':0,'ownedScratchRemoved':True,'runtimeAccepted':False,'repairImplemented':False},sort_keys=True,indent=2))

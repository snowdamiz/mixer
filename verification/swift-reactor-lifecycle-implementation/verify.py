#!/usr/bin/env python3
"""Verify source/compiler/cleanup evidence without executing guest code."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASELINE='3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3'
FINAL='36369eba832214bab721d63aaad021e929ea5f13aa96c780bb5ebceacd99f20b'
ATTEMPTS={'20261024T195917546437Z':False,'20261024T200049805938Z':True}
ALLOWED={'src/experimental_swift_reactor/lifecycle.rs','src/experimental_swift_reactor/memory_growth_operations.rs'}
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def manifest(tree):return {str(p.relative_to(tree)):sha(p.read_bytes()) for p in sorted(tree.rglob('*')) if p.is_file()}
def read(path):return json.loads(path.read_bytes())
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    baseline=read(HERE/'baseline-manifest.json');assert len(baseline)==130 and sha(encoded(baseline))==BASELINE
    inputs=read(HERE/'input-bindings.json')
    for name,pin in inputs.items():
        saved=HERE/'inputs'/name
        assert sha(saved.read_bytes())==pin,name
        if args.live:assert sha((ROOT/name).read_bytes())==pin,name
    candidate=manifest(HERE/'candidate');assert len(candidate)==131 and sha(encoded(candidate))==FINAL
    assert set(baseline)<=set(candidate)
    assert {name for name,pin in candidate.items() if baseline.get(name)!=pin}==ALLOWED
    for name,pin in baseline.items():
        if name not in ALLOWED:assert candidate[name]==pin,name
        if args.live:assert sha((ROOT/'vm'/name).read_bytes())==pin,name
    for attempt,success in ATTEMPTS.items():
        folder=HERE/'attempts'/attempt
        source_manifest=read(folder/'candidate-manifest.json');closure=sha(encoded(source_manifest))
        assert len(source_manifest)==131
        assert {name for name,pin in source_manifest.items() if baseline.get(name)!=pin}==ALLOWED
        with tarfile.open(folder/'candidate-source.tar.gz','r:gz') as packed:
            members=packed.getmembers();assert len(members)==len(source_manifest)
            assert len({m.name for m in members})==len(members)
            for member in members:
                assert member.isfile() and member.name in source_manifest
                assert sha(packed.extractfile(member).read())==source_manifest[member.name],member.name
        receipt=read(folder/'receipt.json');commands=read(folder/'commands.json');cleanup=read(folder/'cleanup.json')
        assert receipt['candidateClosure']==closure and receipt['baselineClosure']==BASELINE
        assert receipt['commands']==commands and len(commands)==7
        assert receipt['fullOwnerEntryBorrowRouteProven']==success
        assert receipt['liveBaselineRecheckedAfter'] and receipt['cleanupPassed']
        assert receipt['vmExecutions']==0 and receipt['nativeInstancesCreated']==0 and not receipt['targetArtifactRead']
        assert not receipt['accountingAccepted'] and not receipt['runtimeSelected']
        assert cleanup['groupsEmpty'] and cleanup['holderCheckEmpty'] and cleanup['ownedScratchRemoved']
        assert not any(cleanup['remainingCommandGroups'].values())
        if success:assert closure==FINAL
        expected={'swift-debug','swift-release','all-debug','all-release'}
        assert {row['label'] for row in commands if row['target']}==expected
        for row in commands:
            output=gzip.decompress((folder/row['log']).read_bytes());assert sha(output)==row['outputSHA256']
            assert row['sourceBefore']==closure==row['sourceAfter'] and row['sourceUnchanged']
            assert not row['timedOut'] and not row['remainingGroup']
            assert row['exitCode']==(0 if success or not row['target'] else 101)
            if row['target']:
                argv=row['argv'];assert argv[:7]==[str(Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo')),'check','--lib','--locked','--offline','--no-default-features',('--all-features' if row['label'].startswith('all') else '--features')]
                assert ('--release' in argv)==row['label'].endswith('release')
                if not success:assert b'error[E0506]' in output and b'owner.lifecycle' in output
    summary=read(HERE/'receipt.json')
    assert summary['candidateClosure']==FINAL and summary['fullOwnerEntryBorrowRouteProven']
    assert not summary['accountingAccepted'] and not summary['runtimeSelected'] and not summary['implementationAccepted']
    assert sha((ROOT/'docs/swift-reactor-lifecycle-implementation.md').read_bytes())==summary['documentSHA256']
    assert sha((HERE/'candidate.diff').read_bytes())==summary['deltaSHA256']
    seal=HERE/'seal.json'
    if seal.exists():
        sealed=read(seal)
        actual={name:pin for name,pin in manifest(HERE).items() if name!='seal.json'}
        assert sealed['files']==actual
        assert sealed['closureSHA256']==sha(encoded(actual))
    print(json.dumps({'schema':'mixer.swift-lifecycle.owner-entry-verification.1','verified':True,'liveRechecked':args.live,'baselineClosure':BASELINE,'candidateClosure':FINAL,'successfulProductionContexts':4,'preservedFailedProductionContexts':4,'vmExecutions':0,'accountingAccepted':False,'runtimeSelected':False},sort_keys=True,indent=2))
if __name__=='__main__':main()

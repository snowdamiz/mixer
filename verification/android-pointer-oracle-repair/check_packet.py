#!/usr/bin/env python3
"""Exact immutable host packet replay; only the designated contained runtime subtree is excluded."""
import json
from pathlib import Path
import common

REVIEW=common.ROOT/'verification/android-pointer-fixture-review'
REVIEW_SEAL_SHA256='0942e53a9de5b6fcf87255b7324ced091cd42b4ae42c7628c4698164a2c21f13'
RUNTIME_POLICY='Only verification/android-pointer-oracle-repair/runtime/runtime-N is mutable runtime evidence; root dispatch required, contained fresh directory, no symlinks; each run seals its own complete receipt recursively.'

def upstream():
    count=common.preserved_inputs();seal=REVIEW/'artifact-seal.json'
    if common.sha(seal)!=REVIEW_SEAL_SHA256:raise ValueError('immutable independent review seal drift')
    expected=json.loads(seal.read_text())['files']
    if len(expected)!=42:raise ValueError('exact42 independent review bindings required')
    for name,value in expected.items():
        path=common.ROOT/name
        if path.is_symlink() or {'bytes':path.stat().st_size,'sha256':common.sha(path)}!=value:raise ValueError('immutable independent review binding drift '+name)
    return {'candidate4Files':count,'candidate4PacketSealSHA256':common.PRIOR_SEAL,'reviewFiles':len(expected),'reviewSealSHA256':REVIEW_SEAL_SHA256,'originalContractAcceptanceSHA256':common.ROOT_CONTRACT_SHA256}

def files():
    here=common.HERE;runtime=here/'runtime'
    if here.is_symlink() or runtime.is_symlink() or runtime.resolve()!=here.resolve()/'runtime':raise ValueError('runtime or host packet path escape/symlink')
    own=[]
    for path in sorted(here.rglob('*')):
        if path.is_symlink():raise ValueError('host packet/runtime symlink refused')
        if path==runtime or path.is_relative_to(runtime):continue
        if path.is_dir() and path.name in ('.build','.scratch','__pycache__'):raise ValueError('owned generated scratch remains')
        if path.is_file() and path!=here/'packet-seal.json':own.append(path)
    doc=common.ROOT/'docs/android-pointer-oracle-repair.md'
    if doc.is_symlink():raise ValueError('host document symlink refused')
    own.append(doc)
    return {str(p.relative_to(common.ROOT)):{'bytes':p.stat().st_size,'sha256':common.sha(p)} for p in sorted(own)}

def check():
    expected=json.loads((common.HERE/'packet-seal.json').read_text())
    if expected['runtimeSubtreeExcluded']!='verification/android-pointer-oracle-repair/runtime' or expected['files']!=files():raise ValueError('exact immutable host packet membership/hash/size drift')
    packet=json.loads((common.HERE/'packet.json').read_text())
    if packet['nativeRuntime']!='NOT RUN' or packet['nativeAcceptance'] or packet['nativeDispatchAuthorizedByThisPacket'] or packet['nativeInstancesStarted'] or packet['physicalTargetsQueried']:raise ValueError('host packet claims native authority/evidence')
    if packet['upstream']!=upstream():raise ValueError('upstream proof binding differs')
    return {'status':'passed-exact-recursive-pointer-oracle-repair-host-packet','hostFiles':len(expected['files']),'upstream':packet['upstream'],'packetSealSHA256':common.sha(common.HERE/'packet-seal.json'),'runnerContractSHA256':packet['runnerContractSHA256'],'concreteRunnerSHA256':packet['concreteRunnerSHA256'],'runtimeSubtreeExcluded':expected['runtimeSubtreeExcluded'],'nativeRuntime':'NOT RUN','nativeDispatchAuthorizedByThisPacket':False}

if __name__=='__main__':print(json.dumps(check(),indent=2,sort_keys=True))

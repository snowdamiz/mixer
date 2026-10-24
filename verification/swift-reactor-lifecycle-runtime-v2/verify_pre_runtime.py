#!/usr/bin/env python3
"""Read-only finite proof/source replay; no compiler or runtime executes."""
from pathlib import Path
import gzip,hashlib,json,re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def enc(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def read(path):return json.loads(path.read_bytes())
def manifest(tree):return {str(p.relative_to(tree)):sha(p.read_bytes())for p in sorted(tree.rglob('*'))if p.is_file()}
def bounds(text,name):
    a=text.index('fn '+name+'(');b=text.index('{',a);end=b+1;depth=1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return b,end
def mask(text):
    for name in ['swift_lifecycle_sl09_initializer_exact_resource_failures','swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage']:
        a,b=bounds(text,name);text=text[:a]+'{SELECTED_BODY}'+text[b:]
    return text
source=read(HERE/'candidate-manifest.json');assert manifest(HERE/'candidate')==source
assert sha(enc(source))=='0fa7ae254ac2b3aa3390e6fbc935e920422fc9024db220256074ec6ef4e3cd56'
oldroot=ROOT/'verification/swift-reactor-lifecycle-accounting'
old=read(oldroot/'candidate-final-manifest.json')
file='src/experimental_swift_reactor/lifecycle_tests.rs'
assert [x for x in source if old[x]!=source[x]]==[file]
assert mask((oldroot/'candidate'/file).read_text())==mask((HERE/'candidate'/file).read_text())
assert sha((HERE/'test-repair-selection.json').read_bytes())=='8712df6cbe4ec813b3e5e40169425711b0b3aeb298411d99a06c60232d796a46'
summary=read(HERE/'unchanged-runtime-proof.json');assert summary['runtimeBodies']==160 and summary['rawBodyDifferences']==34
assert summary['sourceInfoChanges']==134 and summary['sourceCoordinatesAndScopeChanges']==0 and summary['canonicalActualBodyChanges']==0
bodies=json.loads(gzip.decompress((HERE/'runtime-body-reconciliation.json.gz').read_bytes()))
for row in bodies:
    cfg=next(x for x in summary['contexts']if x['config']==row['config']);mapping=cfg['finiteAllocationBijection'];assert len(set(mapping.values()))==len(mapping)
    before=row['oldBody']['mir'];after=row['newBody']['mir']
    assert sha(before.encode())==row['oldFullBodySHA256']and sha(after.encode())==row['newFullBodySHA256']
    assert set(re.findall(r'\balloc\d+\b',before))<=set(mapping)
    assert re.sub(r'\balloc\d+\b',lambda m:mapping[m[0]],before)==after
roles=read(HERE/'role-reconciliation-summary.json');assert roles['unitFourRolePositions']==11760 and roles['sourceInfoRoleChanges']==632
frozen=read(HERE/'frozen-identity-proof.json');assert len(frozen['oldExpandedMethods'])==39 and frozen['oldExpandedMethods']==frozen['newExpandedMethods']
pins=read(HERE/'compiler-pin-and-command-cleanup-proof.json');assert len(pins)==5 and all(x['cleanupComplete']and x['exitCode']==0 for x in pins)
assert read(HERE/'metadata-tool-cleanup.json')['removed']
if (HERE/'pre-runtime-freeze.json').exists():
    freeze=read(HERE/'pre-runtime-freeze.json')
    for name,pin in freeze['files'].items():assert sha((HERE/name).read_bytes())==pin,name
    assert sha(enc(freeze['files']))==freeze['closureSHA256']
print(json.dumps({'verified':True,'sourceClosure':summary['sourceClosure'],'runtimeBodies':160,'rawMIRAllocationLabelChanges':34,'sourceInfoHygieneChanges':134,'sourceInfoRoleChanges':632,'unexplainedInstructionTypeLayoutChanges':0,'FrozenMethodsExact':39,'runtimeExecuted':False,'finiteRepresentationSelectionPending':True},sort_keys=True,indent=2))

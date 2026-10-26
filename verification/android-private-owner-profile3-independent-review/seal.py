#!/usr/bin/env python3
"""Audit retained independent evidence and seal it without rerunning product tests."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
PACKET=ROOT/'verification/android-private-owner-profile3-integration/candidate4-qualification'

def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def load(path):return json.loads(path.read_text())
def save(path,data):path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def require(condition,message):
    if not condition:raise RuntimeError(message)

receipt=load(BASE/'receipt.json')
require(receipt['status']=='passed-independent-profile3-host-review-awaiting-root','review status')
require(identity((BASE/'review.py').read_bytes())==receipt['runner'],'runner bytes changed')
for name,value in load(BASE/'source-binding.json')['files'].items():
    require(identity((BASE/'source'/name).read_bytes())==value,'own snapshot drift '+name)
producer_sources=load(PACKET/'source-binding.json')['files']
for name,value in producer_sources.items():
    require(identity((PACKET/'source'/name).read_bytes())==value,'producer snapshot drift '+name)
    require(identity((ROOT/name).read_bytes())==value,'live source356 drift '+name)
for name,value in load(ROOT/'verification/android-private-owner-integration-implementation/candidate-4/source-map.json').items():
    require(identity((ROOT/name).read_bytes())==value,'canonical309 drift '+name)
pins={
 'verification/android-private-owner-profile3-integration/candidate4-qualification/manifest.json':'ff947ccf16b055e10e3458bd9b8161b597b7744131c5eb8d7f67377736c134a6',
 'verification/android-private-owner-profile3-integration/candidate4-qualification/seal-receipt.json':'a86a971a8be3d62b5c5ae8a03cc0aee6192941d6c138d26b39d1f390dc417251',
 'verification/android-private-owner-effect-integration-root-review/candidate-4-profile-selection.json':'fc0e083821790e12c1c12b709f2a8e7c44a40ff457e4183853ef6adbdd919106',
 'verification/android-private-owner-integration-implementation/candidate-4/manifest.json':'69fcd445119c0ea311c11cf97587d591d87ba1c5bd2d5b3c0a722116f66231c5',
}
for name,sha in pins.items():require(identity((ROOT/name).read_bytes())['sha256']==sha,'external pin changed '+name)
products=load(BASE/'products-before-cleanup.json')
commands=load(BASE/'commands.json')
for command in commands:
    folder=BASE/'commands'/command['label']
    require(load(folder/'result.json')==command,'aggregate command mismatch')
    for stream in ('stdout','stderr'):
        require(identity((folder/stream).read_bytes())==command[stream],'stream mismatch')
    require(command['exit']==command['expected_exit'] and not command['timed_out'] and not command['output_limit_exceeded'],'unexpected command status')
    if command['argv'][0].endswith('/mixer'):
        key=str(Path(command['argv'][0]).relative_to(BASE))
        require({k:command['executable'][k] for k in ('bytes','sha256')}==products[key],'CLI product identity')
for path in receipt['cleanup']['removed_owned_scratch']:require(not (BASE/path).exists(),'scratch remains')
host=(BASE/'commands/independent-copied-host-tests/stdout').read_text()
require('Test run with 3 tests in 1 suite passed' in host,'host method evidence')
test=(BASE/'IndependentReviewTests.swift').read_text()
require(test.count('#expect(')==18 and test.count('#require(')==2,'assertion sites changed')
binding=load(BASE/'consumer-binding.json')
for folder,key in [('ReviewConsumer','created'),('CopiedReviewConsumer','exported_customized')]:
    for name,value in binding[key].items():require(identity((BASE/folder/name).read_bytes())==value,'consumer changed')
doc=ROOT/'docs/android-private-owner-profile3-independent-review.md'
save(BASE/'final-audit.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'live_source356_and_canonical309_unchanged':True,'external_pins':pins,'command_results_verified':len(commands),
 'own156_snapshot_unchanged':True,'Swift_methods':3,'static_expect_sites':18,'shared_require_sites':2,
 'producer_Swift_methods_per_configuration':13,'producer_Swift_parameterized_cases':71,
 'producer_Swift_total_invocations_per_configuration':77,'producer_Python_methods_per_mode':[10,9,11],
 'top_level_run':{'tool':'exec_command','cmd':'python3 -B verification/android-private-owner-profile3-independent-review/review.py','observed_exit':0},
 'documentation':{'path':str(doc.relative_to(ROOT)),**identity(doc.read_bytes())},
 'tool_identity_scope':'direct executables and resolved Swift frontend only; no descendant launch/dependency trace',
 'no_native_owner_or_GA_acceptance':True})
members={}
for path in sorted(BASE.rglob('*')):
    if path.is_file() and path.name not in ('manifest.json','seal-receipt.json'):
        require(not path.is_symlink(),'symlink in packet')
        members[path.relative_to(BASE).as_posix()]=identity(path.read_bytes())
save(BASE/'manifest.json',{'schema':1,'members':len(members),'bytes':sum(v['bytes'] for v in members.values()),'files':members})
save(BASE/'seal-receipt.json',{'schema':1,'status':'sealed-independent-host-review-awaiting-root',
 'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python_version':sys.version,
 'python':{'path':str(Path(sys.executable).resolve()),**identity(Path(sys.executable).resolve().read_bytes())},
 'argv':[sys.executable,*sys.argv],'script':identity(Path(__file__).read_bytes()),
 'manifest':identity((BASE/'manifest.json').read_bytes()),'members':len(members),
 'documentation':{'path':str(doc.relative_to(ROOT)),**identity(doc.read_bytes())},
 'commands':len(commands),'native_owner_accepted':False,'GA_qualified':False})
print(json.dumps({'status':'sealed','manifest':identity((BASE/'manifest.json').read_bytes()),
 'seal_receipt':identity((BASE/'seal-receipt.json').read_bytes()),'members':len(members)}))

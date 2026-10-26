#!/usr/bin/env python3
"""Audit retained independent evidence and seal it without rerunning product tests."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
PACKET=ROOT/'verification/android-private-owner-profile3-integration/candidate5-qualification'

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
for name,value in load(ROOT/'verification/android-private-owner-integration-implementation/candidate-5/source-map.json').items():
    require(identity((ROOT/name).read_bytes())==value,'canonical311 drift '+name)
pins={
 'verification/android-private-owner-profile3-integration/candidate5-qualification/manifest.json':'31e034832247144f6f042006f4725dbf0242408ec33d61b9d1cedaa688b90ec4',
 'verification/android-private-owner-profile3-integration/candidate5-qualification/seal-receipt.json':'8ffb4ec37ff4189a330dfb0c32b427d7399365fdbf3c94a5a64ea6b70cf92db0',
 'verification/android-private-owner-effect-integration-root-review/candidate-5-profile-selection.json':'990f8dff5a27f30892aa5671394f072f5a093658a8b71eb6bbe1848c34bcbe2d',
 'verification/android-private-owner-integration-implementation/candidate-5/manifest.json':'59a820bd3cd7e01ead02114293028985f64a42eebc36094cef9d76f516eee1f1',
}
pins.update(load(BASE/'producer-audit.json')['external_pins'])
for name,sha in pins.items():require(identity((ROOT/name).read_bytes())['sha256']==sha,'external pin changed '+name)
for other in (PACKET,ROOT/'verification/android-private-owner-profile3-independent-review'):
    old=load(other/'manifest.json')
    for name,value in old['files'].items():require(identity((other/name).read_bytes())==value,'sealed input member drift '+name)
    present={p.relative_to(other).as_posix() for p in other.rglob('*') if p.is_file()}
    require(present==set(old['files'])|{'manifest.json','seal-receipt.json'},'sealed input closed inventory drift')
for label,count,suites in [('copied-shared-app-host-tests',4,0),('copied-native-session-host-tests',3,1),('copied-custom-factory-reducer-test',1,0)]:
    text=(PACKET/'commands'/label/'stdout').read_text()
    require('Test run with '+str(count)+' test'+('s' if count!=1 else '')+' in '+str(suites)+' suite'+('s' if suites!=1 else '')+' passed' in text,'producer copied host count '+label)
review=load(BASE/'source-review.json')
previous_root=ROOT/'verification/android-private-owner-profile3-independent-review/source'
for item in review['CLI_selected_inputs']:
    before=(previous_root/item['path']).read_bytes();after=(BASE/'source'/item['path']).read_bytes()
    require(identity(before)==item['prior'] and identity(after)==item['selected'] and (before==after)==item['unchanged'],'source delta identity')
previous=load(ROOT/'verification/android-private-owner-integration-implementation/candidate-4/profile-proposal.json')
current=load(ROOT/'verification/android-private-owner-integration-implementation/candidate-5/profile-proposal.json')
owner='app/src/dev/mixer/android/NativeOwnerV2.java'
a=(previous_root/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
z=(BASE/'source/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
for x,y in [(previous['adapter_compatibility_sha256'],current['adapter_compatibility_sha256']),
            (str(previous['adapter_files'][owner]['bytes']),str(current['adapter_files'][owner]['bytes'])),
            (previous['adapter_files'][owner]['sha256'],current['adapter_files'][owner]['sha256'])]:a=a.replace(x,y)
require(a==z,'normalized compiled profile delta')
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
require(len(commands)==69 and sum(c['expected_exit']==0 for c in commands)==15 and sum(c['expected_exit']==1 for c in commands)==54,'independent command counts')
require(receipt['independent_mutation_fixtures']==9 and receipt['independent_preaccess_traps']==9,'negative controls')
host=(BASE/'commands/independent-copied-host-tests/stdout').read_text()
require('Test run with 3 tests in 1 suite passed' in host,'host method evidence')
test=(BASE/'IndependentReviewTests.swift').read_text()
require(test.count('#expect(')==18 and test.count('#require(')==2,'assertion sites changed')
binding=load(BASE/'consumer-binding.json')
for folder,key in [('ReviewConsumer','created'),('CopiedReviewConsumer','exported_customized')]:
    for name,value in binding[key].items():require(identity((BASE/folder/name).read_bytes())==value,'consumer changed')
doc=ROOT/'docs/android-private-owner-profile3-candidate5-review.md'
save(BASE/'final-audit.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'live_source356_and_canonical311_unchanged':True,'external_pins':pins,'command_results_verified':len(commands),
 'own156_snapshot_unchanged':True,'Swift_methods':3,'static_expect_sites':18,'shared_require_sites':2,
 'producer_Swift_methods_per_configuration':13,'producer_Swift_parameterized_cases':71,
 'producer_Swift_total_invocations_per_configuration':77,'producer_Python_methods_per_mode':[10,9,11],
 'top_level_run':{'tool':'exec_command','cmd':'python3 -B verification/android-private-owner-profile3-candidate5-independent-review/review.py','observed_exit':0},
 'documentation':{'path':str(doc.relative_to(ROOT)),**identity(doc.read_bytes())},
 'tool_identity_scope':'direct executables and resolved Swift frontend only; no descendant launch/dependency trace',
 'no_native_owner_or_GA_acceptance':True,'successful_commands':15,'expected_refusals':54,'independent_preaccess_traps':9,'no_independent_product_test_failures':True,'source_classification':'source-review.json','preparation_failures':'preparation.json'})
members={}
for path in sorted(BASE.rglob('*')):
    if path.is_file() and path.name not in ('manifest.json','seal-receipt.json'):
        require(not path.is_symlink(),'symlink in packet')
        members[path.relative_to(BASE).as_posix()]=identity(path.read_bytes())
save(BASE/'manifest.json',{'schema':1,'members':len(members),'bytes':sum(v['bytes'] for v in members.values()),'files':members})
save(BASE/'seal-receipt.json',{'schema':1,'status':'sealed-independent-host-review-awaiting-root',
 'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python_version':sys.version,
 'python':{'path':str(Path(sys.executable).resolve()),**identity(Path(sys.executable).resolve().read_bytes())},
 'argv':[sys.executable,*sys.argv],'script':identity(Path(__file__).read_bytes()),'orig_argv':sys.orig_argv,
 'manifest':identity((BASE/'manifest.json').read_bytes()),'members':len(members),
 'documentation':{'path':str(doc.relative_to(ROOT)),**identity(doc.read_bytes())},
 'commands':len(commands),'native_owner_accepted':False,'GA_qualified':False})
print(json.dumps({'status':'sealed','manifest':identity((BASE/'manifest.json').read_bytes()),
 'seal_receipt':identity((BASE/'seal-receipt.json').read_bytes()),'members':len(members)}))

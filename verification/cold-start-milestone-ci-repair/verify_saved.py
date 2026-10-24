#!/usr/bin/env python3
"""Strictly validate retained qualifying logs and exact source bindings, without running UI."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
digest = lambda v: hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--name', default='final-1')
args = parser.parse_args()
assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
out = HERE/args.name
r = json.loads((out/'receipt.json').read_text())
assert r['status']=='passed',r.get('problem')
assert r['modes']==['debug','release','tsan']
assert r['driver_sha256']==sha(HERE/'run.py')
assert r['source_manifest_sha256']==sha(out/'source-manifest.json')
assert r['derived_manifest_sha256']==sha(out/'derived-manifest.json')
manifest=json.loads((out/'source-manifest.json').read_text())
derived=json.loads((out/'derived-manifest.json').read_text())
assert manifest['files']==r['input_files'] and manifest['sha256']==digest(manifest['files'])==r['input_tree_sha256']
assert derived['files']==r['source_files'] and derived['sha256']==digest(derived['files'])==r['source_tree_sha256']
archive=ROOT/r['source_archive']['path']; assert sha(archive)==r['source_archive']['sha256']
with tarfile.open(archive) as tar:
    members=tar.getmembers()
    assert len(members)==len(manifest['files']) and len({m.name for m in members})==len(members)
    for m in members:
        assert m.isfile() and m.name in manifest['files'] and '..' not in Path(m.name).parts
        assert hashlib.sha256(tar.extractfile(m).read()).hexdigest()==manifest['files'][m.name],m.name
    # The runtime/test fixtures and dependencies are exact saved bytes. Current
    # source checks cover only these lanes; active Rust work is deliberately not
    # read as the pinned native archive source.
    for relative,h in manifest['files'].items():
        if relative.startswith(('sdk/','updates/','runtime-identity/','experimental-capability-runtime/','capability-activation/')):
            assert sha(ROOT/relative)==h,relative
        if relative.startswith('vm/'):
            data=subprocess.check_output(['git','show',r['native_source_revision']+':'+relative],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==h,relative
    for name in ['MilestoneProbe.swift','TestSupport.swift','run.py']:
        assert sha(HERE/name)==manifest['files']['support/'+name]
for relative,h in derived['files'].items():
    if relative.startswith('derived/'):
        assert sha(out/relative)==h,relative
assert r['native_archive']['source_revision']==r['native_source_revision']
assert r['native_archive']['source_files']=={k:v for k,v in manifest['files'].items() if k.startswith('vm/')}
assert re.fullmatch('[0-9a-f]{64}',r['native_archive']['sha256'])
commands={c['name']:c for c in r['commands']}; assert len(commands)==len(r['commands'])
logs={}
for name,c in commands.items():
    path=ROOT/c['log']; assert sha(path)==c['sha256'],name
    assert c['exit']==c['expected_exit'],name
    logs[name]=path.read_text()
    assert 'WARNING: ThreadSanitizer' not in logs[name],name
    assert 'TIMEOUT' not in logs[name],name
assert commands['native-build']['exit']==0
assert 'experimental-capability-native' in commands['native-build']['argv']
assert '--locked' in commands['native-build']['argv'] and '--offline' in commands['native-build']['argv']
assert Path(commands['native-build']['environment']['CARGO_TARGET_DIR']).name=='rust-target'
for mode in r['modes']:
    full=logs[mode+'-repaired-unmodified']; assert 'Executed 8 tests, with 0 failures' in full
    names=re.findall(r"Test Case '-\[MixerMilestoneCITests.CapabilityColdStartRuntimeTests (\w+)\]' passed",full)
    assert len(names)==len(set(names))==8
    old=logs[mode+'-original-after-timer']; assert commands[mode+'-original-after-timer']['exit']==1
    assert 'Executed 1 test, with 1 failure (1 unexpected)' in old
    assert 'actual-busy held=true' in old and 'notification-admitted timerFired=true' in old
    assert 'caught error: "Capability cold-start runtime rejected"' in old
    assert 'original-call notificationHeld=true timerFired=true' in old
    for order in ['after-timer','before-timer']:
        log=logs[mode+'-repaired-'+order]
        assert 'Executed 1 test, with 0 failures' in log
        expected='true' if order=='after-timer' else 'false'
        assert 'notification-admitted timerFired='+expected in log
        assert re.search('MILESTONE_CI held '+order+r' retries=([3-9]|[1-9][0-9]+) reported=\[\] returned=false timerFired='+expected,log)
        report='first_screen' if order=='after-timer' else 'feature_started'
        assert 'MILESTONE_CI released '+order+' reported=["'+report+'"] returned=true timerFired='+expected in log
        assert 'actual-report feature_started' in log and 'actual-report first_screen' in log
    errors=logs[mode+'-repaired-errors']; assert 'Executed 1 test, with 0 failures' in errors
    assert 'actual-busy held=true' in errors and 'invalid-propagated capability.runtime.milestone' in errors and 'closed-propagated capability.runtime.closed' in errors
    deadline=logs[mode+'-repaired-deadline']; assert 'Executed 1 test, with 0 failures' in deadline
    assert re.search(r'MILESTONE_CI deadline actualBusy=[1-9][0-9]+ reports=\[\] elapsed=',deadline)
    for name,c in commands.items():
        if name.startswith(mode+'-') and ('-compile-' in name or name.endswith('-link')):
            args=c['argv']
            if mode=='tsan': assert any(a in args for a in ['-sanitize=thread','-fsanitize=thread']),name
            if mode=='release': assert any(a in args for a in ['-O','-O2']),name
    assert set(r['generated_modulemaps'][mode])=={'modulemaps/'+n+'.modulemap' for n in ['MixerCapabilityIO','MixerDurableIO','MixerCapabilityDurableIO','CMixerVMCapability']}
    for item in r['generated_modulemaps'][mode].values(): assert hashlib.sha256(item['text'].encode()).hexdigest()==item['sha256']
assert sum(c['exit']!=0 for c in r['commands'])==3
cleanup=HERE/'cleanup.json'
if cleanup.exists():
    cleaned=json.loads(cleanup.read_text())
    assert {Path(row['path']).name for row in cleaned['rows']}=={'candidate-1','candidate-2','final-1'}
    for row in cleaned['rows']:
        assert row['removed'] and not (ROOT/row['path']).exists()
        assert row['exit']==1 and sha(ROOT/row['log'])==row['sha256']
        assert not (ROOT/row['log']).read_bytes()
    assert sum(row['bytes'] for row in cleaned['rows'])==cleaned['total_bytes_removed']
print(json.dumps({'status':'verified','receipt':str((out/'receipt.json').relative_to(ROOT)),'receipt_sha256':sha(out/'receipt.json'),'source_tree_sha256':r['source_tree_sha256'],'native_archive_sha256':r['native_archive']['sha256'],'full_fixture_tests':24,'controlled_expected_busy_failures':3,'controlled_repaired_tests':12,'native_UI_device_checks':'pending under user pause'},indent=2))

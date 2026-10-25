#!/usr/bin/env python3
"""Verify prepared attribution artifacts. No build, target, devices or Git."""
from pathlib import Path
import hashlib, json
from transform import transform
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def manifest(directory):
    paths=[directory/'Cargo.toml',directory/'Cargo.lock']
    paths += [p for top in ('include','src','tests') for p in (directory/top).rglob('*') if p.is_file()]
    return {str(p.relative_to(directory)):sha(p) for p in sorted(paths)}
seal=read(HERE/'seal.json')
for name,digest in seal['files'].items():assert sha(HERE/name)==digest,name
for name,digest in seal['externalFiles'].items():assert sha(ROOT/name)==digest,name
baseline=read(HERE/'baseline-manifest.json')
assert len(baseline)==132 and sha(HERE/'baseline-manifest.json')=='b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11'
assert baseline==read(HERE/'live-source-after.json')==manifest(ROOT/'vm')
copied=read(HERE/'copied-source-manifest.json')
assert copied==manifest(HERE/'source')
assert [n for n in baseline if baseline[n]!=copied[n]]==['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/lifecycle_tests.rs']
for name in baseline:assert (HERE/'source'/name).read_bytes()==transform(name,(ROOT/'vm'/name).read_bytes()),name
binding=read(HERE/'binding.json')
for info in binding['inputs']:assert sha(info['path'])==info['sha256'],info['path']
for name,digest in binding['authoredInputs'].items():assert sha(HERE/name)==digest,name
diagnosis=ROOT/'verification/swift-cache-remaining-work-diagnosis'
diagnosis_seal=read(diagnosis/'seal.json')
assert len(diagnosis_seal['files'])==20
for name,digest in diagnosis_seal['files'].items():assert sha(diagnosis/name)==digest,name
for name,digest in diagnosis_seal['externalFiles'].items():assert sha(ROOT/name)==digest,name
for name,digest in read(diagnosis/'input-bindings.json').items():assert sha(ROOT/name)==digest,name
prepared=read(HERE/'prepared-selection.json')
assert prepared['rootMustCreateSelectionBeforeTarget'] and not prepared['targetAttempted'] and not prepared['gaAccepted']
assert prepared['maxTargetAttempts']==1
for name,digest in prepared['boundEvidence'].items():assert sha(HERE/name)==digest,name
binary=prepared['binary'];assert sha(binary['path'])==binary['sha256'] and Path(binary['path']).stat().st_size==binary['bytes']
target=prepared['target'];assert target['bytes']==53_777_114 and sha(target['path'])==target['sha256']=='24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994'
command=read(HERE/'proposed-command.json')
assert command['argv']==prepared['argv'] and command['outerCommand']==prepared['outerCommand']
assert (command['outerDeadlineSeconds'],command['terminationGraceSeconds'],command['killWaitSeconds'])==(170,5,5)
assert (command['validationDeadlineMs'],command['cumulativeRuntimeDeadlineMs'],command['cumulativeWasiDeadlineMs'])==(120000,30000,30000)
assert not (HERE/'target-attempt-started.json').exists() and not (HERE/'root-selection.json').exists()
suite=read(HERE/'control-suite.json');assert suite['passed'] and len(suite['commands'])==3
observed=[]
for name in suite['commands']:
    receipt=read(HERE/'commands'/name/'receipt.json')
    assert receipt['passed'] and receipt['processGroupEmpty'] and receipt['rawStreamEOFConfirmed'] and receipt['exitCode']==0 and not receipt['timedOut']
    assert sha(HERE/'commands'/name/'stdout')==receipt['stdout']['sha256']
    assert sha(HERE/'commands'/name/'stderr')==receipt['stderr']['sha256']
    parsed=[]
    for line in (HERE/'commands'/name/'stdout').read_text().splitlines():
        for prefix in ('MIXER_ATTRIBUTION ','MIXER_EXACT '):
            if prefix in line:parsed.append(json.loads(line.split(prefix,1)[1]))
    assert parsed==read(HERE/(name+'-events.json'))
    observed.extend(parsed)
snapshots=[e['observer'] for e in observed if 'observer' in e]
snapshots += [e['payload'] for e in observed if e.get('event','').startswith('attribution_')]
assert snapshots
for s in snapshots:
    assert s['reconciled'] and s['invalid_flags']==0
    assert len(s['successful_credits'])==len(s['work_calls'])==12
    assert sum(s['successful_credits'])==s['successful_sum']==s['authoritative_cache_work']
    assert len(s['free_pin_probe_length_histogram'])==len(s['resident_hit_probe_length_histogram'])==65
    assert s['seen_bitmap_bytes']==10000 and s['seen_population']==s['distinct_completed_decodes']
    assert len(s['first_repeated_function_identities'])<=16
    assert 'seen' not in s and 'bitmap' not in s
    if s['authoritative_cache_totals'] is not None:
        c=s['authoritative_cache_totals']
        assert s['hits']==c['hits'] and s['misses']==c['misses']
        assert s['distinct_completed_decodes']+s['repeated_completed_decodes']==c['decodes']
        assert c['evictions']<=c['decodes']<=c['misses']
        assert c['decodes']-c['evictions']<=64
    assert len(json.dumps(s))<=16384
cycle=next(e['observer'] for e in observed if e.get('case')=='65_cycle_twice')
assert (cycle['distinct_completed_decodes'],cycle['repeated_completed_decodes'],cycle['authoritative_cache_totals']['evictions'])==(65,65,66)
assert cycle['first_repeated_function_identities']==list(range(34,50)) and cycle['untracked_repeated_completion_occurrences']==49
assert len([e for e in observed if e.get('case')=='finite_cache_work_failure'])==10
assert len([e for e in observed if e.get('case')=='finite_cancellation_failure'])==6
assert any(e.get('observer_invalidity_did_not_change_vm_results') for e in observed)
assert any(e.get('event')=='observer_all_snapshots_reconciled' and e['payload'] for e in observed)
assert any(e.get('event')=='cleanup_empty' and e['payload'] for e in observed)
cleanup=read(HERE/'cleanup.json')
assert cleanup['removed'] and cleanup['live132SourceHashesUnchanged'] and not (HERE/'owned-scratch').exists()
assert all(g['state']=='absent' for g in cleanup['processGroups'])
receipt=read(HERE/'receipt.json')
assert receipt['status']=='prepared-awaiting-fresh-exact-root-selection' and not receipt['targetExecuted'] and not receipt['gaAccepted']
assert receipt['liveVMChanged'] is False and receipt['focusedReleaseControlsPassed'] and receipt['ownedBuildScratchRemoved']
print(f"Verified {len(seal['files'])} attribution files, 20 diagnosis files, 132 live/copy source files, finite Release controls, fresh binary and unchanged budgets. Full target not executed.")

#!/usr/bin/env python3
"""Seal rejected frozen3 bounded evidence; no product test or acceptance."""
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DOC=ROOT/'docs/android-private-owner-candidate3-review.md'
MANIFEST=HERE/'manifest.json'
SIDECAR=HERE/'manifest.sha256'
RESULT=HERE/'seal-result.json'
EXCLUDED={MANIFEST,SIDECAR,RESULT}


def record(path):
    data=path.read_bytes()
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def read(path):return json.loads(path.read_text())


def verify():
    checks=0
    def check(condition,label):
        nonlocal checks
        checks+=1
        if not condition:raise AssertionError(label)
    for name,pin in {'candidate-3-admission.json':'81f9a86838a060063db5ffa5abd9ee63581e5032a9899a68e88165f03c5e7378',
        'candidate-3-manifest.json':'c5bed3d89498abe0f9d9ee2547e74f4b26d2f29a05c9744e09b61d47259ecb6b',
        'candidate-3-gate-finding-and-hold.json':'e215582b755848778b125c77dc73eb64e0195db33d8768e5e936c02daecb79cb'}.items():
        check(record(HERE/'admission'/name)['sha256']==pin,'exact root frozen3 pin '+name)
    candidate=read(HERE/'admission/candidate-3-manifest.json')
    check(candidate['members']==1215 and candidate['bytes']==11798221,'exact admitted closure summary')
    expected=set()
    for entry in read(HERE/'custody.json')['snapshot_inputs']:
        name='source/'+entry['path'];value=dict(bytes=entry['bytes'],sha256=entry['sha256'])
        check(record(HERE/'candidate-3'/name)==candidate['files'][name]==value,'root-admitted frozen subject '+name);expected.add(name)
    legacy=read(HERE/'historical-vector-inputs.json')
    check(not legacy['producer_harness_execution'] and not legacy['expected_outcome_oracle'],'legacy read authorization scope')
    for entry in legacy['inputs']:
        name=entry['path'];value=dict(bytes=entry['bytes'],sha256=entry['sha256'])
        check(record(HERE/'candidate-3'/name)==candidate['files'][name]==value,'exact historical-vector source '+name);expected.add(name)
    actual={str(p.relative_to(HERE/'candidate-3')) for p in (HERE/'candidate-3').rglob('*') if p.is_file()}
    check(actual==expected and len(actual)==97,'bounded97-source read subset; no producer runner input')
    for phase,pin in [('preaccess','3d9100d342756d902152a6e786ec0e2a8ae1cd63d3ca79dde68f56ce3c7a390b'),
        ('leaf-review-1','a553307572c2a7384a2a9129016a629fc8dd572f451da87c6c2714ce6be34ec7'),
        ('implementation-review-1','e59aed63978371a1bb946b77b3e07ef0fce0fd9bd39a14d1c5c3f45aa2dd4742')]:
        old=HERE.parent/phase/'manifest.json';check(record(old)['sha256']==pin,'prior immutable seal '+phase)
        for name,value in read(old)['files'].items():check(record(ROOT/name)==value,'prior exact member untouched '+name)
    roster=read(HERE.parent/'preaccess/site-input-map.json')['concrete_subjects']
    leaves=read(HERE.parent/'leaf-review-1/admission/leaf-manifest-3.json')['files']
    compile_set={'candidate-3/source/'+name for name in roster+sorted(leaves)}|{'IndependentOwnerFocusReview.java'}
    check(len(roster)==14 and len(leaves)==74 and len(compile_set)==89,'exact14+73+probe+independent-driver closure')
    core=HERE/'candidate-3/source/native/android/app/src/dev/mixer/android/OwnerLifecycleV2.java'
    check(record(core)['sha256']=='4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6','exact unchanged core')
    history=read(HERE/'historical-authored-source-map.json')['runs'];check(len(history)==8,'all8 authored invocation snapshots')
    for row in history:
        directory=HERE/row['run'];compiled=read(directory/'01-compile.command.json')
        check(compiled['exit_code']==0 and set(compiled['source_map'])==compile_set,'exact strict full actual-subject compilation '+row['run'])
        check(compiled['independent_runner_sha256']==row['authored_runner']['sha256'],'exact independent runner hash')
        for key in ['authored_driver','authored_runner']:
            value=row[key];check(record(HERE/value['path'])==dict(bytes=value['bytes'],sha256=value['sha256']),'authored bytes retained '+key)
        for name,value in compiled['source_map'].items():
            path=HERE/(row['authored_driver']['path'] if name=='IndependentOwnerFocusReview.java' else name)
            check(record(path)==value,'exact compiled historical/frozen source '+name)
        for value in row['runtime_inputs'].values():check(record(HERE/value['path'])==dict(bytes=value['bytes'],sha256=value['sha256']),'exact historical input bytes')
        cleanup=read(directory/'cleanup.json')
        check(cleanup['owned_children_reaped'] and cleanup['exclusive_scratch_removed'] and not cleanup['native_or_capture_started'],'observed owned scratch/child cleanup')
    mini=HERE/'targeted-6/witness-seal.json'
    check(record(mini)['sha256']=='f0bf0150fed64e0e3b47da17e7432ffa1d32d1ae34f2c678b478fc6429e9f1e2','root-verified targeted6 seal immutable')
    for name,value in read(mini)['files'].items():check(record(HERE/name)==value,'immutable targeted6 witness member '+name)
    receipt=read(HERE/'receipt.json');check(len(receipt['executions'])==16,'honest16 runtime invocations')
    for row in receipt['executions']:
        command=read(HERE/row['command']);check(command['exit_code']==row['exit_code'],'raw retained exit '+row['command'])
        expected=1 if row['run'] in ['targeted-3','targeted-4','targeted-6'] else 0
        check(row['exit_code']==expected,'honest setup/product failure distinction')
    for path in HERE.glob('targeted-*/*.command.json'):
        command=read(path);check(command['forced_termination'] is None,'observed child returned')
        check(command['limits']==dict(wall_seconds=120,stdout_bytes=2097152,stderr_bytes=2097152,owned_children=1),'one owned bounded child')
        tool=Path(command['argv'][0]).name
        check(command['executable_sha256']==read(HERE/'tools'/f'{tool}.command.json')['executable_sha256'],'exact official host tool')
        if tool=='javac':
            argv=command['argv'];check(argv[argv.index('--release')+1]=='17' and all(x in argv for x in ['-g','-Xlint:all','-Werror','-proc:none','-classpath','-sourcepath']),'strict Java17 target compilation')
    check('openjdk version "27"' in (HERE/'tools/java.stderr').read_text(),'actual runtime27, not JDK17 claim')
    fail=read(HERE/'targeted-6/03-active-lifecycle-dirty.stdout')
    check(fail['inputCancellationReturnedWhileCoordinatorBusy'] and fail['actualCurrentGateOpenAtPost'] and not fail['sharedAuthorityOpenAtPost'] and fail['actualCoreDirty'] and fail['actualCorePhase']=='LIVE' and fail['actualQueuedDrains']==1 and fail['JNIcommitCalls']==1,'actual lifecycle-dirty defect and F01 positive')
    helpers=read(HERE/'targeted-5/03-helper-negative.stdout')
    check(helpers['actualHelpers']==13 and helpers['staleAndCleanupRefusals']==26 and helpers['nativeLeavesReached']==0 and helpers['noOperationMinted'],'13 actual before-leaf helper scope controls')
    observer=read(HERE/'targeted-7/03-observer-dirty.stdout')
    check(observer['generationAfter']==observer['generationBefore']+1 and observer['actualCorePhase']=='RETIRED' and observer['JNIcommitCalls']==0 and observer['JNIabortCalls']==observer['JNIdestroyCalls']==1,'actual observer-dirty distinction')
    refresh=read(HERE/'targeted-7/03-retained-refresh.stdout')
    check(refresh['sameRetainedPacketIdentity'] and refresh['sameRevision'] and refresh['newActualPresentation'] and not refresh['actualCoreDirty'] and refresh['JNIprepareCalls']==refresh['JNIcommitCalls']==refresh['JNIcreateCalls']==1,'actual exact-packet zero-added-JNI refresh')
    fatal=read(HERE/'targeted-7/03-fatal-current-report.stdout')
    check(fatal['sameFatalEscaped'] and fatal['sameTailFatal'] and fatal['rendererCause']=='CURRENT_CHECK_FATAL' and fatal['queuedTerminalTails']==1 and fatal['destroyBeforeTail']==0 and fatal['destroyAfterTail']==1 and not fatal['actualClosePendingAfterTail'],'actual typed terminal report/one deferred disposal')
    bindings=read(HERE/'runtime-frame-bindings.json');check(bindings['bound_runtime_frames']==38,'all38 targeted frame identities bound')
    for row in bindings['bindings']:
        check(record(HERE/row['source_path'])==row['source'] and record(HERE/row['javap_output'])['sha256']==row['javap_sha256'],'exact retained source/class instruction binding')
    check(not any(receipt['restrictions'].values()),'scope restrictions observed')
    check(not any(receipt[x] for x in ['full_site_matrix_complete','full_new_site_inventory_independently_bound','legacy_vector_migration_complete','implementation_accepted','CLI_consumer_qualified','native_qualified','public_V2_enabled','GA_qualified']),'no partial evidence promoted to acceptance')
    check(receipt['full_matrix_rows_qualified']==0 and receipt['V1_positive_rows_executed']==0,'remaining matrix and V1 explicit')
    check(not (HERE/'scratch').exists() and DOC.is_file(),'owned cleanup/doc complete')
    return checks


def members():return sorted([p for p in HERE.rglob('*') if p.is_file() and p not in EXCLUDED]+[DOC])


def main():
    assertions=verify();mode=sys.argv[1:]
    if mode==['--seal']:
        if any(p.exists() for p in EXCLUDED):raise SystemExit('refuse to overwrite rejected candidate3 seal')
        files={str(p.relative_to(ROOT)):record(p) for p in members()}
        MANIFEST.write_text(json.dumps(dict(schema=1,scope='independent frozen3 rejection and bounded controls; full qualification pending',members=len(files),
            bytes=sum(v['bytes'] for v in files.values()),files=files,excluded_metadata=['manifest.json','manifest.sha256','seal-result.json'],
            command=['python3','-B','verification/android-private-owner-independent-review/implementation-review-2/verify_and_seal.py','--seal'],python=sys.version),indent=2,sort_keys=True)+'\n')
        SIDECAR.write_text(record(MANIFEST)['sha256']+'  manifest.json\n')
    elif mode not in [['--check'],['--content']]:raise SystemExit('expected --seal/--check/--content')
    if mode==['--content']:
        print(json.dumps(dict(status='rejected-candidate3-custody-only',custody_assertions=assertions)));return
    actual={str(p.relative_to(ROOT)):record(p) for p in members()}
    if actual!=read(MANIFEST)['files'] or SIDECAR.read_text()!=record(MANIFEST)['sha256']+'  manifest.json\n':raise SystemExit('exact closure changed')
    result=dict(status='sealed-frozen3-rejection-evidence-verified',manifest_sha256=record(MANIFEST)['sha256'],members=len(actual),
        bytes=sum(v['bytes'] for v in actual.values()),custody_assertions=assertions,recommendation='reject3; separate corrected4 review',implementation_accepted=False,full_matrix_complete=False)
    if mode==['--seal']:RESULT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    elif read(RESULT)!=result:raise SystemExit('deterministic result differs')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()

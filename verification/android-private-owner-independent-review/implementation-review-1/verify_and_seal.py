#!/usr/bin/env python3
"""Seal candidate2 findings and custody, not implementation acceptance."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DOC = ROOT / 'docs/android-private-owner-implementation-review.md'
MANIFEST = HERE / 'manifest.json'
SIDECAR = HERE / 'manifest.sha256'
RESULT = HERE / 'seal-result.json'
EXCLUDED = {MANIFEST, SIDECAR, RESULT}


def record(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def read(path):
    return json.loads(path.read_text())


def verify():
    assertions = 0
    def check(condition, description):
        nonlocal assertions
        assertions += 1
        if not condition:
            raise AssertionError(description)
    pins = {'candidate-2-admission.json':'77f257671008d2d6dc51530b8b3d3f954c4ce3f75eeb9edc6257a3b10805df42',
        'candidate-2-hold.json':'f719fe06f8e162ab99de087157bf69a461b6a195bbdcdd79a497166d71bd9c77',
        'candidate-2-manifest.json':'dc75c6544fdc10d25457c00782dcfb8afbcde756988ce0fd742606bb69c8c0e7'}
    for name, expected in pins.items():
        check(record(HERE/'admission'/name)['sha256']==expected, 'exact frozen root admission/override '+name)
    candidate = read(HERE/'admission/candidate-2-manifest.json')
    check(candidate['members']==1170 and candidate['bytes']==11537811, 'exact admitted candidate closure summary')
    custody = read(HERE/'custody.json')['snapshot_inputs']
    check(len(custody)==94, 'explicit bounded source-review subset')
    expected_sources = set()
    for member in custody:
        name = member['path']
        expected = dict(bytes=member['bytes'],sha256=member['sha256'])
        check(record(HERE/'candidate-2/source'/name)==expected, 'exact owned frozen source '+name)
        check(candidate['files']['source/'+name]==expected, 'source belongs to admitted immutable candidate '+name)
        expected_sources.add(name)
    actual_sources = {str(p.relative_to(HERE/'candidate-2/source')) for p in (HERE/'candidate-2/source').rglob('*') if p.is_file()}
    check(actual_sources==expected_sources, 'no additional product/producer inputs in owned subset')
    for phase, pin in [('preaccess','3d9100d342756d902152a6e786ec0e2a8ae1cd63d3ca79dde68f56ce3c7a390b'),
        ('leaf-review-1','a553307572c2a7384a2a9129016a629fc8dd572f451da87c6c2714ce6be34ec7')]:
        old = HERE.parent/phase/'manifest.json'
        check(record(old)['sha256']==pin, 'old owned manifest immutable '+phase)
        for name, expected in read(old)['files'].items():
            check(name.startswith('verification/android-private-owner-independent-review/') or
                name in ('docs/android-private-owner-implementation-review-plan.md','docs/android-private-owner-leaf-review.md'), 'owned prior sealed scope')
            check(record(ROOT/name)==expected, 'prior sealed bytes untouched '+name)
    roster = read(HERE.parent/'preaccess/site-input-map.json')['concrete_subjects']
    check(len(roster)==14, 'actual14 selected subject roster')
    leaves = read(HERE.parent/'leaf-review-1/admission/leaf-manifest-3.json')
    check(len(leaves['files'])==74 and len(leaves['substituteFQCNs'])==73, 'exact admitted mechanical leaves/probe closure')
    compile_set = {'candidate-2/source/'+name for name in roster+sorted(leaves['files'])}|{'IndependentOwnerFocusReview.java'}
    history = read(HERE/'historical-authored-source-map.json')['runs']
    check(len(history)==8, 'all eight invocations retain authored source/runner')
    for row in history:
        directory = HERE/row['run']
        compiled = read(directory/'01-compile.command.json')
        check(compiled['exit_code']==0, 'actual full closure compilation returned success')
        check(set(compiled['source_map'])==compile_set and len(compiled['source_map'])==89, 'exact 14+73+probe+independent source list')
        for name, expected in compiled['source_map'].items():
            path = HERE/row['compiled_driver']['path'] if name=='IndependentOwnerFocusReview.java' else HERE/name
            check(record(path)==expected, 'exact authored/frozen compilation bytes '+row['run']+' '+name)
        for key in ['compiled_driver','authored_runner']:
            value=row[key]
            check(record(HERE/value['path'])==dict(bytes=value['bytes'],sha256=value['sha256']), 'exact archived '+key)
        cleanup=read(directory/'cleanup.json')
        check(cleanup['owned_children_reaped'] and cleanup['exclusive_scratch_removed'] and not cleanup['native_or_capture_started'], 'bounded owned cleanup '+row['run'])
    tool_hashes={tool:read(HERE/'tools'/f'{tool}.command.json')['executable_sha256'] for tool in ['java','javac','javap']}
    for command in sorted(HERE.glob('targeted-*/*.command.json')):
        value=read(command)
        check(value['forced_termination'] is None, 'all observed child commands returned normally')
        check(value['limits']==dict(wall_seconds=120,stdout_bytes=2097152,stderr_bytes=2097152,owned_children=1), 'owned child bounds')
        tool=Path(value['argv'][0]).name
        check(value['executable_sha256']==tool_hashes[tool], 'same exact official host binary '+tool)
        check(set(value['removed_environment'])=={'JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH'}, 'injected Java options removed')
        if tool=='javac':
            argv=value['argv']
            check(argv[argv.index('--release')+1]=='17' and all(x in argv for x in ['-g','-Xlint:all','-Werror','-proc:none','-classpath','-sourcepath']), 'strict Java17 explicit-source compilation')
    check('javac 27' in (HERE/'tools/javac.stdout').read_text(), 'observed compiler27')
    check('openjdk version "27"' in (HERE/'tools/java.stderr').read_text(), 'observed host runtime27, not17')
    expected_exits={'targeted-1':{'fresh-input':1,'lifecycle':0},'targeted-2':{'fresh-input':1,'lifecycle':0},
        'targeted-3':{'fresh-input':1,'lifecycle':0,'terminal':1},'targeted-4':{'accepted-input':0},
        'targeted-5':{'post-failure':1},'targeted-6':{'registration-failure':0},'targeted-7':{},'targeted-8':{}}
    for run, expected in expected_exits.items():
        actual={p.name[3:].removesuffix('.command.json'):read(p)['exit_code'] for p in (HERE/run).glob('03-*.command.json')}
        check(actual==expected, 'honest retained runtime outcomes '+run)
    focus=read(HERE/'targeted-2/03-fresh-input.stdout')
    check(all(focus[x] for x in ['focusFlippedAtNativeReturn','queuedCallbackObserved','drawAllowedAtPost','inputAllowedAtPost','actualCurrentGateOpenAtPost','actualCoreDirtyAtPost']) and not focus['actualCoreFocusedAtPost'], 'exact confirmed focus observation')
    terminal=read(HERE/'targeted-3/03-terminal.stdout')
    check(terminal['actualCancellationReentry'] and terminal['actualCorePhase']=='RETIRED' and terminal['ordinaryProbesAfterTerminal']!='[]' and not terminal['drawAllowed'] and not terminal['inputAllowed'], 'exact terminal boundary observation without reopening')
    post=read(HERE/'targeted-5/03-post-failure.stdout')
    check(post['actualQueuedWorkAfterRetirement']==1 and post['actualRemoveCalls']==0 and post['handlerLedger']=='RETURNED' and post['samePrimaryFailure'] and post['JNIcreateCalls']==0, 'exact post cleanup failure observation')
    successor=read(HERE/'targeted-4/03-accepted-input.stdout')
    check(successor['delegateResult'] and successor['actualPresentationChanged'] and successor['actualCorePhase']=='LIVE' and successor['operationCleared'] and successor['JNIprepareCalls']==successor['JNIcommitCalls']==2 and successor['actualPacketRevision']=='2', 'actual accepted completed-successor baseline')
    observer=read(HERE/'targeted-6/03-registration-failure.stdout')
    check(observer['allEightActualRemovalAttempts']=='[1, 1, 1, 1, 1, 1, 1, 1]' and observer['actualObserverSlots']=='[3, 4, 3, 3, 3, 3, 3, 3]' and all(observer[x] for x in ['sameOwnerPrimary','sameOwnerFirstFatal','sameEscapedFatal','sameObserverPrimary','sameObserverFirstFatal']) and observer['JNIcreateCalls']==0, 'actual eight-slot cleanup and fatal identities')
    bindings=read(HERE/'runtime-frame-bindings.json')
    check(bindings['bound_runtime_frames']==33 and len(bindings['bindings'])==33, 'targeted exact descriptor/BCI bindings')
    for row in bindings['bindings']:
        check(record(HERE/row['source_path'])==row['source'] and record(HERE/row['javap_output'])['sha256']==row['javap_sha256'], 'bound actual source and bytecode bytes')
    findings=read(HERE/'findings.json')
    check(len(findings['findings'])==7 and not findings['repairs_reviewed'] and not findings['implementation_accepted'], 'unresolved scoped findings; repaired bytes unreviewed')
    receipt=read(HERE/'receipt.json')
    check(receipt['selected_family_count']==30 and receipt['selected_baseline_seven_case_rows']==1288 and receipt['selected_baseline_V2_sites']==184, 'unchanged selected proof obligations')
    check(not any(receipt[x] for x in ['complete_matrix_executed','new_site_inventory_completed','five_V1_positive_baselines_executed','implementation_accepted','CLI_consumer_qualified','native_qualified','public_V2_enabled','GA_qualified']), 'no expanded acceptance/count claims')
    check(not any(receipt['restrictions'].values()), 'restricted surfaces untouched and repairs unreviewed')
    check(not (HERE/'scratch').exists(), 'exclusive transient scratch absent')
    check(DOC.is_file(), 'owned source-review document retained')
    return assertions


def members():
    paths=sorted([p for p in HERE.rglob('*') if p.is_file() and p not in EXCLUDED]+[DOC])
    if any('__pycache__' in p.parts or p.is_symlink() for p in paths):
        raise AssertionError('unexpected generated cache or symlink')
    return paths


def main():
    assertions=verify()
    mode=sys.argv[1:]
    if mode==['--seal']:
        if any(p.exists() for p in EXCLUDED):
            raise SystemExit('refuse to overwrite sealed candidate2 review')
        files={str(p.relative_to(ROOT)):record(p) for p in members()}
        MANIFEST.write_text(json.dumps(dict(schema=1,scope='independent frozen candidate2 findings; incomplete implementation qualification',
            members=len(files),bytes=sum(x['bytes'] for x in files.values()),files=files,
            excluded_metadata=['manifest.json','manifest.sha256','seal-result.json'],
            command=['python3','-B','verification/android-private-owner-independent-review/implementation-review-1/verify_and_seal.py','--seal'],
            python=sys.version),indent=2,sort_keys=True)+'\n')
        SIDECAR.write_text(record(MANIFEST)['sha256']+'  manifest.json\n')
    elif mode not in (['--check'],['--content']):
        raise SystemExit('expected --seal, --check or --content')
    if mode==['--content']:
        print(json.dumps(dict(status='candidate2-evidence-custody-only',custody_assertions=assertions,implementation_accepted=False)))
        return
    manifest=read(MANIFEST)
    actual={str(p.relative_to(ROOT)):record(p) for p in members()}
    if actual!=manifest['files'] or SIDECAR.read_text()!=record(MANIFEST)['sha256']+'  manifest.json\n':
        raise SystemExit('sealed candidate2 exact closure or bytes changed')
    result=dict(status='sealed-candidate2-findings-and-exact-evidence-verified',manifest_sha256=record(MANIFEST)['sha256'],
        members=len(actual),bytes=sum(x['bytes'] for x in actual.values()),custody_assertions=assertions,
        recommendation='reject-candidate2; await separately root-admitted repaired frozen candidate',
        implementation_accepted=False,complete_matrix=False,native_qualified=False)
    if mode==['--seal']:
        RESULT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    elif read(RESULT)!=result:
        raise SystemExit('deterministic seal-result mismatch')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    main()

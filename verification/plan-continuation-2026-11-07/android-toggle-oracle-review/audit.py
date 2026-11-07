"""Independent file/JSON/hash audit only. Never executes candidate code or probes processes."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import platform
import re
import sys
import zipfile

OUT = Path(__file__).resolve().parent
PARENT = OUT.parents[2]
CANDIDATE = Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-5c87cbc0')
MOTION = Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-5a390519')
REL = Path('verification/plan-continuation-2026-11-07')
E = CANDIDATE / REL / 'android-toggle-oracle'
M = MOTION / REL / 'android-effective-motion'
BASE = PARENT / REL / 'android-runtime'
PIN = '81d4e5fcbddd4c1f74519699c8dde3ec1c3e997c36c58c5af7dc82c6dfab5a57'
PATHS = [
    'native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java',
    'native/android/tests/NativeOwnerV2ConcreteHostLeaves/android/widget/Switch.java',
    'native/android/tests/NativeAndroidFixtureHostTests.java',
]
HELD = {20745,20770,20780,20817,20842,20851,20866,2424,2621}
checks = []
identities = {}

def ident(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    result = {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}
    identities[str(path)] = result
    return result

def sha(path):
    return ident(path)['sha256']

def read(path):
    ident(path)
    return json.loads(Path(path).read_text())

def check(name, condition, detail=None):
    checks.append({'name': name, 'passed': bool(condition), 'detail': detail})

def matches(path, expected):
    actual = ident(path)
    return actual['sha256'] == (expected if isinstance(expected, str) else expected['sha256']) and (
        isinstance(expected, str) or 'bytes' not in expected or actual['bytes'] == expected['bytes'])

def verify_map(name, root, mapping):
    bad = [relative for relative, expected in mapping.items() if not matches(root / relative, expected)]
    check(name, not bad, {'count': len(mapping), 'mismatches': bad})

def main():
    motion_review = read(PARENT / REL / 'android-effective-motion-review/result.json')
    check('motion acceptance prerequisite', motion_review['decision'] == 'ACCEPT_FOR_PARENT_INTEGRATION')
    manifest = read(M / 'implementation-paths.json')
    verify_map('motion original implementation paths stable', MOTION, manifest['paths'])
    verify_map('accepted motion present in parent', PARENT, manifest['paths'])
    verify_map('accepted motion present in oracle candidate', CANDIDATE,
               {p: v for p, v in manifest['paths'].items() if p != PATHS[0]})
    result = read(E / 'result.json')
    check('pinned oracle patch', sha(E / 'oracle.patch') == PIN == result['oraclePatchSHA256'])
    actual_patch = ''.join(''.join(difflib.unified_diff(
        (MOTION / p).read_text().splitlines(keepends=True),
        (CANDIDATE / p).read_text().splitlines(keepends=True),
        fromfile='a/' + p, tofile='b/' + p)) for p in PATHS)
    check('patch exact three-file reconstruction', actual_patch.encode() == (E / 'oracle.patch').read_bytes())
    for p in PATHS:
        check('parent preimage ' + p, sha(PARENT / p) == sha(MOTION / p) == result['oraclePatchFiles'][p]['candidateSHA256'])
        check('candidate postimage ' + p, sha(CANDIDATE / p) == result['oraclePatchFiles'][p]['correctedSHA256'])
    old = (MOTION / PATHS[0]).read_text()
    new = (CANDIDATE / PATHS[0]).read_text()
    replacement = ('check(toggle.performClick(), "actual native click accepted");',
                   'result.putBoolean("togglePerformClickReturn", toggle.performClick());')
    check('all other instrumentation bytes unchanged', old.count(replacement[0]) == 1 and new == old.replace(*replacement))
    check('three unchanged readiness bounds', new.count('awaitPresentation("') == 3 and
          'attempt<100' in new and 'Thread.sleep(20)' in new)
    messages = re.findall(r'check\(.*?,\s*"([^"]+)"\);', new, re.S)
    check('eleven executable assertion messages', len(messages) == 11, messages)
    check('no dummy listener in instrumentation', 'setOnClickListener' not in new and new.count('toggle.performClick()') == 1)
    fixture = (CANDIDATE / PATHS[2]).read_text()
    added = fixture.split('private static void switchClickContract() {', 1)[1].split('\n    static int run()', 1)[0]
    check('seven fixture assertions registered', added.count('check(') == 7 and 'NativeAndroidFixtureHostTests::switchClickContract' in fixture)
    old_leaf = (MOTION / PATHS[1]).read_text()
    new_leaf = (CANDIDATE / PATHS[1]).read_text()
    check('fixture forwards superclass result only', new_leaf == old_leaf.replace(
        'super.performClick();done("Switch.performClick");return true;',
        'boolean result=super.performClick();done("Switch.performClick");return result;'))

    evidence_manifest = read(E / 'evidence-manifest.json')
    verify_map('sealed evidence manifest', E, evidence_manifest['files'])
    source_lock = read(E / 'source-lock.json')
    verify_map('runtime source lock', CANDIDATE, source_lock['files'])
    closure = hashlib.sha256(json.dumps(source_lock['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    runtime = read(E / 'receipt.json')
    check('runtime closure digest', closure == source_lock['sourceClosureSHA256'] == runtime['sourceClosureSHA256'])
    for p in [PATHS[0], 'native/android/tests/NativeCoordinatorV2IntegrationActivity.java',
              'verification/android-native-v2-coordinator/AndroidManifest.future-test.xml',
              'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json']:
        check('canonical snapshot ' + p, matches(E / 'canonical-inputs' / p, source_lock['files'][p]))
    admission = read(E / 'candidate-admission.json')
    candidate_lock = read(M / 'source-lock.json')
    candidate_receipt = read(M / 'receipt.json')
    check('candidate admission hashes', sha(M / 'source-lock.json') == admission['candidateSourceLockSHA256'] and
          sha(M / 'receipt.json') == admission['candidateReceiptSHA256'])
    check('103 unchanged motion runtime inputs', len(source_lock['files']) == 105 and
          len(candidate_lock['files']) == 105 and all(source_lock['files'][p] == v for p, v in candidate_lock['files'].items()
          if p not in admission['testInputs']))
    check('original failed smoke retained', candidate_receipt['runtime']['passed'] is False and
          'actual native click accepted' in candidate_receipt['runtime']['instrumentationOutput'])
    baseline_manifest = read(E / 'baseline-manifest.json')
    verify_map('106 parent baseline files preserved', BASE, baseline_manifest['files'])
    check('baseline file set preserved', set(baseline_manifest['files']) == {str(p.relative_to(BASE)) for p in BASE.rglob('*') if p.is_file()})
    reuse = read(E / 'native-reuse.json')
    prior = read(BASE / 'build-receipt.json')
    prior_lock = read(BASE / 'source-lock.json')
    check('native reuse receipts bound', reuse == runtime['nativeReuse'] and sha(BASE / 'build-receipt.json') == reuse['buildReceiptSHA256'] and
          sha(BASE / 'source-lock.json') == reuse['sourceLockSHA256'] and sha(E / 'candidate-admission.json') == reuse['candidateAdmissionSHA256'])
    check('101 original native build inputs unchanged', len(prior_lock['files']) - len(reuse['explicitJavaChanges']) == 101 and all(
        source_lock['files'][p] == v for p, v in prior_lock['files'].items() if p not in reuse['explicitJavaChanges']))
    check('explicit Java changes correctly identified', all(v == {'prior': prior_lock['files'][p], 'current': source_lock['files'][p]}
          for p, v in reuse['explicitJavaChanges'].items()))
    native = reuse['nativeLibraries']
    check('18-library identity chain', len(native) == 18 and native == candidate_receipt['nativeReuse']['nativeLibraries'] and
          native == {p: v for p, v in prior['artifacts'].items() if p.startswith('lib/')} and
          native == {p: v for p, v in runtime['artifacts'].items() if p.startswith('lib/')} and reuse['rebuildCount'] == 0)
    apk = Path(reuse['retainedAPK'])
    check('retained APK identity', sha(apk) == reuse['retainedAPKSHA256'] == prior['apkSHA256'])
    with zipfile.ZipFile(apk) as z:
        check('retained APK exact native set', set(p for p in z.namelist() if p.startswith('lib/')) == set(native))
        library_bad = []
        for p, expected in native.items():
            data = z.read(p)
            if {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} != expected:
                library_bad.append(p)
        check('18 retained library bytes', not library_bad, library_bad)

    tool_maps = [runtime['tools'], admission['candidateTools'], reuse['matchingTools'], read(E / 'fullB/receipt.json')['tools']]
    checked_tools = {}
    for mapping in tool_maps:
        for p, expected in mapping.items():
            if p not in checked_tools:
                checked_tools[p] = ident(p)
            check('tool identity ' + p, checked_tools[p]['sha256'] == expected['sha256'] and
                  checked_tools[p]['bytes'] == expected['bytes'] and ('realPath' not in expected or str(Path(p).resolve()) == expected['realPath']))
    check('17 candidate runtime tool descriptors identical', len(runtime['tools']) == 17 and runtime['tools'] == admission['candidateTools'])

    full = read(E / 'fullB/receipt.json')
    source_map = read(E / 'fullB/source-map.json')
    verify_map('108 full B source identities', CANDIDATE, source_map)
    prior_map = read(M / 'fullB/source-map.json')
    changed = [p for p in set(source_map) | set(prior_map) if source_map.get(p) != prior_map.get(p)]
    check('full B changes only two fixture paths', set(changed) == set(PATHS[1:]), changed)
    matrix = read(E / 'fullB/barrier-cases.json')
    check('1323-case entire matrix identical', matrix == read(M / 'fullB/barrier-cases.json') and len(matrix['cases']) == 1323 and not matrix['missing'])
    check('host check delta exactly seven', (E / 'fullB/host.stdout').read_text().strip() ==
          'PASS concrete actual16 host checks=14662; platform/JNI leaves, native runtime pending' and
          'checks=14655;' in (M / 'fullB/host.stdout').read_text())
    verify_map('retained full B class hashes', E / 'fullB/classes', read(E / 'fullB/class-map.json'))
    for c in read(E / 'fullB/commands.json'):
        check('full B command ' + c['label'], c['exit'] == 0 and c['child_reaped'] and not c['timeout'] and not c['output_limit_exceeded'])
        for stream in ['stdout', 'stderr']:
            check('full B output ' + c['label'] + '.' + stream, matches(E / 'fullB' / (c['label'] + '.' + stream), c[stream]))
    check('full B scoped success', full['status'] == 'passed-host-only' and full['source_stable'] and
          full['cleanup']['children_reaped'] and full['cleanup']['scratch_removed'] and not full['native_or_capture_processes_started_or_queried'])
    fixture_control = read(E / 'fixture-control.json')
    check('fixture positive and negative logs', (E / 'fixture-control-fixed.log').read_text().strip() == 'PASS controlled fixture checks=48' and
          'no click listener still toggles but returns false' in (E / 'fixture-control-old.log').read_text() and
          [c['exitCode'] for c in fixture_control['commands']] == [0, 0, 0, 1])
    for c in fixture_control['commands']:
        check('fixture command record ' + c['output'], matches(E / c['output'], c['outputSHA256']) and
              c['cleanup']['leaderReaped'] and c['cleanup']['groupAbsent'] and
              c['cleanup']['pid'] not in HELD and c['cleanup']['pgid'] not in HELD)
    check('fixture old and corrected leaf identities', fixture_control['oldLeafSHA256'] == sha(MOTION / PATHS[1]) and
          fixture_control['correctedLeafSHA256'] == sha(CANDIDATE / PATHS[1]))

    expected_output = ('INSTRUMENTATION_RESULT: checks=11\n'
        'INSTRUMENTATION_RESULT: scope=actual JNI/Swift/native smoke test only; no complete native/IME/physical/GA acceptance\n'
        'INSTRUMENTATION_RESULT: togglePerformClickReturn=false\nINSTRUMENTATION_CODE: -1')
    raw_output = (E / 'canonical-instrumentation.log').read_text().strip()
    check('exact eleven-assertion runtime output', raw_output == expected_output == runtime['runtime']['instrumentationOutput'])
    check('one narrow API37 arm64 attempt', runtime['runtime']['passed'] and runtime['status'] == 'passed-smoke' and
          runtime['nativeInstancesStarted'] == 1 and runtime['elapsedSeconds'] == 53.65 and
          runtime['runtime']['environment']['ro.build.version.sdk'] == '37' and
          runtime['runtime']['environment']['ro.product.cpu.abi'] == 'arm64-v8a' and not runtime['physicalTargetsQueried'])
    for prop, value in runtime['runtime']['environment'].items():
        check('environment output ' + prop, (E / ('target-' + prop + '.log')).read_text().strip() == value)
    commands = runtime['commands']
    groups = runtime['cleanup']['groups']
    check('50 unique owned groups match 50 commands', len(groups) == len(commands) == 50 and
          len({g['pid'] for g in groups}) == 50 and
          {(g['pid'], g['pgid']) for g in groups} == {(c['pid'], c['pgid']) for c in commands})
    for c in commands:
        g = next(g for g in groups if g['pid'] == c['pid'])
        check('runtime command custody ' + c['name'], matches(E / c['output'], c['sha256']) and
              c['processCleanup'] == g and g['pid'] == g['pgid'] and g['pid'] not in HELD and
              g['groupAbsent'] and g['leaderReaped'])
        if Path(c['argv'][0]).name == 'adb' and c['name'] != 'adb-version':
            check('private ADB target ' + c['name'], c['argv'][1:5] == ['-P', '63338', '-s', 'emulator-5570'])
    byname = {c['name']: c for c in commands}
    for name in ['production-java17-sdk37', 'canonical-instrumentation-java17-sdk37', 'canonical-d8-min28',
                 'install-diagnostic-apk', 'canonical-instrumentation', 'stop-only-owned-emulator']:
        check('retained command exit ' + name, byname[name]['exitCode'] == 0)
    check('native compilation uses 21 real products and two canonical tests',
          len([a for a in byname['production-java17-sdk37']['argv'] if a.endswith('.java')]) == 21 and
          len([a for a in byname['canonical-instrumentation-java17-sdk37']['argv'] if a.endswith('.java')]) == 2)
    check('private server is emulator-only', '--one-device' in byname['owned-adb-server']['argv'])
    cleanup = read(E / 'cleanup-port-recheck.json')
    check('port cleanup delayed observation accurately retained', cleanup['initialImmediateObservation'] == runtime['cleanup']['ports'] and
          cleanup['ports'] == {'5570': 'released', '5571': 'released', '63338': 'released'} and cleanup['allPortsReleased'])
    check('owned scratch AVD and disposable keys absent', not Path(runtime['scratch']).exists() and not Path(runtime['avd']['path']).exists() and
          runtime['cleanup']['scratchRemoved'] and not runtime['cleanup']['privateKeyRetained'])
    control = read(E / 'cleanup-control.json')
    check('cleanup controls fail closed on inaccessible or unknown group', control['status'] == 'passed' and
          [c['groupAbsent'] for c in control['controls']] == [True, True, True, False, False])
    check('no broad native or GA claim', not runtime['nativeAcceptance'] and not runtime['gaAcceptance'])
    return {'oraclePatchSHA256': PIN, 'sourceClosureSHA256': closure, 'runtime': runtime['runtime'],
            'sourceRevision': runtime['sourceRevision'], 'sourceTree': runtime['sourceTree'],
            'oraclePatchFiles': result['oraclePatchFiles'], 'hostMatrixSHA256': sha(E / 'fullB/barrier-cases.json'),
            'nativeLibraries': native, 'cleanup': cleanup, 'toolIdentities': checked_tools,
            'evidenceManifestSHA256': sha(E / 'evidence-manifest.json')}

started = datetime.datetime.now(datetime.timezone.utc).isoformat()
try:
    details = main()
except Exception as error:
    check('audit completed without file/schema errors', False, repr(error))
    details = {}
report = {'schema': 1, 'startedUTC': started, 'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'command': ['python3', '-B', str(Path(__file__).resolve())], 'python': sys.version,
          'platform': platform.platform(), 'candidate': str(CANDIDATE), 'parent': str(PARENT),
          'checks': checks, 'failedChecks': [c for c in checks if not c['passed']],
          'checkedFileIdentities': identities, 'details': details,
          'compilerJVMNativeRuns': 0, 'processOrPortProbes': 0, 'sourceEdits': 0, 'children': 0, 'commits': 0, 'pushes': 0}
(OUT / 'audit.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({'checks': len(checks), 'failedChecks': report['failedChecks'], 'detailsAvailable': bool(details)}))

#!/usr/bin/env python3
"""Audit and seal only the private concrete-attempt owner slice; run no builds."""
import datetime
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CACHE = {'.build', '.swiftpm', '__pycache__', '.git'}
PRODUCTION = 'capability-activation/Sources/MixerCapabilityActivation/'
TEST = 'capability-activation/Tests/MixerCapabilityActivationTests/ConcreteAttemptTests.swift'
IMPLEMENTATION = [PRODUCTION + 'CapabilityConcreteAttempt.swift',
                  PRODUCTION + 'CapabilityConcreteRetirement.swift', TEST]
PINS = {
    '2026-10-23-candidate-4': 'e9acbf61e7bd9c7300aa02671c3b7ad5faeccac73f4d64b2e916627e2fbb2685',
    '2026-10-23-tsan-replay-1': '9e346940facaf32bbfecee9d2004708f6aa156493cf18168a4b9c991a6383c0a',
    '2026-10-23-derived-1': '94bd92550cb3f70875f64350c4da4b1555e580c5df43e6bb51a051afa557c558',
    '2026-10-23-opacity': 'baf1a7f457a87c3749ae0ce7376af1652bd9916bb3d7116361e2468fa6dc97f2',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text())


def sealed(path, digest):
    require(sha(path) == digest, 'sealed receipt ' + str(path))
    return read(path)


def mapping_text(mapping):
    return ''.join(digest + '  ' + name + '\n' for name, digest in sorted(mapping.items()))


def file_manifest(paths):
    return mapping_text({str(p.relative_to(ROOT)): sha(p) for p in paths})


def checked_source(mapping, export, manifest, digest):
    require(sha(manifest) == digest and manifest.read_text() == mapping_text(mapping),
            'closed source manifest ' + str(manifest))
    for name, pin in mapping.items():
        require(not CACHE.intersection(Path(name).parts), 'no cache input ' + name)
        require(sha(export / name) == pin, 'immutable exported source ' + name)


def checked_artifacts(mapping, verified):
    for value in mapping.values():
        if isinstance(value, dict) and 'path' in value and 'sha256' in value:
            path = Path(value['path'])
            require(sha(path) == value['sha256'], 'retained artifact ' + str(path))
            verified[str(path)] = value['sha256']
        elif isinstance(value, dict):
            checked_artifacts(value, verified)


def checked_commands(receipt, folder, logs, failed_name=None, failed_exit=None):
    for row in receipt['commands']:
        path = folder / row['log']
        raw = path.read_bytes()
        require(sha(path) == row['log_sha256'], 'actual command log ' + str(path))
        expected = failed_exit if failed_name is not None and row.get('name') == failed_name else row.get('expected_exit', 0)
        require(row['exit_code'] == expected, 'expected command outcome ' + str(path))
        if 'expected_tests' in row and expected == 0:
            counts = [int(n) for n in re.findall(rb'Executed (\d+) tests?, with 0 failures', raw)]
            require(counts == row['observed_test_counts'] and counts and
                    counts[-1] == row['expected_tests'], 'actual XCTest count ' + str(path))
            require(b'WARNING: ThreadSanitizer' not in raw, 'no TSan warning')
        logs[str(path.relative_to(ROOT))] = sha(path)


def check_symbols(folder, modes):
    for mode in modes:
        raw = (folder / (mode + '-native-symbols.log')).read_text()
        tests = (folder / (mode + '-test-native-symbols.log')).read_text()
        require(len(re.findall(r'\b_mixer_vm_capability_session_enable_v1$', raw, re.M)) == 1,
                'one native registry definition ' + mode)
        require(re.search(r'\b_mixer_vm_\w+$', tests, re.M) is None,
                'no second native VM in test bundle ' + mode)


def audit():
    receipts = {name: sealed(HERE / name / 'receipt.json', pin) for name, pin in PINS.items()}
    base = receipts['2026-10-23-candidate-4']
    base_path = HERE / '2026-10-23-candidate-4/receipt.json'
    original = Path(base['export'])
    require(base['status'] == 'failed check preserved' and
            base['problem'] == 'tsan-tests unexpected exit -6', 'preserved failed launcher')
    require(len(base['source_files']) == 127, 'exact base 127 inputs')
    checked_source(base['source_files'], original, base_path.parent / 'source-manifest.sha256',
                   base['source_manifest_sha256'])
    for name in IMPLEMENTATION + ['verification/capability-concrete-attempt/Bundle.swift']:
        require(sha(ROOT / name) == base['source_files'][name], 'unchanged implementation/test ' + name)

    dep_path = ROOT / base['dependency_receipt']['path']
    dep = sealed(dep_path, base['dependency_receipt']['sha256'])
    require(dep['status'] == 'scoped private transitions passed; independent review pending' and
            dep['source_unchanged'], 'immutable owner-qualified dependency, not independent approval')
    require(len(dep['source_files']) == 122 and dep['source_manifest_sha256'] ==
            base['dependency_manifest_sha256'], '122 dependency source inputs')
    checked_source(dep['source_files'], Path(dep['export']), dep_path.parent / 'source-manifest.sha256',
                   dep['source_manifest_sha256'])
    require({n: base['source_files'][n] for n in dep['source_files']} == dep['source_files'],
            'base borrows exact frozen dependency, not live source')
    artifacts = {}
    for name, digest in base['native_files'].items():
        path = Path(base['native_directory']) / name
        require(sha(path) == digest and dep['native_files'][name] == digest, 'one pinned native artifact')
        artifacts[str(path)] = digest
    for mode, info in base['retained_products'].items():
        path = Path(info['directory']) / 'products/libMixerCapabilityActivation.a'
        require(sha(path) == info['library_sha256'], 'borrowed dependency library ' + mode)
        artifacts[str(path)] = info['library_sha256']
    checked_artifacts(base['artifacts'], artifacts)
    logs = {}
    checked_commands(base, base_path.parent, logs, 'tsan-tests', -6)
    require(len(base['commands']) == 15, 'closed main matrix command scope')
    failed = (base_path.parent / 'tsan-tests.log').read_bytes()
    require(b'Interceptors are not working' in failed and b'Executed ' not in failed,
            'TSan launcher failed before XCTest execution')
    for mode in ['debug', 'release']:
        row = next(c for c in base['commands'] if c['name'] == mode + '-tests')
        require(row['expected_tests'] == 6 and row['exit_code'] == 0, 'six unmodified tests ' + mode)
    check_symbols(base_path.parent, ['debug', 'release'])

    replay = receipts['2026-10-23-tsan-replay-1']
    replay_dir = HERE / '2026-10-23-tsan-replay-1'
    require(replay['status'] == 'passed' and replay['exit_code'] == 0 and
            replay['base_receipt']['sha256'] == sha(base_path) and
            replay['base_source_manifest_sha256'] == base['source_manifest_sha256'] and
            replay['base_source_unchanged'] and replay['artifacts_unchanged'], 'exact retained TSan replay')
    require(sha(HERE / 'replay-tsan.py') == replay['driver_sha256'], 'replay driver')
    raw = (replay_dir / 'tests.log').read_bytes()
    counts = [int(n) for n in re.findall(rb'Executed (\d+) tests?, with 0 failures', raw)]
    require(sha(replay_dir / 'tests.log') == replay['log_sha256'] and counts == [6, 6, 6] and
            counts == replay['observed_test_counts'] and b'WARNING: ThreadSanitizer' not in raw,
            'six actual TSan replay tests')
    require(sha(replay_dir / 'xctest-path.log') == replay['xctest_path_log_sha256'] and
            replay['command'][0] == (replay_dir / 'xctest-path.log').read_text().strip() and
            'xcrun' not in replay['command'][0], 'resolved XCTest executable used directly')
    for path, digest in replay['artifacts'].items():
        require(sha(Path(path)) == digest, 'unchanged exact TSan module/bundle')
        artifacts[path] = digest
    for name in ['tests.log', 'xctest-path.log']:
        logs[str((replay_dir / name).relative_to(ROOT))] = sha(replay_dir / name)

    driver = 'verification/capability-concrete-attempt/run.py'
    before = "            run(mode+'-tests',['xcrun','xctest',str(bundle)],env=env,expected_tests=6)"
    after = """            # /usr/bin/xcrun strips DYLD_* at its protected launcher boundary.
            # Resolve first, then execute XCTest directly so TSan loads at launch.
            xctest=subprocess.check_output(['xcrun','--find','xctest'],env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},text=True).strip()
            run(mode+'-tests',[xctest,str(bundle)],env=env,expected_tests=6)"""
    old = (original / driver).read_text()
    require(old.count(before) == 1 and (ROOT / driver).read_text() == old.replace(before, after),
            'current driver differs only by preserved launcher repair')

    derived = receipts['2026-10-23-derived-1']
    derived_dir = HERE / '2026-10-23-derived-1'
    require(derived['status'] == 'passed' and derived['base_unchanged'] and derived['derived_unchanged'] and
            derived['base_source'] == base['source_files'] and
            derived['base_receipt']['sha256'] == sha(base_path), 'exact derived base binding')
    require(len(derived['derived_source']) == 131 and len(derived['fixed_edits']) == 5,
            '131 derived inputs with exactly five fixed edits')
    checked_source(derived['derived_source'], Path(derived['export']),
                   derived_dir / 'derived-source-manifest.sha256',
                   sha(derived_dir / 'derived-source-manifest.sha256'))
    for name, digest in derived['own_inputs'].items():
        require(sha(HERE / name) == digest, 'fixed derived control ' + name)
    expected = {name: (original / name).read_bytes() for name in base['source_files']}
    patch = []
    for name, before, after in derived['fixed_edits']:
        path = PRODUCTION + name
        old = expected[path].decode()
        require(old.count(before) == 1, 'unique bounded derived edit')
        new = old.replace(before, after)
        expected[path] = new.encode()
        patch.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                        fromfile='base/' + name, tofile='derived/' + name))
    require((derived_dir / 'test-only.patch').read_text() == ''.join(patch) and
            sha(derived_dir / 'test-only.patch') == derived['patch_sha256'], 'exact five-edit mutation map')
    for name in derived['own_inputs']:
        expected['verification/capability-concrete-attempt/' + name] = (HERE / name).read_bytes()
    expected[PRODUCTION + 'ConcreteProbeHooks.swift'] = (HERE / 'DerivedHooks.swift').read_bytes()
    expected[TEST] += b'\n' + (HERE / 'DerivedTests.swift').read_bytes()
    require({n: hashlib.sha256(raw).hexdigest() for n, raw in expected.items()} == derived['derived_source'],
            'all derived bytes reconstruct from exact base plus labelled controls')
    checked_commands(derived, derived_dir, logs)
    require(len(derived['commands']) == 21 and
            len([c for c in derived['commands'] if c.get('expected_tests') == 1]) == 9,
            'three original isolated probes in each mode')
    check_symbols(derived_dir, ['debug', 'release', 'tsan'])
    checked_artifacts(derived['artifacts'], artifacts)

    opacity = receipts['2026-10-23-opacity']
    opacity_dir = HERE / '2026-10-23-opacity'
    require(opacity['status'] == 'passed' and len(opacity['commands']) == 3 and
            opacity['base_receipt']['sha256'] == sha(base_path) and
            sha(HERE / 'opacity.py') == opacity['driver_sha256'], 'three ordinary-import checks')
    checked_commands(opacity, opacity_dir, logs)
    for row in opacity['commands']:
        require(sha(ROOT / row['source']) == row['source_sha256'], 'external compile probe source')
    for name, symbol in [('attempt', 'CapabilityConcreteAttempt'), ('retirement', 'CapabilityConcreteRetirement')]:
        require(("cannot find type '" + symbol + "' in scope") in (opacity_dir / (name + '.log')).read_text(),
                'private external type rejection ' + symbol)

    historical = {}
    preflight = read(HERE / '2026-10-23-candidate-1/preflight.json')
    require(preflight['commands_executed'] == [] and
            sha(HERE / '2026-10-23-candidate-1/source-manifest.sha256') ==
            preflight['source_manifest_sha256'], 'preflight is not a compiler/test run')
    for name in ['2026-10-23-candidate-2', '2026-10-23-candidate-3']:
        folder = HERE / name
        receipt = read(folder / 'receipt.json')
        require(receipt['status'] == 'failed check preserved' and len(receipt['commands']) == 4 and
                receipt['problem'] == 'debug-tests-link unexpected exit 1', 'historical harness failure')
        checked_source(receipt['source_files'], Path(receipt['export']), folder / 'source-manifest.sha256',
                       receipt['source_manifest_sha256'])
        checked_commands(receipt, folder, logs, 'debug-tests-link', 1)
        for source in IMPLEMENTATION[:2]:
            require(receipt['source_files'][source] == base['source_files'][source],
                    'no production change during harness repair')
        for source in [TEST, driver]:
            require(sha(folder / 'historical-inputs' / Path(source).name) == receipt['source_files'][source],
                    'durable historical test/driver repair input')
        historical[name] = {'receipt_sha256': sha(folder / 'receipt.json'),
                            'source_manifest_sha256': receipt['source_manifest_sha256'],
                            'problem': receipt['problem'], 'production_compile_exit': 0,
                            'tests_executed': 0}
    return dict(status='scoped concrete owner source and executable evidence audit passed',
                base_receipts={n: {'path': str((HERE / n / 'receipt.json').relative_to(ROOT)), 'sha256': p}
                               for n, p in PINS.items()},
                implementation={name: sha(ROOT / name) for name in IMPLEMENTATION},
                dependency_receipt=base['dependency_receipt'], dependency_source_inputs=122,
                dependency_source_manifest_sha256=dep['source_manifest_sha256'],
                qualified_source_inputs=127, source_manifest_sha256=base['source_manifest_sha256'],
                source_export=base['export'], live_dependency_equality_claimed=False,
                current_driver_launcher_repair_sha256=sha(ROOT / driver),
                verified_logs=logs, verified_artifacts=artifacts, preserved_historical_failures=historical,
                preserved_pretest_tsan_failure='2026-10-23-candidate-4/tsan-tests.log',
                unmodified_tests_per_mode={'debug': 6, 'release': 6, 'tsan_exact_replay': 6},
                derived_tests_per_mode={'debug': 3, 'release': 3, 'tsan': 3},
                derived_input_count=131, derived_fixed_edits=5, opacity_rejections=2, opacity_positive=1,
                invariant_scope=['Immediate I/O-free adapter-obligation reservation; adapterOwner always nil',
                                 'Exclusive concrete adapters; no owned group/session in retirement sink',
                                 'Actual bridge retirement plus returned setup and method frames required',
                                 'Obligation retirement returns before waiter success publication',
                                 'Cancellation/duplicate waiter never fabricates retirement',
                                 'Original startup cutoff passed to owned native enable SPI',
                                 'No new Task/dispatch cleanup/consumer/polling loop or authority ingress'])


def main():
    result = audit()
    names = ['README.md', 'run.py', 'replay-tsan.py', 'derived.py', 'opacity.py', 'finalize.py',
             'Bundle.swift', 'DerivedHooks.swift', 'DerivedTests.swift',
             'CompileNegative/attempt.swift', 'CompileNegative/retirement.swift',
             'CompileNegative/public-positive.swift']
    sources = [HERE / n for n in names]
    implementation_manifest = file_manifest([ROOT / name for name in IMPLEMENTATION])
    verification_manifest = file_manifest(sources)
    if '--check' in sys.argv:
        receipt = read(HERE / 'final-receipt.json')
        require(read(HERE / 'owner-audit.json') == result, 'stable owner audit')
        require((HERE / 'implementation-source.sha256').read_text() == implementation_manifest,
                'implementation/test source seal')
        require((HERE / 'verification-source.sha256').read_text() == verification_manifest,
                'verification source seal')
        for field, name in [('owner_audit_sha256', 'owner-audit.json'),
                            ('implementation_source_manifest_sha256', 'implementation-source.sha256'),
                            ('verification_source_manifest_sha256', 'verification-source.sha256'),
                            ('evidence_manifest_sha256', 'evidence-manifest.sha256')]:
            require(sha(HERE / name) == receipt[field], 'aggregate binding ' + field)
        for line in (HERE / 'evidence-manifest.sha256').read_text().splitlines():
            digest, name = line.split('  ', 1)
            require(not CACHE.intersection(Path(name).parts) and sha(ROOT / name) == digest,
                    'noncache final evidence ' + name)
        evidence = [p for p in HERE.rglob('*') if p.is_file() and
                    not CACHE.intersection(p.relative_to(HERE).parts) and
                    p.name not in ['final-receipt.json', 'evidence-manifest.sha256', '.DS_Store']]
        require((HERE / 'evidence-manifest.sha256').read_text() == file_manifest(evidence) and
                len(evidence) == receipt['evidence_files'], 'closed complete evidence file set')
        print('Concrete-attempt owner seal verified ' + sha(HERE / 'final-receipt.json'))
        return
    (HERE / 'owner-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    (HERE / 'implementation-source.sha256').write_text(implementation_manifest)
    (HERE / 'verification-source.sha256').write_text(verification_manifest)
    evidence = [p for p in HERE.rglob('*') if p.is_file() and
                not CACHE.intersection(p.relative_to(HERE).parts) and
                p.name not in ['final-receipt.json', 'evidence-manifest.sha256', '.DS_Store']]
    (HERE / 'evidence-manifest.sha256').write_text(file_manifest(evidence))
    receipt = dict(status='private concrete-attempt owner scoped tests passed; independent review pending',
                   completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   owner_audit_sha256=sha(HERE / 'owner-audit.json'),
                   implementation_source_manifest_sha256=sha(HERE / 'implementation-source.sha256'),
                   verification_source_manifest_sha256=sha(HERE / 'verification-source.sha256'),
                   evidence_manifest_sha256=sha(HERE / 'evidence-manifest.sha256'),
                   implementation_and_test_files=len(IMPLEMENTATION), verification_source_files=len(sources),
                   evidence_files=len(evidence), source_manifest_sha256=result['source_manifest_sha256'],
                   dependency_source_manifest_sha256=result['dependency_source_manifest_sha256'],
                   unmodified_tests_per_mode=result['unmodified_tests_per_mode'],
                   original_derived_tests_per_mode=result['derived_tests_per_mode'],
                   ordinary_import_opacity_rejections=2, ordinary_import_positive=1,
                   new_production_files=IMPLEMENTATION[:2], new_test_file=TEST,
                   preexisting_production_edited=False, final_coordinator_composition_qualified=False,
                   independent_review_qualified=False, committed=False, pushed=False,
                   limitations=['Qualification uses immutable transition candidate2 and old Signals; newer shared composition is separate',
                                'Candidate4 failed pretest TSan launcher remains preserved; exact retained bundle replay passes without rebuild',
                                'Five fixed derived barriers/counters/faults affect copies only; no native/exit/ack result fabricated',
                                'Required external weak terminal consumer and no transitive sink back-edge belong to coordinator scope',
                                'Missing bridge retirement/quarantine retains outer capacity; cancellation is not native exit',
                                'Swift TSan does not instrument Rust/platform internals; no package/Rust/dependency graph rebuilt',
                                'No devices, public execution authority, health, atomic hard-real-time cutoff, rollback, global OS resource cap, Task/allocator destruction, production/publication or GA claim'])
    (HERE / 'final-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(final_receipt_sha256=sha(HERE / 'final-receipt.json'),
                          implementation_source_manifest_sha256=receipt['implementation_source_manifest_sha256'],
                          verification_source_manifest_sha256=receipt['verification_source_manifest_sha256'],
                          evidence_manifest_sha256=receipt['evidence_manifest_sha256'],
                          evidence_files=len(evidence))))


if __name__ == '__main__':
    main()

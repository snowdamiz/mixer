#!/usr/bin/env python3
"""Independent file-only review. Runs no compiler/native tool/service or Git command."""
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import plistlib
import stat
import subprocess
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / 'verification/apple-focus-reference-diagnostic-v1'
OLD = ROOT / 'verification/apple-focus-diagnostic-runtime-v1'
ORIGINAL_BUILD = ROOT / 'verification/apple-toggle-keyboard-focus-diagnostic-v1-build'
EXPECTED_HANDOFF = '9f066db167168e8ab0c78b2147f857ba3980d965a69b681e566e5e185f6a0d3c'
EXPECTED_PREPARED = 'e71f226c97182e2f8b8b8cd0f2f5e07ffa43e54d540c34189516123e21fb9ed1'
EXPECTED_TREE = '696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a'
CONTROLS = []


def stable(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def row(path):
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and path.resolve() == path
    return {'kind': 'file', 'bytes': info.st_size, 'mode': stat.S_IMODE(info.st_mode), 'sha256': digest(path.read_bytes())}


def read_json(path):
    return json.loads(path.read_bytes())


def check(name, condition, detail=None):
    item = {'name': name, 'passed': condition is True}
    if detail is not None:
        item['detail'] = detail
    CONTROLS.append(item)
    print(('PASS ' if item['passed'] else 'FAIL ') + name, flush=True)


def archive(path, expected, prefix):
    files, dirs, seen = {}, {}, set()
    with tarfile.open(path, 'r:gz') as source:
        for member in source:
            p = PurePosixPath(member.name)
            assert member.name and not p.is_absolute() and '..' not in p.parts and str(p) == member.name
            assert member.name not in seen
            seen.add(member.name)
            assert member.name == prefix.removesuffix('/') or member.name.startswith(prefix)
            if member.isdir():
                dirs[member.name] = member.mode
                assert member.size == 0 and member.mode == 0o755
                continue
            assert member.isfile() and not member.islnk() and not member.issym()
            data = source.extractfile(member).read()
            rel = member.name.removeprefix(prefix)
            assert expected[rel] == {'kind': 'file', 'mode': member.mode, 'bytes': len(data), 'sha256': digest(data)}
            files[rel] = data
    expected_dirs = {str(parent) for name in expected for parent in PurePosixPath(prefix + name).parents if str(parent) != '.'}
    assert set(files) == set(expected) and set(dirs) == expected_dirs
    return files


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    assert not (BASE / 'receipt.json').exists(), 'Retain prior independent review run'
    handoff = read_json(PRODUCER / 'handoff.json')
    prepared = read_json(PRODUCER / 'prepared.json')
    check('frozen-handoff-identity', row(PRODUCER / 'handoff.json')['sha256'] == EXPECTED_HANDOFF)
    check('frozen-members-and-tree', all(row(ROOT / name) == item for name, item in handoff['members'].items())
          and digest(stable(handoff['members'])) == handoff['memberTreeSHA256'])
    check('prepared-identity-and-source-tree', row(PRODUCER / 'prepared.json')['sha256'] == EXPECTED_PREPARED
          and prepared['derivativeSourceTreeSHA256'] == EXPECTED_TREE
          and digest(stable(prepared['derivativeSources'])) == EXPECTED_TREE)
    check('input-bindings', all(row(ROOT / name) == item for name, item in prepared['inputs'].items())
          and digest(stable(prepared['inputs'])) == prepared['inputTreeSHA256'])
    old_packet = read_json(OLD / 'packet.json')
    old_outputs = read_json(OLD / 'output-manifest.json')
    inherited = read_json(ORIGINAL_BUILD / 'source-manifest.json')
    selected_manifest = read_json(OLD / 'selected-runtime-source-manifest.json')
    check('original-failure-packet-and-manifest-bindings', digest((OLD / 'packet.json').read_bytes()) == prepared['inheritedPacketSHA256']
          and row(OLD / 'output-manifest.json')['sha256'] == old_packet['outputManifestSHA256']
          and row(OLD / 'selected-runtime-source-manifest.json')['sha256'] == old_packet['selectedSourceArchiveManifestSHA256']
          and inherited['materializedSources'] == old_outputs['acceptedSources']
          and selected_manifest['files'] == old_outputs['selectedRuntime'])
    accepted = archive(ORIGINAL_BUILD / 'accepted-sources.tar.gz', inherited['materializedSources'], 'accepted/')
    derived = archive(PRODUCER / 'accepted-sources.tar.gz', prepared['derivativeSources'], 'accepted/')
    selected = archive(OLD / 'selected-runtime-sources.tar.gz', selected_manifest['files'], 'selected/')
    check('complete-archives-39-39-29', (len(accepted), len(derived), len(selected)) == (39, 39, 29))
    app = 'source/Prototype/main.swift'
    runner = 'harness/UITests/ToggleUITests.swift'
    check('exact-two-source-overlay', {name for name in accepted if accepted[name] != derived[name]} == {app, runner})
    check('app-exact-reversible-initial-preference', derived[app].count(b'{ [referenceButton] }') == 1
          and derived[app].replace(b'{ [referenceButton] }', b'{ [toggle] }') == accepted[app])
    added_branch = b'''        if let requiredFocusBefore {
            let observedFocus = try focus(before)
            let premisePassed = observedFocus == requiredFocusBefore
            try jsonAttachment("Reference first-Tab precondition", ["schema": "mixer.apple-focus-reference-precondition.1",
                "case": caseName, "phase": phase, "generation": baseline["generation"]!, "actionIndex": baseline["actionIndex"]!,
                "requiredFocus": requiredFocusBefore, "observedFocus": observedFocus as Any? ?? NSNull(),
                "passed": premisePassed, "actionInjectionCount": 0, "before": before])
            guard premisePassed else { throw Failure.focus("Reference first-Tab precondition failed before key injection") }
        }
'''
    added_method = b'''    func test010ReferenceFirstTab() throws {
        _ = try launchCase("keyboard-enabled-off", initial: false)
        try key("acquire", "tab", requiredFocusBefore: "plain-uibutton-reference")
    }
'''
    reversed_runner = derived[runner].replace(b', requiredFocusBefore: String? = nil', b'').replace(added_branch, b'').replace(added_method, b'')
    check('runner-exact-reversible-overlay-preserves-all-original-bytes', reversed_runner == accepted[runner]
          and derived[runner].count(added_branch) == derived[runner].count(added_method) == 1)
    check('premise-guard-before-one-unchanged-public-key-call', derived[runner].index(added_branch) < derived[runner].index(b'        if value == "shift-tab" { app.typeKey')
          and derived[runner].count(b'app.typeKey') == accepted[runner].count(b'app.typeKey') == 2)
    check('only-reviewed-selected-method-contract', prepared['methods'] == ['test000PublicSettingsFullKeyboardAccess', 'test010ReferenceFirstTab']
          and prepared['maximumApplicationKeyInjections'] == 1)
    check('pure-oracle-nine-member-bindings', len(prepared['pureOracleClosure']) == 9
          and all(digest(selected[name]) == item['sha256'] for name, item in prepared['pureOracleClosure'].items()))
    check('observer-v2-unchanged', digest(selected['command_observer.py']) == prepared['observerV2SHA256'])
    freeze = subprocess.run([sys.executable, '-B', str(PRODUCER / 'freeze.py'), 'verify'], cwd=ROOT, capture_output=True, check=False)
    (BASE / 'freeze-verify.stdout.log').write_bytes(freeze.stdout)
    (BASE / 'freeze-verify.stderr.log').write_bytes(freeze.stderr)
    check('producer-file-only-freeze-verification', freeze.returncode == 0, freeze.stdout.decode().strip())

    contract = load('reviewed_reference_contract', PRODUCER / 'reference_contract.py')
    with tempfile.TemporaryDirectory(prefix='pure-oracle-', dir=BASE) as temporary:
        pure = Path(temporary)
        for name in prepared['pureOracleClosure']:
            target = pure / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(selected[name])
        oracle = load('independent_unchanged_pure_oracle', pure / 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py')
        check('only-pure-nine-files-materialized', len([p for p in pure.rglob('*') if p.is_file()]) == 9)
        old_before = read_json(OLD / 'runtime/captures/0001-before-1.json')
        old_after = read_json(OLD / 'runtime/captures/0001-after-1.json')
        retained = read_json(OLD / 'runtime/captures/0001-keyboard-witness-1.json')
        baseline = copy.deepcopy(old_before['observation'])
        baseline.update(keyboardWitness=retained['witness'], keyboardBinding=retained['binding'])
        replayed = oracle.verdict('diagnostic', 'keyboard-enabled-off', 'native-keyboard', baseline, old_after['observation'], old_before['signature'] != old_after['signature'])
        recorded = copy.deepcopy(old_after['verdict'])
        for field in ['ownedSimulatorIdentity', 'generation', 'actionIndex']:
            recorded.pop(field)
        check('complete-original-failure-replay', stable(replayed) == stable(recorded)
              and replayed['passed'] is False
              and [k for k, v in replayed['predicates'].items() if v is not True] == ['actualNativeFocusTraversal'])
        (BASE / 'original-failure-replay.json').write_bytes(stable(replayed))

        def fixture(destination='next-focus'):
            before = copy.deepcopy(old_before['observation'])
            before['state']['focused'] = False
            after = copy.deepcopy(before)
            witness = copy.deepcopy(retained['witness'])
            for snapshot, focus in [(witness['before'], 'plain-uibutton-reference'), (witness['after'], destination)]:
                for name, element in snapshot['elements'].items():
                    element['hasFocus'] = name == focus
            binding = copy.deepcopy(retained['binding'])
            baseline = copy.deepcopy(before)
            baseline.update(keyboardWitness=witness, keyboardBinding=binding)
            verdict = oracle.verdict('diagnostic', 'keyboard-enabled-off', 'native-keyboard', baseline, after, False)
            premise = {'schema': 'mixer.apple-focus-reference-precondition.1', 'case': 'keyboard-enabled-off', 'phase': 'acquire',
                       'generation': witness['generation'], 'actionIndex': witness['actionIndex'],
                       'requiredFocus': 'plain-uibutton-reference', 'observedFocus': 'plain-uibutton-reference',
                       'passed': True, 'actionInjectionCount': 0, 'before': copy.deepcopy(witness['before'])}
            return premise, verdict, {'before': before, 'after': after, 'fileChanged': False}

        def classify(p, v=None, pair=None):
            return contract.result([p], [] if v is None else [v], oracle, [] if pair is None else [pair])

        p, v, pair = fixture()
        good = classify(p, v, pair)
        check('synthetic-reference-next-is-only-single-diagnostic-success', good['status'] == 'one-original-oracle-result'
              and good['singleTabDiagnosticEvidencePassed'] is True and good['keyInjectionCount'] == 1
              and good['returnedPublicKeyWitnessCount'] == 1)
        for destination in [None, 'plain-uibutton-reference']:
            fp, fv, fpair = fixture(destination)
            outcome = classify(fp, fv, fpair)
            check('strict-original-failure-retained-' + str(destination), outcome['status'] == 'one-original-oracle-result'
                  and outcome['singleTabDiagnosticEvidencePassed'] is False and outcome['originalOracleResults'] == [fv])
        false_p = copy.deepcopy(p)
        false_p['before']['elements']['plain-uibutton-reference']['hasFocus'] = False
        false_p.update(passed=False, observedFocus=None)
        zero = classify(false_p)
        check('complete-false-premise-zero-injections', zero['status'] == 'failed-reference-precondition'
              and zero['keyInjectionCount'] == 0 and zero['originalOracleResults'] == [])
        incomplete = classify(p)
        check('true-premise-missing-witness-injection-count-unknown', incomplete['status'] == 'incomplete-after-passing-precondition'
              and incomplete['keyInjectionCount'] is None and incomplete['singleTabDiagnosticEvidencePassed'] is False)

        invalids = []
        invalids.append(('missing-premise', [], [v], [pair]))
        invalids.append(('duplicate-premise', [p, p], [v], [pair]))
        invalids.append(('duplicate-verdict', [p], [v, v], [pair]))
        invalids.append(('duplicate-application-pair', [p], [v], [pair, pair]))
        invalids.append(('false-premise-with-verdict', [false_p], [v], [pair]))
        invalids.append(('missing-application-pair', [p], [v], []))
        for name, mutate in [
            ('premise-generation-mismatch', lambda p, v, pair: p.update(generation=p['generation'] + 1)),
            ('premise-action-mismatch', lambda p, v, pair: p.update(actionIndex=2)),
            ('premise-wrong-focus-claim', lambda p, v, pair: p.update(observedFocus='authored-toggle')),
            ('premise-injection-claim', lambda p, v, pair: p.update(actionInjectionCount=1)),
            ('premise-extra-field', lambda p, v, pair: p.update(authority=True)),
            ('witness-not-returned', lambda p, v, pair: v['keyboardWitness'].update(returned=False)),
            ('witness-binding-generation-mismatch', lambda p, v, pair: v['keyboardBinding'].update(generation=v['keyboardBinding']['generation'] + 1)),
            ('witness-reordered-times', lambda p, v, pair: v['keyboardWitness'].update(finishedUptime=v['keyboardWitness']['startedUptime'])),
            ('witness-exceeds-window', lambda p, v, pair: v['keyboardWitness']['after'].update(uptime=v['keyboardWitness']['before']['uptime'] + 13)),
            ('premise-before-does-not-match-witness', lambda p, v, pair: p['before'].update(uptime=p['before']['uptime'] - 0.01)),
            ('original-predicate-omitted', lambda p, v, pair: v['predicates'].pop('pairedNativeFocusBefore')),
            ('original-predicate-added', lambda p, v, pair: v['predicates'].update(invented=True)),
            ('original-predicate-false', lambda p, v, pair: v['predicates'].update(pairedNativeFocusBefore=False)),
            ('original-app-replay-mutated', lambda p, v, pair: pair['after']['state'].update(eventCount=999)),
            ('original-case-credit-added', lambda p, v, pair: v.update(cursorCompletionCredit=True)),
        ]:
            mp, mv, mpair = fixture()
            mutate(mp, mv, mpair)
            invalids.append((name, [mp], [mv], [mpair]))
        for name, premises, verdicts, pairs in invalids:
            outcome = contract.result(premises, verdicts, oracle, pairs)
            check(name + '-rejected', outcome['status'] == 'invalid-or-incomplete-evidence'
                  and outcome['singleTabDiagnosticEvidencePassed'] is False, outcome['status'])
        for name in ['completeCaseSet', 'cursorCompletionCredit', 'runPassed', 'fullSixCaseQualification', 'nativeKeyboardQualification', 'carrierAccepted', 'gaAccepted']:
            check('no-fabricated-' + name, good[name] is False)
        cursor = oracle.Cursor('keyboard-enabled-off')
        cursor.command('resume'); cursor.command('reset'); cursor.advance(v['keyboardWitness'])
        check('original-cursor-incomplete-after-one-reference-tab', cursor.acquisitions == 1 and cursor.complete is False and cursor.acquired is False)

        counterexamples = []
        for field in ['originalOraclePassed', 'pairedFocusDisagreement', 'missingAppFocusUpdateSignal', 'nativeAppFocusedBefore', 'nativeAppFocusedAfter']:
            mp, mv, mpair = fixture()
            original = mv[field]
            mv[field] = int(original)
            outcome = classify(mp, mv, mpair)
            check('exact-original-verdict-rejects-boolean-to-int-' + field,
                  outcome['status'] == 'invalid-or-incomplete-evidence',
                  {'mutatedField': field, 'originalType': type(original).__name__, 'mutatedType': 'int', 'status': outcome['status'],
                   'diagnosticSuccess': outcome['singleTabDiagnosticEvidencePassed']})
            if outcome['singleTabDiagnosticEvidencePassed']:
                counterexamples.append({'name': 'typed-original-verdict-' + field, 'syntheticOnly': True,
                                        'premises': [mp], 'verdicts': [mv], 'observations': [mpair], 'actual': outcome})
        for field in ['generation', 'actionIndex']:
            mp, mv, mpair = fixture()
            # The retained generation need not be one; use a numerically equal float.
            mv[field] = float(mv['keyboardWitness'][field])
            outcome = classify(mp, mv, mpair)
            check('runtime-reporting-' + field + '-strict-integer', outcome['status'] == 'invalid-or-incomplete-evidence',
                  {'status': outcome['status'], 'value': mv[field], 'type': 'float'})
            if outcome['singleTabDiagnosticEvidencePassed']:
                counterexamples.append({'name': 'typed-reporting-' + field, 'syntheticOnly': True,
                                        'premises': [mp], 'verdicts': [mv], 'observations': [mpair], 'actual': outcome})
        mp, mv, mpair = fixture()
        mp['before']['uptime'] = 10 ** 1000
        try:
            outcome = classify(mp, mv, mpair)
            rejected_without_exception = outcome['status'] == 'invalid-or-incomplete-evidence'
            observed = outcome['status']
        except Exception as error:
            rejected_without_exception = False
            observed = type(error).__name__ + ': ' + str(error)
        check('malformed-large-integer-uptime-fails-closed-with-classification', rejected_without_exception, observed)
        # This is an integration prerequisite, not an assertion of native authority.
        repeated = classify(copy.deepcopy(p), copy.deepcopy(v), copy.deepcopy(pair))
        check('self-consistent-replay-is-only-synthetic-contract-data', repeated['singleTabDiagnosticEvidencePassed'] is True
              and repeated['nativeKeyboardQualification'] is False,
              'No selected-run identity/freshness input exists; runtime importer must establish authority independently.')
        (BASE / 'counterexamples.json').write_bytes(stable({'schema': 'mixer.apple-focus-reference-independent-counterexamples.1',
                                                          'syntheticOnly': True, 'examples': counterexamples,
                                                          'malformedLargeUptime': observed}))

    compile_base = PRODUCER / 'compile-attempt-1'
    compiled = read_json(compile_base / 'receipt.json')
    commands = read_json(compile_base / 'command-receipts.json')['commands']
    tools = read_json(compile_base / 'tool-bindings.json')
    check('compile-source-and-script-bindings', compiled['preparedSHA256'] == EXPECTED_PREPARED
          and compiled['sourceTreeSHA256'] == EXPECTED_TREE
          and compiled['sourceArchive'] == row(PRODUCER / 'accepted-sources.tar.gz')
          and compiled['buildScript'] == row(PRODUCER / 'build.py'))
    check('compile-all-eight-command-output-bindings', len(commands) == 8
          and all(c['stdoutBinding'] == row(compile_base / c['stdout']) and c['stderrBinding'] == row(compile_base / c['stderr']) for c in commands))
    check('compile-exit-timeout-and-owned-group-receipts', compiled['exitCodes'] == {'app': 0, 'core': 0, 'runner': 0, 'ui': 0}
          and all(c['exitCode'] == 0 and c['timedOut'] is False and c['ownedProcessGroupAbsent'] is True for c in commands))
    scratch = compile_base / 'scratch'
    source_root = scratch / 'accepted'
    expected_source_groups = {'mixer-core': 'source/sdk/Sources/MixerCore/', 'mixer-ui': 'source/sdk/Sources/MixerUI/', 'app': 'source/Prototype/'}
    for c in commands:
        if c['name'] in expected_source_groups:
            actual = [arg.removeprefix(str(source_root) + '/') for arg in c['argv'] if arg.endswith('.swift')]
            expected = sorted(name for name in derived if name.startswith(expected_source_groups[c['name']]) and name.endswith('.swift'))
            check('compile-exact-source-argv-' + c['name'], actual == expected and '-target' in c['argv']
                  and c['argv'][c['argv'].index('-target') + 1] == 'arm64-apple-ios26.0-simulator')
    runner_command = next(c for c in commands if c['name'] == 'runner')
    argv = runner_command['argv']
    check('runner-generic-build-only-exact-destination-signing', argv[1] == 'build-for-testing'
          and argv[argv.index('-destination') + 1] == 'generic/platform=iOS Simulator'
          and 'CODE_SIGNING_ALLOWED=NO' in argv and 'CODE_SIGNING_REQUIRED=NO' in argv
          and argv[argv.index('-project') + 1] == str(source_root / 'harness/MixerToggleUITests.xcodeproj')
          and not any(arg in ['test', 'test-without-building', 'simctl', 'devicectl'] for c in commands for arg in c['argv']))
    check('compiler-tools-current-file-bindings', tools['toolTreeSHA256'] == digest(stable(tools['tools'])) == compiled['toolTreeSHA256']
          and all(row(Path(name).resolve()) == item for name, item in tools['tools'].items()))
    check('retained-tool-version-outputs', (compile_base / 'commands/xcode-version.stdout').read_text() == 'Xcode 26.6\nBuild version 17F113\n'
          and (compile_base / 'commands/sdk-version.stdout').read_text().strip() == '26.5'
          and 'Apple Swift version 6.3.3' in (compile_base / 'commands/swift-version.stdout').read_text()
          and (compile_base / 'commands/python-version.stdout').read_text().strip() == 'Python 3.14.8')
    products_manifest = read_json(compile_base / 'product-manifest.json')
    actual_products, archive_members = {}, {}
    with tarfile.open(compile_base / 'products.tar.gz', 'r:gz') as source:
        seen = set()
        for member in source:
            p = PurePosixPath(member.name)
            assert member.name not in seen and not p.is_absolute() and '..' not in p.parts
            seen.add(member.name)
            if member.isdir():
                continue
            if member.issym():
                target = PurePosixPath(member.linkname)
                assert not target.is_absolute() and '..' not in target.parts
                actual_products[member.name] = {'kind': 'symlink', 'mode': member.mode, 'target': member.linkname}
            else:
                assert member.isfile() and not member.islnk()
                data = source.extractfile(member).read()
                archive_members[member.name] = data
                actual_products[member.name] = {'kind': 'file', 'bytes': len(data), 'mode': member.mode, 'sha256': digest(data)}
    check('compiled-product-complete-tree-bytes-modes-links', actual_products == products_manifest['products']
          and digest(stable(actual_products)) == compiled['productTreeSHA256'] == products_manifest['productTreeSHA256']
          and row(compile_base / 'products.tar.gz') == compiled['productArchive'] == products_manifest['archive'])
    derivation = read_json(compile_base / 'packaging-derivation.json')
    info_before = plistlib.loads(derived['source/Prototype/Info.plist'])
    info_after = plistlib.loads(archive_members['MixerToggleDiagnostics.app/Info.plist'])
    expected_info = copy.deepcopy(info_before); expected_info['MinimumOSVersion'] = '26.0'
    check('packaging-exact-minimum-version-only-derivation', info_after == expected_info
          and derivation['before'] == info_before['MinimumOSVersion'] == '17.0'
          and derivation['product'] == actual_products['MixerToggleDiagnostics.app/Info.plist']
          and derivation['source'] == prepared['derivativeSources']['source/Prototype/Info.plist'])
    cleanup = read_json(compile_base / 'cleanup.json')
    check('compile-scratch-retired-bound-receipt', cleanup == compiled['cleanup']
          and cleanup['removedPath'] == str(scratch) and cleanup['scratchAbsent'] is True and not scratch.exists()
          and cleanup['removedFileBytes'] == 164590153 and cleanup['ownedCompilerGroupsAbsent'] is True)
    check('no-native-runtime-or-qualification-claims', all(compiled[name] is False for name in ['nativeExecuted', 'runtimeSelected', 'uiOrCapturePerformed', 'completeCaseSet', 'runPassed', 'fullSixCaseQualification', 'carrierAccepted', 'gaAccepted'])
          and handoff['runnablePacketAssembled'] is False and compiled['physicalPhones'] == 'disconnected-deferred')
    check('review-owned-pure-scratch-cleaned', not any(p.is_dir() and p.name.startswith('pure-oracle-') for p in BASE.iterdir()))
    check('producer-handoff-unmodified-after-review', row(PRODUCER / 'handoff.json')['sha256'] == EXPECTED_HANDOFF
          and all(row(ROOT / name) == item for name, item in handoff['members'].items()))
    failures = [item['name'] for item in CONTROLS if item['passed'] is False]
    receipt = {'schema': 'mixer.apple-focus-reference-independent-review.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'command': [sys.executable, '-B', str(Path(__file__).resolve())], 'cwd': str(ROOT), 'python': sys.version,
               'pythonExecutable': str(Path(sys.executable).resolve()), 'platform': platform.platform(),
               'sourceRevisionLabel': prepared['sourceRevisionLabel'], 'sourceRevisionMeaning': 'Inherited producer label; reviewed exact hashes without Git commands.',
               'reviewedHandoffSHA256': EXPECTED_HANDOFF, 'reviewedPreparedSHA256': EXPECTED_PREPARED, 'reviewedSourceTreeSHA256': EXPECTED_TREE,
               'controls': CONTROLS, 'controlsRun': len(CONTROLS), 'controlsPassed': len(CONTROLS) - len(failures), 'failedControls': failures,
               'passed': not failures, 'disposition': 'source-and-compilation-bindings-verified-contract-findings-retained' if failures else 'reviewed-with-runtime-authority-prerequisite',
               'compileRerun': False, 'nativeExecuted': False, 'runtimeSelected': False, 'nativeInstancesQueried': 0,
               'servicesStarted': 0, 'gitCommands': 0, 'uiOrCapturePerformed': False, 'hostedAuthorityOrCatalogImported': False,
               'physicalPhones': 'disconnected-deferred', 'completeCaseSet': False, 'runPassed': False, 'gaAccepted': False,
               'cleanup': {'ownedPureOracleScratchAbsent': True, 'producerCompileScratchAbsent': not scratch.exists()},
               'limitations': ['Synthetic controls do not prove any native focus behavior.',
                               'Compile evidence verified from frozen outputs and live tool hashes; compiler was not rerun.',
                               'Process-group absence is the retained producer observation; no new process or native inventory was queried.',
                               'A runtime importer must independently bind a unique authoritative premise and witness to the selected run, device, method and source/product tree.']}
    receipt['reviewSources'] = {'review.py': row(Path(__file__).resolve())}
    receipt['outputs'] = {p.name: row(p) for p in sorted(BASE.iterdir()) if p.is_file() and p.name not in ['receipt.json', 'review.py', 'review.stdout.log', 'review.stderr.log']}
    (BASE / 'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({'controlsRun': len(CONTROLS), 'controlsPassed': len(CONTROLS) - len(failures), 'failedControls': failures, 'nativeExecuted': False}, sort_keys=True))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())

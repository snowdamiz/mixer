#!/usr/bin/env python3
"""Independent bounded macro review: sealed artifacts plus fresh host replays."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = HERE / 'results' / STAMP
OUT.mkdir(parents=True)
(OUT / 'review.py').write_bytes(Path(__file__).read_bytes())
ENV = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
ENV.pop('RUSTC_BOOTSTRAP', None)
COMMANDS = []
DETAILS = {}
DETAILS['reviewScriptSHA256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DETAILS['reviewArgv'] = sys.argv


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_manifest(files):
    return {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}


def manifest(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def load_archive(path):
    with tarfile.open(path) as archive:
        return {member.name.removeprefix('vm/'): archive.extractfile(member).read()
                for member in archive.getmembers() if member.isfile()}


def command(name, argv, cwd=ROOT, source=None, target=None):
    if source is not None:
        assert manifest(cwd) == source, 'source before ' + name
    env = dict(ENV)
    if target is not None:
        env['CARGO_TARGET_DIR'] = str(target)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=1200)
    if source is not None:
        assert manifest(cwd) == source, 'source after ' + name
    row = dict(name=name, argv=argv, cwd=str(cwd), target=str(target) if target else None,
               sourceTreeSHA256=hashlib.sha256(encoded(source)).hexdigest() if source else None,
               startedUTC=started, completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               exitCode=result.returncode, diagnosticBootstrap=False)
    for stream, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
        output = OUT / (name + '.' + stream)
        output.write_bytes(data)
        row[stream] = output.name
        row[stream + 'SHA256'] = sha(output)
    COMMANDS.append(row)
    print(name, result.returncode, flush=True)
    assert result.returncode == 0, name
    return result.stdout.decode()


def method(text, name):
    start = text.index('fn ' + name + '(')
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def marker_rows(text, markers):
    rows = []
    for line in text.splitlines():
        for marker in markers:
            at = line.find(marker)
            if at >= 0:
                rows.append(line[at:])
                break
    return rows


def independent_build(name, files, selected, lib=False):
    source = OUT / name / 'vm'
    source.mkdir(parents=True)
    for path, data in files.items():
        dest = source / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    expected = digest_manifest(files)
    (OUT / (name + '-manifest.json')).write_bytes(encoded(expected))
    argv = ['cargo', 'test', '--locked', '--offline', '--all-features', '--release',
            '--no-run', '--message-format=json']
    argv += ['--lib'] if lib else ['--test', 'span_control_extraction']
    output = command(name + '-build', argv, source, expected, HERE / 'target' / STAMP / name)
    binaries = []
    for line in output.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if item.get('reason') == 'compiler-artifact' and item.get('executable') and item.get('profile', {}).get('test'):
            binaries.append(Path(item['executable']))
    assert len(binaries) == 1
    binary = binaries[0]
    listing = command(name + '-list', [str(binary), '--list'], source, expected)
    identities = [line[:-6] for line in listing.splitlines() if line.endswith(': test')]
    assert len(identities) == len(set(identities))
    assert set(selected) <= set(identities)
    outputs = []
    for index, test in enumerate(selected):
        result = command(name + '-run-' + str(index),
                         [str(binary), test, '--exact', '--nocapture', '--test-threads=1'],
                         source, expected)
        assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in result
        outputs.append(result)
    return dict(binary=str(binary), binarySHA256=sha(binary), listedTests=identities,
                executedTests=selected, sourceTreeSHA256=hashlib.sha256(encoded(expected)).hexdigest()), outputs


def main():
    receipt_path = Path(sys.argv[1]).resolve()
    folder = receipt_path.parent
    receipt = json.loads(receipt_path.read_text())
    assert receipt['status'] == 'host-bounded-executable-parity-complete-root-review-pending'
    assert all(receipt[key] is False for key in ['productHooksAdded', 'swiftInvocation', 'nativeRuntime',
                                                'physicalRuntime', 'publication', 'gaAcceptance'])
    DETAILS['producerReceipt'] = str(receipt_path.relative_to(ROOT))
    DETAILS['producerReceiptSHA256'] = sha(receipt_path)
    inherited_path = folder.parent / receipt['inheritedReceipt']
    assert sha(inherited_path) == receipt['inheritedReceiptSHA256']
    inherited = json.loads(inherited_path.read_text())
    inherited_binaries = [entry for entry in inherited['binaries']
                          if entry['label'].startswith('baseline-') and '-probe' not in entry['label']]
    assert len(inherited_binaries) == 16
    inherited_names = {entry[key] for entry in inherited_binaries for key in ['listCommand', 'runCommand']}
    inherited_names |= {entry['label'] + '-build' for entry in inherited_binaries}
    inherited_commands = [entry for entry in inherited['commands'] if entry['name'] in inherited_names]
    assert {entry['name'] for entry in inherited_commands} == inherited_names
    inherited_baseline = next(entry for entry in inherited['variants'] if entry['name'] == 'baseline')
    final_baseline = next(entry for entry in receipt['variants'] if entry['name'] == 'baseline')
    assert inherited_baseline['treeSHA256'] == final_baseline['treeSHA256']
    assert (inherited_path.parent / inherited_baseline['manifest']).read_bytes() == (folder / final_baseline['manifest']).read_bytes()
    DETAILS['verifiedInheritedReceiptSHA256'] = sha(inherited_path)
    DETAILS['inheritedBaselineBinariesOnly'] = len(inherited_binaries)
    DETAILS['tools'] = {name: command('tool-' + name, argv).strip() for name, argv in {
        'python': ['python3', '--version'], 'rustc': ['rustc', '-vV'], 'cargo': ['cargo', '--version'],
        'host': ['uname', '-a'], 'revision': ['git', 'rev-parse', 'HEAD']}.items()}
    by_name = {}
    command_folders = {}
    qualifying_commands = [(entry, folder) for entry in receipt['commands']]
    qualifying_commands += [(entry, inherited_path.parent) for entry in inherited_commands]
    for entry, command_folder in qualifying_commands:
        assert entry['exitCode'] == 0, entry['name']
        assert entry['diagnosticBootstrap'] is False
        for stream in ['stdout', 'stderr']:
            assert sha(command_folder / entry[stream]) == entry[stream + 'SHA256'], entry['name']
        by_name[entry['name']] = entry
        command_folders[entry['name']] = command_folder
    DETAILS['verifiedProducerCommands'] = len(by_name)
    binaries = {}
    for entry in receipt['binaries'] + inherited_binaries:
        assert sha(Path(entry['path'])) == entry['sha256'], entry['label']
        assert Path(entry['path']).stat().st_size == entry['bytes']
        listing = (command_folders[entry['listCommand']] / by_name[entry['listCommand']]['stdout']).read_text()
        actual = [line[:-6] for line in listing.splitlines() if line.endswith(': test')]
        assert actual == entry['tests']
        assert set(entry['executedTests']) <= set(actual)
        output = (command_folders[entry['runCommand']] / by_name[entry['runCommand']]['stdout']).read_text()
        assert f"test result: ok. {len(entry['executedTests'])} passed; 0 failed; 0 ignored;" in output
        binaries[(entry['label'], entry['name'])] = entry
    DETAILS['verifiedProducerBinaries'] = len(binaries)
    required_tests = ['shared_control_' + suffix for suffix in [
        'branch_targets_and_frame_boundary', 'cancellation_and_limits', 'close_partial_effects',
        'public_parity_trace', 'warm_dispatch_allocation_free', 'work_and_fuel_prefixes']]
    parity_rows = []
    for mode in ['span', 'all']:
        for profile in ['debug', 'release']:
            for target in ['span_control_extraction', 'span_execution',
                           'span_execution_allocations', 'span_numeric_extraction']:
                left = binaries[('baseline-' + mode + '-' + profile, target)]
                right = binaries[('candidate-' + mode + '-' + profile, target)]
                assert left['tests'] == right['tests']
                if target == 'span_control_extraction':
                    assert left['tests'] == required_tests
                markers = ['control_trace ', 'control_warm ', 'control_validation_ceiling '] if target == 'span_control_extraction' else ['numeric_trace ', 'numeric_cases '] if target == 'span_numeric_extraction' else []
                if markers:
                    get_output = lambda entry: (command_folders[entry['runCommand']] / by_name[entry['runCommand']]['stdout']).read_text()
                    a, b = marker_rows(get_output(left), markers), marker_rows(get_output(right), markers)
                    assert a == b
                    parity = next(entry for entry in receipt['parity'] if entry['mode'] == mode and entry['profile'] == profile and entry['target'] == target)
                    assert len(a) == parity['records']
                    assert hashlib.sha256(encoded(a)).hexdigest() == parity['traceSHA256']
                    parity_rows.append(dict(mode=mode, profile=profile, target=target, records=len(a)))
            left = binaries[('baseline-' + mode + '-' + profile + '-probe', 'mixer_vm')]
            right = binaries[('candidate-' + mode + '-' + profile + '-probe', 'mixer_vm')]
            assert left['executedTests'] == right['executedTests'] and len(left['executedTests']) == 2
            assert marker_rows(get_output(left), ['control_probe ']) == marker_rows(get_output(right), ['control_probe '])
    value_binaries = [entry for entry in receipt['binaries'] if entry['label'].endswith('-values')]
    assert len(value_binaries) == 4
    assert all(len(entry['executedTests']) == 12 and all('swift_values_' in name for name in entry['executedTests']) for entry in value_binaries)
    assert len([entry for entry in receipt['commands'] if entry['name'].endswith('-check')]) == 8
    assert {'candidate-format', 'candidate-clippy'} <= set(by_name)
    DETAILS['independentlyComparedFullTraceMatrices'] = parity_rows
    variants = {}
    for entry in receipt['variants']:
        expected = json.loads((folder / entry['manifest']).read_text())
        assert hashlib.sha256(encoded(expected)).hexdigest() == entry['treeSHA256']
        assert sha(folder / entry['archive']) == entry['archiveSHA256']
        files = load_archive(folder / entry['archive'])
        assert digest_manifest(files) == expected
        assert len(expected) == entry['files']
        assert manifest(Path(entry['path'])) == expected
        variants[entry['name']] = files
    DETAILS['verifiedProducerVariants'] = {entry['name']: entry['treeSHA256'] for entry in receipt['variants']}
    baseline, candidate = variants['baseline'], variants['candidate']
    accepted = load_archive(ROOT / 'verification/swift-control-macro-implementation/accepted-baseline.tar.gz')
    assert len(accepted) == 116
    assert hashlib.sha256(encoded(digest_manifest(accepted))).hexdigest() == receipt['acceptedBaselineTreeSHA256']
    assert set(baseline) - set(accepted) == {'tests/span_control_extraction.rs'}
    assert all(baseline[name] == data for name, data in accepted.items())
    assert set(candidate) == set(baseline)
    assert {name for name in baseline if baseline[name] != candidate[name]} == {
        'src/experimental/execution/mod.rs', 'src/experimental/execution/borrowed.rs'}
    owner_name = 'src/experimental/execution/mod.rs'
    borrowed_name = 'src/experimental/execution/borrowed.rs'
    owner = baseline[owner_name].decode()
    macro = (ROOT / 'verification/swift-control-macro-extraction/frozen_control_methods.rs').read_text()
    for name in ['pop32', 'close_control', 'branch']:
        original = method(owner, name)
        # Moving the literal method under the macro adds one indentation level.
        # Only leading/trailing line whitespace is ignored here; the archived
        # compiler pretty-printed method comparison below remains byte exact.
        normalized = lambda text: '\n'.join(line.strip() for line in text.splitlines())
        assert normalized(original) == normalized(method(macro, name)), name
        owner = owner.replace(original, 'borrowed::frozen_control_methods!();' if name == 'pop32' else '', 1)
    nonblank = lambda text: '\n'.join(line for line in text.splitlines() if line.strip())
    assert nonblank(owner) == nonblank(candidate[owner_name].decode())
    # The sole optional wording fix removes a stale proposal-only comment; the
    # complete macro definition, literal bodies and feature/private export stay exact.
    suffix = candidate[borrowed_name][len(baseline[borrowed_name]):].decode().strip()
    assert candidate[borrowed_name].startswith(baseline[borrowed_name])
    assert suffix[suffix.index('#[cfg'):].strip() == macro[macro.index('#[cfg'):].strip()
    DETAILS['productMacroComment'] = suffix[:suffix.index('#[cfg')].strip()
    assert candidate[owner_name].count(b'borrowed::frozen_control_methods!();') == 1
    assert 'macro_export' not in macro
    assert 'pub(super) use frozen_control_methods;' in macro
    # All private probes must be an appended cfg(test) module in the original
    # execution owner file; no lib alias, owner wrapper or extra runtime source.
    for name in ['baseline', 'candidate']:
        plain, probe = variants[name], variants[name + '-probe']
        assert set(plain) == set(probe), name
        assert {path for path in plain if plain[path] != probe[path]} == {owner_name}, name
        assert probe[owner_name].startswith(plain[owner_name])
    live_paths = [ROOT / 'vm/Cargo.toml', ROOT / 'vm/Cargo.lock']
    for directory in ['src', 'tests', 'include']:
        live_paths += [p for p in (ROOT / 'vm' / directory).rglob('*') if p.is_file()]
    assert {str(p.relative_to(ROOT / 'vm')): sha(p) for p in live_paths} == digest_manifest(candidate)
    DETAILS['literalSourceAndProbeScopeVerified'] = True
    # Verify the original compiler/layout/privacy evidence from archived inputs,
    # without invoking its historical live-tree verifier after implementation.
    proposal = ROOT / 'verification/swift-control-macro-extraction'
    freeze = json.loads((proposal / 'root-freeze.json').read_text())
    assert sha(proposal / 'seal.json') == freeze['sealSHA256']
    seal = json.loads((proposal / 'seal.json').read_text())
    for name, digest in seal['bindings'].items():
        assert sha(ROOT / name) == digest, name
    DETAILS['verifiedProposalSealFiles'] = len(seal['bindings'])
    DETAILS['proposalRootFreezeSHA256'] = sha(proposal / 'root-freeze.json')
    preflight = proposal / 'results/20261024T030635088702Z'
    saved = json.loads((preflight / 'receipt.json').read_text())
    expanded = {}
    commands = {entry['name']: entry for entry in saved['commands']}
    for entry in saved['expansions']:
        row = commands[entry['label']]
        assert sha(preflight / row['stdout']) == row['stdoutSHA256']
        assert sha(preflight / row['stderr']) == row['stderrSHA256']
        assert row['diagnosticBootstrap'] is True
        text = (preflight / row['stdout']).read_text()
        text = text[text.index('impl SpanInstance {'):]
        expanded[entry['label']] = {name: method(text, name) for name in ['pop32', 'close_control', 'branch']}
    for mode in ['span', 'all']:
        for profile in ['debug', 'release']:
            suffix = mode + '-' + profile + '-expansion'
            assert expanded['baseline-' + suffix] == expanded['candidate-' + suffix]
    layouts = []
    for entry in saved['binaries']:
        assert sha(Path(entry['path'])) == entry['sha256']
        text = (preflight / (entry['runCommand'] + '.stdout')).read_text()
        rows = marker_rows(text, ['control_macro_type ', 'control_macro_offset ', 'control_macro_reservation '])
        assert len(rows) == 66 and 'control_macro_reservation 2912' in rows
        layouts.append(rows)
    assert len(layouts) == 16 and all(rows == layouts[0] for rows in layouts)
    final_preflight = proposal / 'results/20261024T030849261537Z'
    finalized = json.loads((final_preflight / 'receipt.json').read_text())
    assert finalized['inheritedReceiptSHA256'] == sha(preflight / 'receipt.json')
    for entry in finalized['commands']:
        assert entry['exitCode'] != 0 and entry['expectedError'] in ['E0433', 'E0624']
        for stream in ['stdout', 'stderr']:
            assert sha(final_preflight / entry[stream]) == entry[stream + 'SHA256']
        output = (final_preflight / entry['stdout']).read_text()
        assert entry['expectedError'] in output
    sibling = json.loads((proposal / 'privacy-sibling/receipt.json').read_text())['command']
    assert sibling['exitCode'] != 0 and 'E0603' in sibling['actualCodes']
    for stream in ['stdout', 'stderr']:
        assert sha(proposal / ('privacy-sibling/' + stream + '.log')) == sibling[stream + 'SHA256']
    DETAILS['historicalPrivacyRejections'] = ['E0433', 'E0624', 'E0603']
    delta = json.loads((ROOT / 'verification/swift-control-macro-extraction/named-transient-map.json').read_text())
    assert len(delta['bindingGroups']) == 26 and sum(delta['trySites'].values()) == 9
    assert all(group['additionalBytes'] == group['additionalPositions'] == 0 for group in delta['bindingGroups'])
    DETAILS['historicalCompilerMethodComparisons'] = 12
    DETAILS['historicalLayoutBinaries'] = 16
    DETAILS['historicalLayoutRowsPerBinary'] = 66
    DETAILS['reservationHostBytes'] = 2912
    DETAILS['deltaMapOnly'] = True
    selected = ['shared_control_public_parity_trace', 'shared_control_work_and_fuel_prefixes',
                'shared_control_warm_dispatch_allocation_free', 'shared_control_cancellation_and_limits']
    replay, outputs = independent_build('candidate-public-all-release', candidate, selected)
    baseline_entry = binaries[('baseline-all-release', 'span_control_extraction')]
    baseline_output = (command_folders[baseline_entry['runCommand']] / by_name[baseline_entry['runCommand']]['stdout']).read_text()
    all_baseline_rows = marker_rows(baseline_output, ['control_trace ', 'control_warm ', 'control_validation_ceiling '])
    # Whole tests are retained in the producer log in harness order. Replayed
    # test traces are compared with the exact corresponding baseline test block.
    for test, output in zip(selected, outputs):
        start = baseline_output.index('test ' + test + ' ... ')
        next_test = baseline_output.find('\ntest ', start + 1)
        block = baseline_output[start:next_test if next_test >= 0 else len(baseline_output)]
        assert marker_rows(output, ['control_trace ', 'control_warm ', 'control_validation_ceiling ']) == marker_rows(
            block, ['control_trace ', 'control_warm ', 'control_validation_ceiling ']), test
    DETAILS['freshPublicReplay'] = replay
    DETAILS['producerControlTraceRows'] = len(all_baseline_rows)
    probe_entry = binaries[('candidate-all-release-probe', 'mixer_vm')]
    probe_tests = probe_entry['executedTests']
    replay, outputs = independent_build('candidate-probe-all-release', variants['candidate-probe'], probe_tests, True)
    baseline_probe = binaries[('baseline-all-release-probe', 'mixer_vm')]
    baseline_probe_output = (command_folders[baseline_probe['runCommand']] / by_name[baseline_probe['runCommand']]['stdout']).read_text()
    assert marker_rows('\n'.join(outputs), ['control_probe ']) == marker_rows(baseline_probe_output, ['control_probe '])
    DETAILS['freshPrivateReplay'] = replay
    DETAILS['scope'] = 'Bounded host frozen literal source extraction; no Swift control or frame execution qualification'


status = 'failed-independent-review'
try:
    main()
    status = 'independent-host-review-passed-bounded-extraction'
finally:
    result = dict(schema=1, status=status, commands=COMMANDS, details=DETAILS,
                  sourceMutation=False, productHooksAdded=False, swiftExecution=False,
                  nativeRuntime=False, physicalRuntime=False, gaAcceptance=False,
                  limitations=['Zero-addition delta only; historical full baseline accounting is not newly proved',
                               'Malformed-state private probes are derived archived-source tests, not valid public modules',
                               'Profile operand/control low-limit rejections are validation evidence, not runtime ceilings',
                               'Cancellation at helper entry and allocation ordinals is deterministic; no timing-race claim',
                               'Native runtime paused; physical, FieldLog immutable package, signing/store/customer/operational and GA pending'])
    (OUT / 'receipt.json').write_bytes(encoded(result))
    print(str(OUT / 'receipt.json'), flush=True)

#!/usr/bin/env python3
"""Rebind final trap-prefix refinement and replay only its changed host test."""
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
DETAILS = dict(reviewScriptSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), reviewArgv=sys.argv)
EXPECTED = ['shared_control_' + suffix for suffix in [
    'branch_targets_and_frame_boundary', 'cancellation_and_limits', 'close_partial_effects',
    'public_parity_trace', 'warm_dispatch_allocation_free', 'work_and_fuel_prefixes']]


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def rows(output, markers):
    result = []
    for line in output.splitlines():
        for marker in markers:
            at = line.find(marker)
            if at >= 0:
                result.append(line[at:])
                break
    return result


def packet(path, binaries_filter=lambda entry: True):
    receipt = json.loads(path.read_text())
    folder = path.parent
    commands = {entry['name']: entry for entry in receipt['commands']}
    for entry in commands.values():
        for stream in ['stdout', 'stderr']:
            assert sha(folder / entry[stream]) == entry[stream + 'SHA256']
    binaries = {}
    for entry in receipt['binaries']:
        assert sha(Path(entry['path'])) == entry['sha256']
        listing = (folder / commands[entry['listCommand']]['stdout']).read_text()
        assert [line[:-6] for line in listing.splitlines() if line.endswith(': test')] == entry['tests']
        assert set(entry['executedTests']) <= set(entry['tests'])
        output = (folder / commands[entry['runCommand']]['stdout']).read_text()
        assert f"test result: ok. {len(entry['executedTests'])} passed; 0 failed; 0 ignored;" in output
        if binaries_filter(entry):
            binaries[(entry['label'], entry['name'])] = (entry, output)
    variants = {}
    for entry in receipt['variants']:
        expected = json.loads((folder / entry['manifest']).read_text())
        assert sha(folder / entry['archive']) == entry['archiveSHA256']
        assert hashlib.sha256(encoded(expected)).hexdigest() == entry['treeSHA256']
        with tarfile.open(folder / entry['archive']) as archive:
            files = {member.name.removeprefix('vm/'): archive.extractfile(member).read()
                     for member in archive.getmembers() if member.isfile()}
        assert {name: hashlib.sha256(data).hexdigest() for name, data in files.items()} == expected
        assert manifest(Path(entry['path'])) == expected
        variants[entry['name']] = files
    return receipt, binaries, variants


def command(name, argv, cwd=ROOT, source=None, target=None):
    if source is not None:
        assert manifest(cwd) == source
    env = dict(ENV)
    if target:
        env['CARGO_TARGET_DIR'] = str(target)
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=1200)
    if source is not None:
        assert manifest(cwd) == source
    entry = dict(name=name, argv=argv, cwd=str(cwd), sourceTreeSHA256=hashlib.sha256(encoded(source)).hexdigest() if source else None,
                 target=str(target) if target else None, startedUTC=start,
                 completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), exitCode=result.returncode,
                 diagnosticBootstrap=False)
    for stream, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
        path = OUT / (name + '.' + stream)
        path.write_bytes(data)
        entry[stream] = path.name
        entry[stream + 'SHA256'] = sha(path)
    COMMANDS.append(entry)
    print(name, result.returncode, flush=True)
    assert result.returncode == 0
    return result.stdout.decode()


def main():
    final_path, earlier_review_path = [Path(value).resolve() for value in sys.argv[1:3]]
    final, final_binaries, final_variants = packet(final_path)
    assert final['schema'] == 2 and final['status'] == 'host-bounded-executable-parity-complete-root-review-pending'
    previous_path = (final_path.parent / final['inheritedReceipt']).resolve()
    assert sha(previous_path) == final['inheritedReceiptSHA256']
    previous, inherited_binaries, previous_variants = packet(previous_path, lambda entry: entry['name'] != 'span_control_extraction')
    original_path = previous_path.parent.parent / previous['inheritedReceipt']
    assert sha(original_path) == previous['inheritedReceiptSHA256']
    original, original_binaries, original_variants = packet(original_path, lambda entry: entry['label'].startswith('baseline-') and '-probe' not in entry['label'] and entry['name'] != 'span_control_extraction')
    assert len(final_binaries) == 8 and len(inherited_binaries) == 24 and len(original_binaries) == 12
    assert original_variants['baseline'] == previous_variants['baseline']
    assert all(entry['exitCode'] == 0 and entry['diagnosticBootstrap'] is False for receipt in [final, previous] for entry in receipt['commands'])
    for name in ['baseline', 'candidate']:
        old, new = previous_variants[name], final_variants[name]
        assert set(old) == set(new)
        assert {path for path in old if old[path] != new[path]} == {'tests/span_control_extraction.rs'}
        probe = previous_variants[name + '-probe']
        assert set(probe) == set(old)
        assert {path for path in old if old[path] != probe[path]} == {'src/experimental/execution/mod.rs'}
        assert probe['src/experimental/execution/mod.rs'].startswith(old['src/experimental/execution/mod.rs'])
    # Exact source delta: the final test changes only the loop input to include
    # the same hand-authored unreachable trap used in public parity.
    old_test = previous_variants['candidate']['tests/span_control_extraction.rs'].decode()
    new_test = final_variants['candidate']['tests/span_control_extraction.rs'].decode()
    prefix = 'fn shared_control_work_and_fuel_prefixes() {'
    old_start, new_start = old_test.index(prefix), new_test.index(prefix)
    old_end = old_test.index('\n#[test]', old_start)
    new_end = new_test.index('\n#[test]', new_start)
    assert old_test[:old_start] == new_test[:new_start]
    assert old_test[old_end:] == new_test[new_end:]
    assert '"unreachable"' in new_test[new_start:new_end]
    DETAILS['changedSourceFile'] = 'vm/tests/span_control_extraction.rs'
    markers = ['control_trace ', 'control_warm ', 'control_validation_ceiling ']
    matrix = []
    for mode in ['span', 'all']:
        for profile in ['debug', 'release']:
            left, left_out = final_binaries[('baseline-' + mode + '-' + profile, 'span_control_extraction')]
            right, right_out = final_binaries[('candidate-' + mode + '-' + profile, 'span_control_extraction')]
            assert left['tests'] == right['tests'] == left['executedTests'] == right['executedTests'] == EXPECTED
            a, b = rows(left_out, markers), rows(right_out, markers)
            assert a == b and len(a) == 795
            entry = next(entry for entry in final['parity'] if entry['mode'] == mode and entry['profile'] == profile)
            assert entry['records'] == len(a) and entry['traceSHA256'] == hashlib.sha256(encoded(a)).hexdigest()
            matrix.append(dict(mode=mode, profile=profile, records=len(a), traceSHA256=entry['traceSHA256']))
            for target in ['span_execution', 'span_execution_allocations', 'span_numeric_extraction']:
                baseline, baseline_output = original_binaries[('baseline-' + mode + '-' + profile, target)]
                candidate, candidate_output = inherited_binaries[('candidate-' + mode + '-' + profile, target)]
                assert baseline['tests'] == candidate['tests'] == baseline['executedTests'] == candidate['executedTests']
                if target == 'span_numeric_extraction':
                    assert rows(baseline_output, ['numeric_trace ', 'numeric_cases ']) == rows(candidate_output, ['numeric_trace ', 'numeric_cases '])
            baseline, baseline_output = inherited_binaries[('baseline-' + mode + '-' + profile + '-probe', 'mixer_vm')]
            candidate, candidate_output = inherited_binaries[('candidate-' + mode + '-' + profile + '-probe', 'mixer_vm')]
            assert baseline['executedTests'] == candidate['executedTests'] and len(baseline['executedTests']) == 2
            assert rows(baseline_output, ['control_probe ']) == rows(candidate_output, ['control_probe '])
    values = [entry for entry in previous['binaries'] if entry['label'].endswith('-values')]
    assert len(values) == 4 and all(len(entry['executedTests']) == 12 and all('swift_values_' in name for name in entry['executedTests']) for entry in values)
    assert len([entry for entry in previous['commands'] if entry['name'].endswith('-check')]) == 8
    assert {'candidate-format', 'candidate-clippy'} <= {entry['name'] for entry in previous['commands']}
    # Rebind retained independent successful replays to the exact old variant
    # manifests; only the integration test changed since those six selected runs.
    earlier_review = json.loads(earlier_review_path.read_text())
    assert earlier_review['status'] == 'independent-host-review-passed-bounded-extraction'
    assert earlier_review['details']['producerReceiptSHA256'] == sha(previous_path)
    for entry in earlier_review['commands']:
        assert entry['exitCode'] == 0
        for stream in ['stdout', 'stderr']:
            assert sha(earlier_review_path.parent / entry[stream]) == entry[stream + 'SHA256']
    for key, variant in [('freshPublicReplay', 'candidate'), ('freshPrivateReplay', 'candidate-probe')]:
        replay = earlier_review['details'][key]
        assert sha(Path(replay['binary'])) == replay['binarySHA256']
        expected = {path: hashlib.sha256(data).hexdigest() for path, data in previous_variants[variant].items()}
        assert replay['sourceTreeSHA256'] == hashlib.sha256(encoded(expected)).hexdigest()
    DETAILS['priorIndependentReceipt'] = str(earlier_review_path.relative_to(ROOT))
    DETAILS['priorIndependentReceiptSHA256'] = sha(earlier_review_path)
    DETAILS['producerReceipt'] = str(final_path.relative_to(ROOT))
    DETAILS['producerReceiptSHA256'] = sha(final_path)
    DETAILS['verifiedProducerCommands'] = len(final['commands']) + len(previous['commands']) + len(original['commands'])
    DETAILS['verifiedQualifyingBinaries'] = 44
    DETAILS['independentlyComparedFullControlMatrix'] = matrix
    DETAILS['tools'] = {name: command('tool-' + name, argv).strip() for name, argv in {
        'python': ['python3', '--version'], 'rustc': ['rustc', '-vV'], 'cargo': ['cargo', '--version'],
        'host': ['uname', '-a'], 'revision': ['git', 'rev-parse', 'HEAD']}.items()}
    # Recheck every immutable proposal binding, including saved diagnostic
    # expansions, layout binaries' outputs, privacy rejections, and named map.
    proposal = ROOT / 'verification/swift-control-macro-extraction'
    freeze = json.loads((proposal / 'root-freeze.json').read_text())
    assert sha(proposal / 'seal.json') == freeze['sealSHA256']
    bindings = json.loads((proposal / 'seal.json').read_text())['bindings']
    for name, digest in bindings.items():
        assert sha(ROOT / name) == digest
    DETAILS['verifiedProposalSealFiles'] = len(bindings)
    candidate = final_variants['candidate']
    for name, data in candidate.items():
        assert (ROOT / 'vm' / name).read_bytes() == data
    source = OUT / 'candidate-prefix-all-release' / 'vm'
    for name, data in candidate.items():
        dest = source / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    expected = manifest(source)
    (OUT / 'candidate-prefix-manifest.json').write_bytes(encoded(expected))
    output = command('prefix-build', ['cargo', 'test', '--locked', '--offline', '--all-features', '--release',
                                    '--test', 'span_control_extraction', '--no-run', '--message-format=json'],
                     source, expected, HERE / 'target' / STAMP / 'prefix')
    artifacts = []
    for line in output.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if item.get('reason') == 'compiler-artifact' and item.get('executable') and item.get('profile', {}).get('test'):
            artifacts.append(Path(item['executable']))
    assert len(artifacts) == 1
    binary = artifacts[0]
    listing = command('prefix-list', [str(binary), '--list'], source, expected)
    assert [line[:-6] for line in listing.splitlines() if line.endswith(': test')] == EXPECTED
    selected = 'shared_control_work_and_fuel_prefixes'
    output = command('prefix-run', [str(binary), selected, '--exact', '--nocapture', '--test-threads=1'], source, expected)
    assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in output
    baseline_output = final_binaries[('baseline-all-release', 'span_control_extraction')][1]
    start = baseline_output.index('test ' + selected + ' ... ')
    end = baseline_output.find('\ntest ', start + 1)
    baseline_block = baseline_output[start:end if end >= 0 else len(baseline_output)]
    assert rows(output, markers) == rows(baseline_block, markers)
    trap_rows = [line for line in rows(output, markers) if line.startswith('control_trace unreachable ')]
    assert len(trap_rows) == 16
    assert any('kind: GuestTrap' in line for line in trap_rows)
    assert any('kind: WorkExhausted' in line for line in trap_rows)
    assert any('kind: FuelExhausted' in line for line in trap_rows)
    DETAILS['freshPublicReplay'] = dict(binary=str(binary), binarySHA256=sha(binary), listedTests=EXPECTED,
                                        executedTests=[selected], sourceTreeSHA256=hashlib.sha256(encoded(expected)).hexdigest())
    DETAILS['unreachablePrefixRows'] = len(trap_rows)
    DETAILS['finalCandidateTreeSHA256'] = hashlib.sha256(encoded(expected)).hexdigest()
    assert DETAILS['finalCandidateTreeSHA256'] == next(entry['treeSHA256'] for entry in final['variants'] if entry['name'] == 'candidate')


status = 'failed-independent-review'
try:
    main()
    status = 'independent-host-review-passed-bounded-extraction'
finally:
    receipt = dict(schema=2, status=status, commands=COMMANDS, details=DETAILS,
                   sourceMutation=False, productHooksAdded=False, swiftExecution=False,
                   nativeRuntime=False, physicalRuntime=False, gaAcceptance=False,
                   limitations=['Final refined prefix test freshly replayed; unchanged selected public/private tests inherited from independent prior replay',
                                'Zero-addition delta only; no new complete historical baseline memory proof',
                                'Invalid private states and validation-limit rejections retain their distinct scopes',
                                'Native runtime paused; final physical, immutable FieldLog, signing/store/customer/operational and GA evidence pending'])
    (OUT / 'receipt.json').write_bytes(encoded(receipt))
    print(str(OUT / 'receipt.json'), flush=True)
